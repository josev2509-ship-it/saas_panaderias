from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.models import Pedido
from comercial.pedidos_services import siguiente_numero
from conduces.decorators import modulo_requerido
from conduces.models import PerfilUsuario
from conduces.services import obtener_empresa_usuario
from documentos.services import obtener_documentos

from .models import (
    DetallePlanProduccion, DetalleRecetaProduccion, NecesidadMateriaPrima, OrdenProduccion, PlanProduccion,
    ProductoInventario, RecetaProduccion,
)
from .produccion_forms import (
    CompletarOrdenForm, DetallesPlanFormSet, GenerarPlanPedidosForm, IngredientesFormSet,
    FormulaRecetaUploadForm, InicioOrdenForm, OrdenProduccionForm, PlanProduccionForm,
    RecetaProduccionForm,
)
from .recipe_document_parser import RecipeDocumentParser
from .recipe_matching import encontrar_producto_terminado, encontrar_producto_terminado_match
from .recipe_catalog import evaluar_ingrediente, resolver_provisional_exacto, confirmar_alias
from .product_codes import siguiente_codigo_producto
from .recipe_matching import normalizar_nombre
from .produccion_services import (
    calcular_necesidades, duplicar_receta, generar_ordenes_desde_plan,
    generar_plan_desde_pedidos, recalcular_necesidades_plan, transicionar_orden,
)


def _empresa(request):
    empresa=obtener_empresa_usuario(request)
    if not empresa:
        messages.error(request,"Tu usuario no tiene una empresa asociada.")
        return None,redirect("inicio")
    return empresa,None


@login_required
def produccion_dashboard(request):
    empresa,salida=_empresa(request)
    if salida:return salida
    hoy=timezone.localdate(); ordenes=OrdenProduccion.objects.filter(empresa=empresa)
    return render(request,"inventario/produccion_dashboard.html",{
        "empresa":empresa,
        "programadas":ordenes.filter(fecha_programada=hoy,estado=OrdenProduccion.Estado.PROGRAMADA).count(),
        "en_proceso":ordenes.filter(estado=OrdenProduccion.Estado.EN_PROCESO).count(),
        "completadas":ordenes.filter(fecha_fin_real__date=hoy,estado=OrdenProduccion.Estado.COMPLETADA).count(),
        "urgentes":ordenes.filter(prioridad="URGENTE").exclude(estado__in=["COMPLETADA","CANCELADA"]).count(),
        "resumen":ordenes.aggregate(planificado=Sum("cantidad_planificada"),producido=Sum("cantidad_producida"),rechazado=Sum("cantidad_rechazada")),
        "insuficientes":NecesidadMateriaPrima.objects.filter(empresa=empresa,estado=NecesidadMateriaPrima.Estado.INSUFICIENTE).count(),
        "planes":PlanProduccion.objects.filter(empresa=empresa).exclude(estado=PlanProduccion.Estado.CANCELADO)[:6],
    })


@login_required
@modulo_requerido(
    "modulo_inabie",
    permiso_alternativo="inventario.view_recetaproduccion",
)
def recetas_lista(request):
    empresa,salida=_empresa(request)
    if salida:return salida
    qs=RecetaProduccion.objects.filter(empresa=empresa).select_related("producto_terminado").annotate(num_ingredientes=Count("ingredientes"))
    q=request.GET.get("q","")
    if q:qs=qs.filter(Q(codigo__icontains=q)|Q(nombre__icontains=q)|Q(producto_terminado__nombre__icontains=q))
    if request.GET.get("activa"):qs=qs.filter(activa=request.GET["activa"]=="1")
    return render(request,"inventario/recetas_produccion_lista.html",{"empresa":empresa,"recetas":qs,"q":q})


