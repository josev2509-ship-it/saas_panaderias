from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.models import Pedido
from comercial.pedidos_services import siguiente_numero
from conduces.services import obtener_empresa_usuario
from documentos.services import obtener_documentos

from .models import (
    DetallePlanProduccion, NecesidadMateriaPrima, OrdenProduccion, PlanProduccion,
    RecetaProduccion,
)
from .produccion_forms import (
    CompletarOrdenForm, DetallesPlanFormSet, GenerarPlanPedidosForm, IngredientesFormSet,
    InicioOrdenForm, OrdenProduccionForm, PlanProduccionForm, RecetaProduccionForm,
)
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
@permission_required("inventario.view_recetaproduccion",raise_exception=True)
def recetas_lista(request):
    empresa,salida=_empresa(request)
    if salida:return salida
    qs=RecetaProduccion.objects.filter(empresa=empresa).select_related("producto_terminado").annotate(num_ingredientes=Count("ingredientes"))
    q=request.GET.get("q","")
    if q:qs=qs.filter(Q(codigo__icontains=q)|Q(nombre__icontains=q)|Q(producto_terminado__nombre__icontains=q))
    if request.GET.get("activa"):qs=qs.filter(activa=request.GET["activa"]=="1")
    return render(request,"inventario/recetas_produccion_lista.html",{"empresa":empresa,"recetas":qs,"q":q})


def _guardar_receta(request,empresa,receta=None):
    form=RecetaProduccionForm(request.POST or None,instance=receta,empresa=empresa)
    formset=IngredientesFormSet(request.POST or None,instance=receta or RecetaProduccion(),prefix="ingredientes",form_kwargs={"empresa":empresa})
    if request.method=="POST" and form.is_valid() and formset.is_valid():
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
    return render(request,"inventario/produccion_form.html",{"empresa":empresa,"form":form,"formset":formset,"titulo":"Receta de producción"})


@login_required
@permission_required("inventario.add_recetaproduccion",raise_exception=True)
def receta_crear(request):
    empresa,salida=_empresa(request);return salida or _guardar_receta(request,empresa)


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