def _guardar_receta(request,empresa,receta=None,template_name="inventario/produccion_form.html"):
    form=RecetaProduccionForm(request.POST or None,instance=receta,empresa=empresa)
    formset=IngredientesFormSet(request.POST or None,instance=receta or RecetaProduccion(),prefix="ingredientes",form_kwargs={"empresa":empresa})
    if request.method=="POST" and form.is_valid() and formset.is_valid():
        duplicada = not receta and RecetaProduccion.objects.filter(
            empresa=empresa,
        ).filter(
            Q(codigo=form.cleaned_data["codigo"])
            | Q(producto_terminado=form.cleaned_data["producto_terminado"], version=form.cleaned_data["version"])
        ).exists()
        if duplicada:
            form.add_error(None, "Ya existe una receta con el mismo código o producto y versión.")
        else:
            with transaction.atomic():
                obj=form.save(commit=False);obj.empresa=empresa;obj.actualizado_por=request.user
                if not receta:obj.creado_por=request.user
                obj.full_clean();obj.save();formset.instance=obj
                ingredientes=formset.save(commit=False)
                for eliminado in formset.deleted_objects:eliminado.delete()
                for ing in ingredientes:
                    ing.receta=obj;ing.full_clean();ing.save()
                registrar_evento(empresa=empresa,usuario=request.user,request=request,objeto=obj,modulo="produccion",accion=EventoAuditoria.Accion.CREAR if not receta else EventoAuditoria.Accion.EDITAR,descripcion=f"Se {'creó' if not receta else 'editó'} la receta {obj.codigo}.")
            return redirect("inventario:receta_detalle",pk=obj.pk)
    return render(request,template_name,{
        "empresa":empresa,"form":form,"formset":formset,"titulo":"Receta de producción",
        "upload_form": FormulaRecetaUploadForm(), "modo_manual": True,
    })


def _analizar_documento_receta(request, empresa):
    upload_form = FormulaRecetaUploadForm(request.POST, request.FILES)
    if not upload_form.is_valid():
        return render(request, "inventario/receta_asistente.html", {
            "empresa": empresa, "upload_form": upload_form, "titulo": "Nueva receta",
        })
    try:
        lote = RecipeDocumentParser().parse_file(upload_form.cleaned_data["archivo"])
    except Exception:
        upload_form.add_error("archivo", "No fue posible leer el PDF. Verifica que no esté dañado o protegido.")
        return render(request, "inventario/receta_asistente.html", {
            "empresa": empresa, "upload_form": upload_form, "titulo": "Nueva receta",
        })

    if not lote.formulas:
        return render(request, "inventario/receta_asistente.html", {
            "empresa": empresa, "upload_form": FormulaRecetaUploadForm(), "titulo": "Nueva receta",
            "lote": lote, "vista_previa": True,
            "preview_local": getattr(request, "recipe_preview_local", False),
        })
    formulas = []
    productos_terminados = list(ProductoInventario.objects.filter(empresa=empresa, activo=True, tipo="producto_terminado").order_by("nombre"))
    materias_primas = list(ProductoInventario.objects.filter(empresa=empresa, activo=True, tipo="materia_prima").order_by("nombre"))
    for resultado_lote in lote.formulas:
        estado_documento = resultado_lote.estado
        producto_match = encontrar_producto_terminado_match(empresa=empresa, nombre=resultado_lote.nombre)
        producto_lote = ProductoInventario.objects.filter(
            pk=producto_match.producto_id, empresa=empresa, activo=True, tipo="producto_terminado"
        ).first() if producto_match.producto_id else None
        detalles_lote = []
        motivo_ingrediente = ""
        for extraido in resultado_lote.ingredientes:
            match = evaluar_ingrediente(empresa=empresa, nombre=extraido.nombre, unidad=extraido.unidad)
            decision = "EXISTENTE" if match.producto_id and match.estado in {"EXACTA_NORMALIZADA", "ALIAS_CONFIRMADO"} else "PROVISIONAL" if match.estado == "PROVISIONAL" else "REVISAR"
            detalles_lote.append({"extraido": extraido, "match": match, "decision": decision})
            if decision == "REVISAR" and estado_documento == "LISTA":
                motivo_ingrediente = "Unidad de ingrediente incompatible o asociación ambigua"
        requiere_ingrediente = bool(motivo_ingrediente)
        opcion_producto = "existente" if producto_lote else ""
        permite_crear_pt = False
        motivo = "Lista para aprobar" if estado_documento == "LISTA" else "Revisar datos incompletos de la fórmula"
        requiere_pt = False
        if not producto_lote and estado_documento == "LISTA":
            equivalentes = [p for p in productos_terminados if normalizar_nombre(p.nombre) == normalizar_nombre(resultado_lote.nombre)]
            permite_crear_pt = bool(resultado_lote.nombre.strip() and len(resultado_lote.nombre) <= 180 and not equivalentes)
            if permite_crear_pt and not producto_match.candidatos:
                opcion_producto = "crear"
                motivo = "Producto terminado nuevo: se creará al aprobar"
            else:
                requiere_pt = True
        if estado_documento == "LISTA":
            if requiere_pt and requiere_ingrediente:
                resultado_lote.estado = "REVISAR_ASOCIACIONES"
            elif requiere_pt:
                resultado_lote.estado = "REVISAR_PT"
            elif requiere_ingrediente:
                resultado_lote.estado = "REVISAR_ING"
            motivo = "; ".join(x for x in (
                "Falta asociar producto terminado" if requiere_pt else "",
                motivo_ingrediente,
            ) if x) or motivo
        formulas.append({"resultado": resultado_lote, "producto": producto_lote, "producto_match": producto_match,
                         "analisis_ingredientes": detalles_lote, "opcion_producto": opcion_producto,
                         "permite_crear_pt": permite_crear_pt, "requiere_pt": requiere_pt,
                         "requiere_ingrediente": requiere_ingrediente, "motivo": motivo})
    request.session["recetas_importacion_lote"] = [{
        "empresa_id": empresa.pk, "estado": item["resultado"].estado,
        "codigo": item["resultado"].codigo, "nombre": item["resultado"].nombre,
        "version": int(item["resultado"].revision) if item["resultado"].revision.isdigit() else 1,
        "rendimiento_base": str(item["resultado"].rendimiento_base or ""),
        "unidad_rendimiento": item["resultado"].unidad_rendimiento,
        "producto_id": item["producto"].pk if item["producto"] else None,
        "producto_opcion": item["opcion_producto"],
        "permite_crear_pt": item["permite_crear_pt"],
        "requiere_pt": item["requiere_pt"],
        "ingredientes": [{"producto_id": d["match"].producto_id, "nombre": d["extraido"].nombre,
                           "cantidad": str(d["extraido"].cantidad),
                           "unidad": d["extraido"].unidad, "orden": posicion,
                           "decision": d["decision"]}
                          for posicion, d in enumerate(item["analisis_ingredientes"], 1)],
    } for item in formulas]
    return render(request, "inventario/receta_asistente.html", {
        "empresa": empresa, "titulo": "Revisar fórmulas detectadas", "upload_form": FormulaRecetaUploadForm(),
        "lote": lote,
        "formulas_detectadas": formulas,
        "productos_terminados": productos_terminados,
        "materias_primas": materias_primas,
        "hay_formulas_listas": any(item["resultado"].estado == "LISTA" for item in formulas),
        "archivo_nombre": upload_form.cleaned_data["archivo"].name,
        "vista_previa": True,
    })


def _aprobar_lote_recetas(request, empresa, todas=False):
    lote = request.session.get("recetas_importacion_lote", [])
    indices = range(len(lote)) if todas else [int(request.POST.get("formula_index", -1))]
    creadas, errores = [], []
    for indice in indices:
        if indice < 0 or indice >= len(lote):
            errores.append("Fórmula inexistente."); continue
        datos = lote[indice]
        if todas and datos.get("estado") != "LISTA":
            continue
        if datos.get("empresa_id") != empresa.pk or datos.get("estado") not in {"LISTA", "REVISAR_PT", "REVISAR_ING", "REVISAR_ASOCIACIONES"}:
            errores.append(f"{datos.get('nombre') or indice + 1}: no está LISTA."); continue
        opcion = request.POST.get(f"producto_accion_{indice}") if not todas else None
        opcion = opcion or datos.get("producto_opcion") or ("existente" if datos.get("producto_id") else "")
        elegido_id = request.POST.get(f"producto_id_{indice}") if not todas else None
        if datos.get("requiere_pt") and not elegido_id and not (opcion == "crear" and datos.get("permite_crear_pt")):
            errores.append(f"{datos.get('nombre')}: seleccione un producto terminado."); continue
        try:
            with transaction.atomic():
                from conduces.models import Empresa
                Empresa.objects.select_for_update().get(pk=empresa.pk)
                codigo_oficial = (datos.get("codigo") or "").strip()
                existente_codigo = RecetaProduccion.objects.filter(empresa=empresa, codigo=codigo_oficial).first() if codigo_oficial else None
                if existente_codigo:
                    creadas.append(existente_codigo)
                    continue
                producto = None
                if opcion == "existente":
                    producto = ProductoInventario.objects.filter(
                        pk=elegido_id or datos.get("producto_id"), empresa=empresa,
                        activo=True, tipo="producto_terminado").first()
                elif opcion == "crear" and datos.get("permite_crear_pt"):
                    nombre = " ".join(datos["nombre"].split())
                    if not nombre or len(nombre) > 180:
                        raise ValidationError("Nombre del producto terminado inválido.")
                    equivalentes = [p for p in ProductoInventario.objects.filter(empresa=empresa, tipo="producto_terminado")
                                   if normalizar_nombre(p.nombre) == normalizar_nombre(nombre)]
                    if len(equivalentes) > 1:
                        raise ValidationError("Producto terminado ambiguo; requiere asociación manual.")
                    producto = equivalentes[0] if equivalentes else None
                    if producto is None:
                        producto = ProductoInventario.objects.create(
                            empresa=empresa, codigo=siguiente_codigo_producto(empresa=empresa, tipo="producto_terminado"),
                            nombre=nombre, tipo="producto_terminado", unidad_medida="unidad", stock_actual=0,
                            origen_catalogo="RECETA", requiere_revision=True, activo=True)
                if not producto:
                    raise ValidationError("Producto terminado sin asociación válida.")
                existente = RecetaProduccion.objects.filter(
                    empresa=empresa, producto_terminado=producto, version=datos["version"]).first()
                if existente:
                    creadas.append(existente)
                    continue
                materias = []
                aliases_confirmados = []
                for posicion, detalle in enumerate(datos["ingredientes"]):
                    decision = detalle.get("decision") or ("EXISTENTE" if detalle.get("producto_id") else "PROVISIONAL")
                    if decision == "EXISTENTE":
                        materia = ProductoInventario.objects.filter(
                            pk=detalle["producto_id"], empresa=empresa, activo=True,
                            tipo="materia_prima").first()
                    elif decision == "PROVISIONAL":
                        materia = resolver_provisional_exacto(
                            empresa=empresa, nombre=detalle["nombre"], unidad=detalle["unidad"])
                    elif decision == "REVISAR" and not todas:
                        accion = request.POST.get(f"ingrediente_accion_{indice}_{posicion}")
                        if accion == "existente":
                            materia = ProductoInventario.objects.filter(
                                pk=request.POST.get(f"ingrediente_id_{indice}_{posicion}"),
                                empresa=empresa, activo=True, tipo="materia_prima").first()
                            if materia:
                                aliases_confirmados.append((detalle["nombre"], materia))
                        elif accion == "crear":
                            materia = resolver_provisional_exacto(
                                empresa=empresa, nombre=detalle["nombre"], unidad=detalle["unidad"])
                        else:
                            raise ValidationError(f"{detalle['nombre']}: requiere una decisión explícita.")
                    else:
                        raise ValidationError(f"{detalle['nombre']}: requiere una decisión explícita.")
                    from .units import unidades_compatibles
                    if materia is None or not unidades_compatibles(detalle["unidad"], materia.unidad_medida):
                        raise ValidationError(f"{detalle['nombre']}: producto no disponible o unidad incompatible.")
                    materias.append(materia)
                receta = RecetaProduccion(
                    empresa=empresa, codigo=codigo_oficial or siguiente_codigo_producto(empresa=empresa, tipo="receta"),
                    nombre=datos["nombre"], producto_terminado=producto,
                    version=datos["version"], rendimiento_base=datos["rendimiento_base"],
                    unidad_rendimiento=datos["unidad_rendimiento"], activa=False,
                    fecha_vigencia_desde=timezone.localdate(), creado_por=request.user, actualizado_por=request.user,
                )
                receta.full_clean(); receta.save()
                for detalle, materia in zip(datos["ingredientes"], materias):
                    ingrediente = DetalleRecetaProduccion(
                        receta=receta, materia_prima=materia, cantidad=detalle["cantidad"],
                        unidad_medida=detalle["unidad"], orden=detalle["orden"],
                    )
                    ingrediente.full_clean(); ingrediente.save()
                for nombre_alias, materia in aliases_confirmados:
                    confirmar_alias(empresa=empresa, nombre=nombre_alias, producto=materia, usuario=request.user)
                registrar_evento(empresa=empresa, usuario=request.user, request=request, objeto=receta,
                    modulo="produccion", accion=EventoAuditoria.Accion.CREAR,
                    descripcion=f"Se importó y aprobó la receta {receta.codigo}.")
            creadas.append(receta)
        except ValidationError as exc:
            errores.append(f"{datos.get('nombre')}: {'; '.join(exc.messages)}")
    for error in errores: messages.error(request, error)
    if creadas: messages.success(request, f"Se aprobaron {len(creadas)} fórmula(s), sin activar automáticamente.")
    return redirect("inventario:recetas_lista")


@login_required
@modulo_requerido("modulo_inabie")
def receta_crear(request):
    puede_crear = request.user.has_perm("inventario.add_recetaproduccion") or PerfilUsuario.objects.filter(
        user=request.user,
        rol="admin_empresa",
        activo=True,
    ).exists()
    if not puede_crear:
        raise PermissionDenied
    empresa,salida=_empresa(request)
    if salida:return salida
    if request.method == "POST" and request.POST.get("accion") == "analizar":
        return _analizar_documento_receta(request, empresa)
    if request.method == "POST" and request.POST.get("accion") == "aprobar_formula":
        return _aprobar_lote_recetas(request, empresa)
    if request.method == "POST" and request.POST.get("accion") == "aprobar_listas":
        return _aprobar_lote_recetas(request, empresa, todas=True)
    if request.method == "POST" and request.POST.get("accion") == "guardar":
        return _guardar_receta(request, empresa, template_name="inventario/receta_asistente.html")
    return render(request,"inventario/receta_asistente.html",{
        "empresa":empresa,"titulo":"Nueva receta","upload_form":FormulaRecetaUploadForm(),
        "form":RecetaProduccionForm(empresa=empresa),
        "formset":IngredientesFormSet(prefix="ingredientes",form_kwargs={"empresa":empresa}),
    })


@login_required
@permission_required("inventario.change_recetaproduccion",raise_exception=True)
def receta_editar(request,pk):
    empresa,salida=_empresa(request)
    if salida:return salida
    return _guardar_receta(request,empresa,get_object_or_404(RecetaProduccion,pk=pk,empresa=empresa))


@login_required
@permission_required("inventario.view_recetaproduccion",raise_exception=True)
def receta_detalle(request,pk):
    empresa,salida=_empresa(request)
    if salida:return salida
    obj=get_object_or_404(RecetaProduccion.objects.prefetch_related("ingredientes__materia_prima"),pk=pk,empresa=empresa)
    ct=ContentType.objects.get_for_model(obj)
    return render(request,"inventario/receta_produccion_detalle.html",{"empresa":empresa,"receta":obj,"documentos":obtener_documentos(obj,empresa),"eventos":EventoAuditoria.objects.filter(empresa=empresa,content_type=ct,object_id=obj.pk)[:20]})


@login_required
@permission_required("inventario.add_recetaproduccion",raise_exception=True)
def receta_duplicar(request,pk):
    if request.method!="POST":return HttpResponseNotAllowed(["POST"])
    empresa,salida=_empresa(request)
    if salida:return salida
    obj=get_object_or_404(RecetaProduccion,pk=pk,empresa=empresa)
    return redirect("inventario:receta_detalle",pk=duplicar_receta(receta=obj,usuario=request.user,request=request).pk)


@login_required
@permission_required("inventario.change_recetaproduccion",raise_exception=True)
def receta_cambiar_estado(request,pk):
    if request.method!="POST":return HttpResponseNotAllowed(["POST"])
    empresa,salida=_empresa(request)
    if salida:return salida
    obj=get_object_or_404(RecetaProduccion,pk=pk,empresa=empresa);anterior=obj.activa;obj.activa=not obj.activa;obj.actualizado_por=request.user;obj.save()
    registrar_evento(empresa=empresa,usuario=request.user,request=request,objeto=obj,modulo="produccion",accion=EventoAuditoria.Accion.CAMBIAR_ESTADO,descripcion=f"Receta {obj.codigo}: {'activa' if obj.activa else 'inactiva'}.",datos_anteriores={"activa":anterior},datos_nuevos={"activa":obj.activa})
    return redirect("inventario:receta_detalle",pk=obj.pk)


@login_required
@permission_required("inventario.view_planproduccion",raise_exception=True)
def planes_lista(request):
    empresa,salida=_empresa(request)
    if salida:return salida
    qs=PlanProduccion.objects.filter(empresa=empresa).annotate(productos=Count("detalles"),num_ordenes=Count("ordenes"))
    q=request.GET.get("q","")
    if q:qs=qs.filter(numero__icontains=q)
    return render(request,"inventario/planes_lista.html",{"empresa":empresa,"planes":qs,"q":q})


def _guardar_plan(request,empresa,plan=None):
    if plan and plan.estado!=PlanProduccion.Estado.BORRADOR:return redirect("inventario:plan_detalle",pk=plan.pk)
    form=PlanProduccionForm(request.POST or None,instance=plan)
    formset=DetallesPlanFormSet(request.POST or None,instance=plan or PlanProduccion(),prefix="detalles",form_kwargs={"empresa":empresa})
    if request.method=="POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            obj=form.save(commit=False);obj.empresa=empresa;obj.actualizado_por=request.user
            if not plan:obj.numero=siguiente_numero(empresa,obj.fecha_plan,"PLA");obj.creado_por=request.user
            obj.save();formset.instance=obj;lineas=formset.save(commit=False)
            for eliminado in formset.deleted_objects:eliminado.delete()
            for linea in lineas:
                linea.plan=obj;linea.save()
            recalcular_necesidades_plan(obj)
            registrar_evento(empresa=empresa,usuario=request.user,request=request,objeto=obj,modulo="produccion",accion=EventoAuditoria.Accion.CREAR if not plan else EventoAuditoria.Accion.EDITAR,descripcion=f"Se guardó el plan {obj.numero}.")
        return redirect("inventario:plan_detalle",pk=obj.pk)
    return render(request,"inventario/produccion_form.html",{"empresa":empresa,"form":form,"formset":formset,"titulo":"Plan de producción"})


@login_required
@permission_required("inventario.add_planproduccion",raise_exception=True)
def plan_crear(request):
    empresa,salida=_empresa(request);return salida or _guardar_plan(request,empresa)


@login_required
@permission_required("inventario.change_planproduccion",raise_exception=True)
def plan_editar(request,pk):
    empresa,salida=_empresa(request)
    if salida:return salida
    return _guardar_plan(request,empresa,get_object_or_404(PlanProduccion,pk=pk,empresa=empresa))


@login_required
@permission_required("inventario.add_planproduccion",raise_exception=True)
def plan_generar_desde_pedidos(request):
    empresa,salida=_empresa(request)
    if salida:return salida
    form=GenerarPlanPedidosForm(request.POST or None,empresa=empresa)
    if request.method=="POST" and form.is_valid():
        try:plan=generar_plan_desde_pedidos(empresa=empresa,pedidos=form.cleaned_data["pedidos"],fecha_plan=form.cleaned_data["fecha_plan"],usuario=request.user,request=request)
        except ValidationError as e:form.add_error(None,e)
        else:return redirect("inventario:plan_detalle",pk=plan.pk)
    return render(request,"inventario/produccion_form.html",{"empresa":empresa,"form":form,"titulo":"Generar plan desde pedidos"})


@login_required
@permission_required("inventario.view_planproduccion",raise_exception=True)
def plan_detalle(request,pk):
    empresa,salida=_empresa(request)
    if salida:return salida
    obj=get_object_or_404(PlanProduccion.objects.prefetch_related("detalles__producto_terminado","necesidades__materia_prima","ordenes"),pk=pk,empresa=empresa)
    return render(request,"inventario/plan_detalle.html",{"empresa":empresa,"plan":obj,"documentos":obtener_documentos(obj,empresa)})


def _estado_plan(request,pk,destino,permiso):
    if request.method!="POST":return HttpResponseNotAllowed(["POST"])
    empresa,salida=_empresa(request)
    if salida:return salida
    if not request.user.has_perm(permiso):from django.core.exceptions import PermissionDenied;raise PermissionDenied
    with transaction.atomic():
        obj=get_object_or_404(PlanProduccion.objects.select_for_update(),pk=pk,empresa=empresa)
        if destino==PlanProduccion.Estado.APROBADO and obj.estado not in {PlanProduccion.Estado.BORRADOR,PlanProduccion.Estado.GENERADO}:raise ValidationError("Transición no permitida.")
        if destino==PlanProduccion.Estado.CANCELADO and obj.estado not in {PlanProduccion.Estado.BORRADOR,PlanProduccion.Estado.GENERADO}:raise ValidationError("Transición no permitida.")
        obj.estado=destino;obj.actualizado_por=request.user
        if destino==PlanProduccion.Estado.APROBADO:obj.aprobado_por=request.user;obj.fecha_aprobacion=timezone.now()
        obj.save();registrar_evento(empresa=empresa,usuario=request.user,request=request,objeto=obj,modulo="produccion",accion=EventoAuditoria.Accion.CAMBIAR_ESTADO,descripcion=f"Plan {obj.numero}: {obj.get_estado_display()}.")
    return redirect("inventario:plan_detalle",pk=obj.pk)


@login_required
def plan_aprobar(request,pk):return _estado_plan(request,pk,PlanProduccion.Estado.APROBADO,"inventario.aprobar_planproduccion")
@login_required
def plan_cancelar(request,pk):return _estado_plan(request,pk,PlanProduccion.Estado.CANCELADO,"inventario.cancelar_planproduccion")


@login_required
@permission_required("inventario.add_ordenproduccion",raise_exception=True)
def plan_generar_ordenes(request,pk):
    if request.method!="POST":return HttpResponseNotAllowed(["POST"])
    empresa,salida=_empresa(request)
    if salida:return salida
    plan=get_object_or_404(PlanProduccion,pk=pk,empresa=empresa)
    generar_ordenes_desde_plan(plan=plan,empresa=empresa,usuario=request.user,request=request)
    return redirect("inventario:plan_detalle",pk=plan.pk)


@login_required
@permission_required("inventario.view_ordenproduccion",raise_exception=True)
def ordenes_lista(request):
    empresa,salida=_empresa(request)
    if salida:return salida
    qs=OrdenProduccion.objects.filter(empresa=empresa).select_related("producto_terminado","responsable","plan")
    q=request.GET.get("q","")
    if q:qs=qs.filter(Q(numero__icontains=q)|Q(producto_terminado__nombre__icontains=q))
    return render(request,"inventario/ordenes_lista.html",{"empresa":empresa,"ordenes":qs,"q":q})


def _guardar_orden(request,empresa,orden=None):
    if orden and orden.estado!=OrdenProduccion.Estado.BORRADOR:return redirect("inventario:orden_detalle",pk=orden.pk)
    form=OrdenProduccionForm(request.POST or None,instance=orden,empresa=empresa)
    if request.method=="POST" and form.is_valid():
        obj=form.save(commit=False);obj.empresa=empresa;obj.actualizado_por=request.user
        if not orden:obj.numero=siguiente_numero(empresa,obj.fecha_programada,"OP");obj.creado_por=request.user
        obj.save();calcular_necesidades(cantidad=obj.cantidad_planificada,receta=obj.receta,empresa=empresa,orden=obj,fecha_requerida=obj.fecha_programada)
        registrar_evento(empresa=empresa,usuario=request.user,request=request,objeto=obj,modulo="produccion",accion=EventoAuditoria.Accion.CREAR if not orden else EventoAuditoria.Accion.EDITAR,descripcion=f"Se guardó la orden {obj.numero}.")
        return redirect("inventario:orden_detalle",pk=obj.pk)
    return render(request,"inventario/produccion_form.html",{"empresa":empresa,"form":form,"titulo":"Orden de producción"})


@login_required
@permission_required("inventario.add_ordenproduccion",raise_exception=True)
def orden_crear(request):
    empresa,salida=_empresa(request);return salida or _guardar_orden(request,empresa)


@login_required
@permission_required("inventario.change_ordenproduccion",raise_exception=True)
def orden_editar(request,pk):
    empresa,salida=_empresa(request)
    if salida:return salida
    return _guardar_orden(request,empresa,get_object_or_404(OrdenProduccion,pk=pk,empresa=empresa))


@login_required
@permission_required("inventario.view_ordenproduccion",raise_exception=True)
def orden_detalle(request,pk):
    empresa,salida=_empresa(request)
    if salida:return salida
    obj=get_object_or_404(OrdenProduccion.objects.select_related("producto_terminado","receta","plan","responsable").prefetch_related("necesidades__materia_prima"),pk=pk,empresa=empresa)
    ct=ContentType.objects.get_for_model(obj)
    return render(request,"inventario/orden_detalle.html",{"empresa":empresa,"orden":obj,"documentos":obtener_documentos(obj,empresa),"eventos":EventoAuditoria.objects.filter(empresa=empresa,content_type=ct,object_id=obj.pk)[:20],"inicio_form":InicioOrdenForm(initial={"cantidad_iniciada":obj.cantidad_planificada}),"completar_form":CompletarOrdenForm()})


def _accion_orden(request,pk,accion):
    if request.method!="POST":return HttpResponseNotAllowed(["POST"])
    empresa,salida=_empresa(request)
    if salida:return salida
    orden=get_object_or_404(OrdenProduccion,pk=pk,empresa=empresa)
    try:orden=transicionar_orden(orden=orden,empresa=empresa,usuario=request.user,accion=accion,request=request,comentario=request.POST.get("comentario",""),cantidad_iniciada=request.POST.get("cantidad_iniciada"),cantidad_producida=request.POST.get("cantidad_producida"),cantidad_rechazada=request.POST.get("cantidad_rechazada"))
    except ValidationError as e:messages.error(request,"; ".join(e.messages))
    return redirect("inventario:orden_detalle",pk=orden.pk)


@login_required
def orden_programar(request,pk):return _accion_orden(request,pk,"programar")
@login_required
def orden_iniciar(request,pk):return _accion_orden(request,pk,"iniciar")
@login_required
def orden_completar(request,pk):return _accion_orden(request,pk,"completar")
@login_required
def orden_cancelar(request,pk):return _accion_orden(request,pk,"cancelar")


def _programacion(request,semanal=False):
    empresa,salida=_empresa(request)
    if salida:return salida
    try:inicio=date.fromisoformat(request.GET.get("fecha",""))
    except ValueError:inicio=timezone.localdate()
    fin=inicio+timedelta(days=6 if semanal else 0)
    ordenes=OrdenProduccion.objects.filter(empresa=empresa,fecha_programada__range=(inicio,fin)).exclude(estado=OrdenProduccion.Estado.CANCELADA).select_related("producto_terminado","receta","responsable")
    dias=[]
    for i in range((fin-inicio).days+1):
        fecha=inicio+timedelta(days=i);grupo=[o for o in ordenes if o.fecha_programada==fecha]
        dias.append({"fecha":fecha,"ordenes":grupo,"planificada":sum((o.cantidad_planificada for o in grupo),0),"producida":sum((o.cantidad_producida for o in grupo),0)})
    return render(request,"inventario/produccion_programacion.html",{"empresa":empresa,"dias":dias,"semanal":semanal,"inicio":inicio})


@login_required
@permission_required("inventario.view_ordenproduccion",raise_exception=True)
def produccion_programacion_diaria(request):return _programacion(request)
@login_required
@permission_required("inventario.view_ordenproduccion",raise_exception=True)
def produccion_programacion_semanal(request):return _programacion(request,True)


@login_required
def necesidades_materia_prima(request):
    empresa,salida=_empresa(request)
    if salida:return salida
    qs=NecesidadMateriaPrima.objects.filter(empresa=empresa).select_related("materia_prima","producto_terminado","plan","orden")
    return render(request,"inventario/necesidades.html",{"empresa":empresa,"necesidades":qs})

# Preview local del asistente de recetas. Solo disponible con DEBUG=True.
def receta_preview_local(request):
    from django.conf import settings
    from django.http import Http404
    from conduces.models import Empresa

    if not settings.DEBUG:
        raise Http404

    empresa = Empresa.objects.filter(activa=True).first()
    if empresa is None:
        raise Http404("No existe una empresa activa para la previsualizacion local.")

    if request.method == "POST" and request.POST.get("accion") == "analizar":
        request.recipe_preview_local = True
        return _analizar_documento_receta(request, empresa)

    return render(request, "inventario/receta_asistente.html", {
        "empresa": empresa,
        "titulo": "Preview local - Nueva receta",
        "upload_form": FormulaRecetaUploadForm(),
        "form": RecetaProduccionForm(empresa=empresa),
        "formset": IngredientesFormSet(prefix="ingredientes", form_kwargs={"empresa": empresa}),
        "preview_local": True,
    })
