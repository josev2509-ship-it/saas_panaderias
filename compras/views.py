import csv
from datetime import timedelta
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from workflow.domain.exceptions import WorkflowError
from compras.models import DetalleRFQ,ExpedienteCompra,ProcesoRFQ
from compras.application.expedientes_rfq import *
from compras.forms import RFQForm,CriterioRFQForm,ReglaRFQForm,InvitacionRFQForm,SolicitudExpedienteForm,ExtensionRFQForm,ExpedienteForm,CambioContactoForm,DetalleRFQForm
from django.db.models import Avg,Count,F,Sum

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from conduces.decorators import modulo_requerido
from conduces.services import obtener_empresa_usuario
from core.application.operation_context import OperationContext
from documentos.services import obtener_documentos
from .application.proveedores import (
    activar_proveedor, bloquear_proveedor, crear_contacto_proveedor,
    crear_direccion_proveedor, crear_proveedor, inactivar_proveedor,
    reactivar_proveedor, registrar_cuenta_bancaria, rechazar_cuenta_bancaria,
    suspender_proveedor, verificar_cuenta_bancaria,
    vincular_producto_proveedor, vincular_proveedor_legado,
)
from .forms import (
    ContactoProveedorForm, CuentaBancariaProveedorForm, DireccionProveedorForm,
    ProductoProveedorForm, ProveedorForm, ProveedorLegadoMapForm, TransicionForm,
)
from .models import CuentaBancariaProveedor, Proveedor, ProveedorLegadoMap
from .models import SolicitudCompra
from .forms import DetalleSolicitudCompraForm, FiltroSolicitudForm, MotivoSolicitudForm, SolicitudCompraForm
from .selectors import dashboard_solicitudes, solicitudes_empresa
from .application.solicitudes.services import (
    agregar_linea_solicitud, actualizar_solicitud_compra, cancelar_solicitud_compra,
    crear_solicitud_compra, duplicar_solicitud_compra, enviar_solicitud_a_aprobacion,
    exportar_solicitudes_csv, marcar_solicitud_lista, retirar_linea_solicitud,
    validar_solicitud_para_envio, devolver_solicitud_a_borrador,
)
from .selectors import proveedores_empresa


def _empresa(request): return obtener_empresa_usuario(request)
def _context(request): return OperationContext(empresa=_empresa(request),usuario=request.user,request=request,referencia=request.path)


@login_required
@modulo_requerido("modulo_compras","compras.view_proveedor")
def dashboard(request):
    qs=Proveedor.objects.filter(empresa=_empresa(request))
    resumen={x:qs.filter(estado=x).count() for x in Proveedor.Estado.values}
    return render(request,"compras/dashboard.html",{
        "resumen":resumen,"total":qs.count(),"criticos":qs.filter(es_proveedor_critico=True).count(),
        "sin_contacto":qs.exclude(contactos__principal=True,contactos__activo=True).count(),
        "sin_fiscal":qs.exclude(direcciones__tipo="FISCAL",direcciones__activa=True).count(),
        "revision_pendiente":qs.filter(Q(proxima_revision_documental__lte=timezone.localdate())|Q(documentacion_completa=False)).distinct().count(),
        "por_categoria":qs.values("categoria__nombre").annotate(total=Count("id")).order_by("-total"),
        "por_riesgo":qs.values("nivel_riesgo").annotate(total=Count("id")).order_by("nivel_riesgo"),
    })


@login_required
@modulo_requerido("modulo_compras","compras.view_proveedor")
def lista(request):
    filtros={k:request.GET.get(k,"").strip() for k in ("q","estado","categoria","nivel_riesgo","moneda_habitual","condicion_pago","documentacion_completa","es_proveedor_critico","es_preferido")}
    pagina=Paginator(proveedores_empresa(empresa=_empresa(request),filtros=filtros),25).get_page(request.GET.get("page"))
    return render(request,"compras/lista.html",{"proveedores":pagina,"filtros":filtros,"estados":Proveedor.Estado.choices,"riesgos":Proveedor.Riesgo.choices})


@login_required
@modulo_requerido("modulo_compras")
def editar(request,pk=None):
    permiso="compras.change_proveedor" if pk else "compras.add_proveedor"
    if not request.user.has_perm(permiso): raise PermissionDenied
    empresa=_empresa(request); obj=get_object_or_404(Proveedor,pk=pk,empresa=empresa) if pk else None
    form=ProveedorForm(request.POST or None,instance=obj,empresa=empresa)
    if request.method=="POST" and form.is_valid():
        try:
            saved=(__import__("compras.application.proveedores",fromlist=["actualizar_proveedor"]).actualizar_proveedor(
                context=_context(request),proveedor_id=obj.pk,datos=form.cleaned_data) if obj else crear_proveedor(context=_context(request),datos=form.cleaned_data))
            messages.success(request,"Proveedor guardado correctamente.")
            return redirect("compras:detalle",pk=saved.pk)
        except ValidationError as exc: form.add_error(None,exc)
    return render(request,"compras/form.html",{"form":form,"objeto":obj})


@login_required
@modulo_requerido("modulo_compras","compras.view_proveedor")
def detalle(request,pk):
    proveedor=get_object_or_404(Proveedor.objects.select_related("categoria"),pk=pk,empresa=_empresa(request))
    return render(request,"compras/detalle.html",{
        "proveedor":proveedor,"documentos":obtener_documentos(proveedor,_empresa(request)),
        "contacto_form":ContactoProveedorForm(empresa=_empresa(request)),
        "direccion_form":DireccionProveedorForm(empresa=_empresa(request)),
        "producto_form":ProductoProveedorForm(empresa=_empresa(request)),
        "cuenta_form":CuentaBancariaProveedorForm(empresa=_empresa(request)),
        "legado_form":ProveedorLegadoMapForm(empresa=_empresa(request)),
        "transicion_form":TransicionForm(),
    })


RELACIONES={
    "contacto":(ContactoProveedorForm,crear_contacto_proveedor,"add_contactoproveedor"),
    "direccion":(DireccionProveedorForm,crear_direccion_proveedor,"add_direccionproveedor"),
    "producto":(ProductoProveedorForm,vincular_producto_proveedor,"add_productoproveedor"),
    "cuenta":(CuentaBancariaProveedorForm,registrar_cuenta_bancaria,"add_cuentabancariaproveedor"),
    "legado":(ProveedorLegadoMapForm,vincular_proveedor_legado,"gestionar_correspondencia_proveedor"),
}


@login_required
@modulo_requerido("modulo_compras")
def agregar_relacion(request,pk,tipo):
    proveedor=get_object_or_404(Proveedor,pk=pk,empresa=_empresa(request))
    try: form_cls,service,permiso=RELACIONES[tipo]
    except KeyError: raise PermissionDenied
    if request.method!="POST" or not request.user.has_perm(f"compras.{permiso}"): raise PermissionDenied
    form=form_cls(request.POST,empresa=_empresa(request))
    if form.is_valid():
        datos=form.cleaned_data; datos["proveedor_nuevo" if tipo=="legado" else "proveedor"]=proveedor
        service(context=_context(request),datos=datos)
        messages.success(request,"Registro agregado.")
    else:
        messages.error(request,"No fue posible agregar el registro: "+str(form.errors))
    return redirect("compras:detalle",pk=pk)


ACCIONES={"activar":activar_proveedor,"suspender":suspender_proveedor,"bloquear":bloquear_proveedor,"reactivar":reactivar_proveedor,"inactivar":inactivar_proveedor}
@login_required
@modulo_requerido("modulo_compras")
def estado(request,pk,accion):
    if request.method!="POST" or accion not in ACCIONES: raise PermissionDenied
    form=TransicionForm(request.POST)
    if form.is_valid():
        try: ACCIONES[accion](context=_context(request),proveedor_id=pk,motivo=form.cleaned_data["motivo"]); messages.success(request,"Estado actualizado.")
        except ValidationError as exc: messages.error(request,str(exc))
    return redirect("compras:detalle",pk=pk)


@login_required
@modulo_requerido("modulo_compras")
def ver_cuenta(request,pk):
    if not request.user.has_perm("compras.view_datos_bancarios_completos"): raise PermissionDenied
    cuenta=get_object_or_404(CuentaBancariaProveedor,pk=pk,empresa=_empresa(request))
    registrar_evento(empresa=_empresa(request),usuario=request.user,request=request,objeto=cuenta,modulo="compras",
        accion=EventoAuditoria.Accion.OTRO,descripcion="Consulta autorizada de cuenta bancaria completa.",
        datos_nuevos={"cuenta_id":cuenta.pk})
    response=JsonResponse({"numero_cuenta":cuenta.numero_cuenta})
    response["Cache-Control"]="no-store, private"
    response["Pragma"]="no-cache"
    return response


@login_required
@modulo_requerido("modulo_compras")
def revisar_cuenta(request,pk,accion):
    if request.method!="POST": raise PermissionDenied
    cuenta=get_object_or_404(CuentaBancariaProveedor,pk=pk,empresa=_empresa(request))
    try:
        if accion=="verificar": verificar_cuenta_bancaria(context=_context(request),cuenta_id=pk)
        elif accion=="rechazar": rechazar_cuenta_bancaria(context=_context(request),cuenta_id=pk,motivo=request.POST.get("motivo",""))
        else: raise PermissionDenied
        messages.success(request,"Revisión bancaria registrada.")
    except ValidationError as exc: messages.error(request,str(exc))
    return redirect("compras:detalle",pk=cuenta.proveedor_id)


@login_required
@modulo_requerido("modulo_compras","compras.exportar_proveedores")
def exportar(request):
    response=HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"]='attachment; filename="proveedores.csv"'
    writer=csv.writer(response); writer.writerow(["Código","Razón social","RNC","Estado","Riesgo","Categoría","Documentación"])
    qs=proveedores_empresa(empresa=_empresa(request),filtros=request.GET)
    for p in qs: writer.writerow([p.codigo,p.razon_social,p.rnc_identificacion,p.estado,p.nivel_riesgo,p.categoria or "",p.documentacion_completa])
    registrar_evento(empresa=_empresa(request),usuario=request.user,request=request,modulo="compras",accion=EventoAuditoria.Accion.OTRO,descripcion="Exportación segura de proveedores.",datos_nuevos={"filas":qs.count()})
    return response


@login_required
@modulo_requerido("modulo_compras","compras.view_solicitudcompra")
def solicitudes_dashboard(request):
    return render(request,"compras/solicitudes/dashboard.html",{"kpis":dashboard_solicitudes(empresa=_empresa(request))})

@login_required
@modulo_requerido("modulo_compras","compras.view_solicitudcompra")
def solicitudes_lista(request):
    form=FiltroSolicitudForm(request.GET or None);filtros=request.GET if form.is_valid() else {}
    pagina=Paginator(solicitudes_empresa(empresa=_empresa(request),usuario=request.user,filtros=filtros),25).get_page(request.GET.get("page"))
    return render(request,"compras/solicitudes/lista.html",{"solicitudes":pagina,"form":form})

@login_required
@modulo_requerido("modulo_compras")
def solicitud_editar(request,pk=None):
    empresa=_empresa(request);perm="change_solicitudcompra" if pk else "add_solicitudcompra"
    if not request.user.has_perm(f"compras.{perm}"): raise PermissionDenied
    obj=get_object_or_404(SolicitudCompra,pk=pk,empresa=empresa) if pk else None
    form=SolicitudCompraForm(request.POST or None,instance=obj,empresa=empresa)
    if request.method=="POST" and form.is_valid():
        try:
            saved=actualizar_solicitud_compra(context=_context(request),solicitud_id=obj.pk,datos=form.cleaned_data) if obj else crear_solicitud_compra(context=_context(request),datos=dict(form.cleaned_data))
            messages.success(request,"Solicitud guardada.");return redirect("compras:solicitud_detalle",pk=saved.pk)
        except (ValidationError,PermissionDenied) as exc: form.add_error(None,exc)
    return render(request,"compras/solicitudes/form.html",{"form":form,"solicitud":obj})

@login_required
@modulo_requerido("modulo_compras","compras.view_solicitudcompra")
def solicitud_detalle(request,pk):
    obj=get_object_or_404(solicitudes_empresa(empresa=_empresa(request),usuario=request.user),pk=pk)
    result=validar_solicitud_para_envio(context=_context(request),solicitud=obj)
    return render(request,"compras/solicitudes/detalle.html",{"solicitud":obj,"linea_form":DetalleSolicitudCompraForm(empresa=_empresa(request)),"motivo_form":MotivoSolicitudForm(),"validacion":result,"documentos":obtener_documentos(obj,_empresa(request))})

@login_required
@modulo_requerido("modulo_compras")
def solicitud_linea_agregar(request,pk):
    if request.method!="POST": raise PermissionDenied
    form=DetalleSolicitudCompraForm(request.POST,empresa=_empresa(request))
    if form.is_valid():
        try: agregar_linea_solicitud(context=_context(request),solicitud_id=pk,datos=form.cleaned_data);messages.success(request,"Línea agregada.")
        except (ValidationError,PermissionDenied) as exc: messages.error(request,str(exc))
    else: messages.error(request,str(form.errors))
    return redirect("compras:solicitud_detalle",pk=pk)

@login_required
@modulo_requerido("modulo_compras")
def solicitud_linea_retirar(request,pk,linea_id):
    if request.method!="POST": raise PermissionDenied
    retirar_linea_solicitud(context=_context(request),linea_id=linea_id);return redirect("compras:solicitud_detalle",pk=pk)

@login_required
@modulo_requerido("modulo_compras")
def solicitud_accion(request,pk,accion):
    if request.method!="POST": raise PermissionDenied
    try:
        if accion=="marcar-lista": marcar_solicitud_lista(context=_context(request),solicitud_id=pk)
        elif accion=="borrador": devolver_solicitud_a_borrador(context=_context(request),solicitud_id=pk)
        elif accion=="enviar": enviar_solicitud_a_aprobacion(context=_context(request),solicitud_id=pk,idempotency_key=request.POST.get("idempotency_key") or f"solicitud-{pk}-{uuid4().hex}")
        elif accion=="cancelar": cancelar_solicitud_compra(context=_context(request),solicitud_id=pk,motivo=request.POST.get("motivo",""))
        elif accion=="duplicar":
            new=duplicar_solicitud_compra(context=_context(request),solicitud_id=pk);return redirect("compras:solicitud_detalle",pk=new.pk)
        else: raise PermissionDenied
        messages.success(request,"Acción completada.")
    except (ValidationError,PermissionDenied,WorkflowError) as exc: messages.error(request,str(exc))
    return redirect("compras:solicitud_detalle",pk=pk)

@login_required
@modulo_requerido("modulo_compras","compras.exportar_solicitudescompra")
def solicitudes_exportar(request):
    content=exportar_solicitudes_csv(context=_context(request),queryset=solicitudes_empresa(empresa=_empresa(request),usuario=request.user,filtros=request.GET));response=HttpResponse(content,content_type="text/csv; charset=utf-8");response["Content-Disposition"]='attachment; filename="solicitudes_compra.csv"';return response

@login_required
@modulo_requerido("modulo_compras","compras.view_expedientecompra")
def expedientes_lista(request):
    qs=ExpedienteCompra.objects.filter(empresa=_empresa(request)).select_related("responsable","centro_costo","moneda__moneda");return render(request,"compras/expedientes/lista.html",{"expedientes":qs})
@login_required
@modulo_requerido("modulo_compras","compras.view_expedientecompra")
def expediente_detalle(request,pk):
    e=get_object_or_404(ExpedienteCompra.objects.select_related("responsable","centro_costo","moneda__moneda").prefetch_related("solicitudes_vinculadas__solicitud","rfqs","historial"),pk=pk,empresa=_empresa(request));return render(request,"compras/expedientes/detalle.html",{"expediente":e,"salud":calcular_salud_expediente(expediente=e),"documentos":obtener_documentos(e,_empresa(request)),"form":ExpedienteForm(instance=e,empresa=_empresa(request))})
@login_required
@modulo_requerido("modulo_compras","compras.view_procesorfq")
def rfq_lista(request):
    return render(request,"compras/rfq/lista.html",{"rfqs":ProcesoRFQ.objects.filter(empresa=_empresa(request)).select_related("expediente","moneda__moneda")})
@login_required
@modulo_requerido("modulo_compras","compras.view_procesorfq")
def rfq_detalle(request,pk):
    r=get_object_or_404(ProcesoRFQ.objects.select_related("expediente","moneda__moneda").prefetch_related("lineas","criterios","reglas_participacion","invitaciones__proveedor","historial"),pk=pk,empresa=_empresa(request));return render(request,"compras/rfq/detalle.html",{"rfq":r,"documentos":obtener_documentos(r,_empresa(request)),"criterio_form":CriterioRFQForm(empresa=_empresa(request)),"regla_form":ReglaRFQForm(empresa=_empresa(request)),"invitacion_form":InvitacionRFQForm(empresa=_empresa(request)),"extension_form":ExtensionRFQForm()})

@login_required
@modulo_requerido("modulo_compras","compras.view_expedientecompra")
def p2p_dashboard(request):
    from contabilidad.models import CuentaPorPagarEnterprise,FacturaProveedor
    from compras.models import OfertaProveedor,OrdenCompraEnterprise,RecepcionCompra
    empresa=_empresa(request);e,r,inv=_p2p_querysets(request);now=timezone.now();k={"expedientes_abiertos":e.filter(estado="ABIERTO").count(),"rfq_abiertas":r.filter(estado="ABIERTA").count(),"ofertas_activas":OfertaProveedor.objects.filter(empresa=empresa,estado__in=["ENVIADA","ACTUALIZADA","EVALUADA"]).count(),"ordenes_abiertas":OrdenCompraEnterprise.objects.filter(empresa=empresa).exclude(estado__in=["CERRADA","CANCELADA"]).count(),"recepciones_pendientes":RecepcionCompra.objects.filter(empresa=empresa,estado__in=["BORRADOR","EN_PROCESO","PARCIAL","CON_DIFERENCIAS"]).count(),"facturas_pendientes":FacturaProveedor.objects.filter(empresa=empresa).exclude(estado__in=["PAGADA","ANULADA"]).count(),"saldo_cxp":CuentaPorPagarEnterprise.objects.filter(empresa=empresa).aggregate(v=Sum("saldo"))["v"] or 0,"proveedores_criticos":Proveedor.objects.filter(empresa=empresa,nivel_riesgo="CRITICO").count(),"por_vencer":r.filter(estado__in=["ABIERTA","EXTENDIDA"],fecha_limite__gt=now,fecha_limite__lte=now+timedelta(days=7)).count(),"invitados":inv.count(),"montos":e.values("moneda__moneda__codigo").annotate(total=Sum("presupuesto_estimado"))};return render(request,"compras/p2p_dashboard.html",{"k":k,"expedientes":Paginator(e,25).get_page(request.GET.get("page")),"rfqs":r[:25],"filtros":request.GET,"p2p_menu":[("ofertas","Ofertas"),("comparativos","Comparativos"),("adjudicaciones","Adjudicaciones"),("ordenes","Órdenes"),("recepciones","Recepciones"),("devoluciones","Devoluciones"),("facturas","Facturas"),("cxp","CxP"),("pagos","Pagos")]})

def _p2p_querysets(request):
    empresa=_empresa(request);e=ExpedienteCompra.objects.filter(empresa=empresa).select_related("responsable","centro_costo","tipo_compra","moneda__moneda");r=ProcesoRFQ.objects.filter(empresa=empresa).select_related("expediente__responsable","expediente__centro_costo","expediente__tipo_compra","moneda__moneda");inv=InvitacionProveedorRFQ.objects.filter(empresa=empresa).select_related("rfq","proveedor","contacto")
    estado=request.GET.get("estado","");responsable=request.GET.get("responsable","");centro=request.GET.get("centro_costo","");tipo=request.GET.get("tipo_compra","");desde=request.GET.get("desde","");hasta=request.GET.get("hasta","")
    if estado:e=e.filter(estado=estado);r=r.filter(estado=estado)
    if responsable:e=e.filter(responsable_id=responsable);r=r.filter(expediente__responsable_id=responsable)
    if centro:e=e.filter(centro_costo_id=centro);r=r.filter(expediente__centro_costo_id=centro)
    if tipo:e=e.filter(tipo_compra_id=tipo);r=r.filter(expediente__tipo_compra_id=tipo)
    if desde:e=e.filter(fecha_creacion__date__gte=desde);r=r.filter(fecha_creacion__date__gte=desde)
    if hasta:e=e.filter(fecha_creacion__date__lte=hasta);r=r.filter(fecha_creacion__date__lte=hasta)
    inv=inv.filter(rfq__in=r)
    return e.order_by("-fecha_creacion"),r.order_by("-fecha_creacion"),inv.order_by("-fecha_creacion")

@login_required
@modulo_requerido("modulo_compras")
def expediente_accion(request,pk,accion):
    if request.method!="POST":raise PermissionDenied
    try:
        if accion=="abrir":abrir_expediente(context=_context(request),expediente_id=pk)
        elif accion=="preparar":preparar_rfq(context=_context(request),expediente_id=pk)
        elif accion=="cancelar":cancelar_expediente(context=_context(request),expediente_id=pk,motivo=request.POST.get("motivo",""))
        elif accion=="desierto":declarar_expediente_desierto(context=_context(request),expediente_id=pk,motivo=request.POST.get("motivo",""))
        elif accion=="salud":recalcular_salud_expediente(context=_context(request),expediente_id=pk)
        else:raise PermissionDenied
        messages.success(request,"Acción completada.")
    except Exception as exc:messages.error(request,str(exc))
    return redirect("compras:expediente_detalle",pk=pk)

@login_required
@modulo_requerido("modulo_compras")
def rfq_crear_view(request,expediente_id):
    form=RFQForm(request.POST or None,empresa=_empresa(request))
    if request.method=="POST" and form.is_valid():
        try:r=crear_rfq(context=_context(request),expediente_id=expediente_id,datos=form.cleaned_data);return redirect("compras:rfq_detalle",pk=r.pk)
        except Exception as exc:form.add_error(None,exc)
    return render(request,"compras/rfq/form.html",{"form":form})

@login_required
@modulo_requerido("modulo_compras")
def expediente_editar_view(request,pk):
    e=get_object_or_404(ExpedienteCompra,pk=pk,empresa=_empresa(request));form=ExpedienteForm(request.POST or None,instance=e,empresa=_empresa(request))
    if request.method=="POST" and form.is_valid():
        try:actualizar_expediente_borrador(context=_context(request),expediente_id=pk,datos=form.cleaned_data);messages.success(request,"Expediente actualizado.");return redirect("compras:expediente_detalle",pk=pk)
        except Exception as exc:form.add_error(None,exc)
    return render(request,"compras/expedientes/form.html",{"form":form,"expediente":e})

@login_required
@modulo_requerido("modulo_compras")
def rfq_editar_view(request,pk):
    r=get_object_or_404(ProcesoRFQ,pk=pk,empresa=_empresa(request));form=RFQForm(request.POST or None,instance=r,empresa=_empresa(request))
    if request.method=="POST" and form.is_valid():
        try:actualizar_rfq_borrador(context=_context(request),rfq_id=pk,datos=form.cleaned_data);messages.success(request,"RFQ actualizada.");return redirect("compras:rfq_detalle",pk=pk)
        except Exception as exc:form.add_error(None,exc)
    return render(request,"compras/rfq/form.html",{"form":form,"rfq":r})

@login_required
@modulo_requerido("modulo_compras")
def expediente_desde_solicitud_view(request,solicitud_id):
    if request.method!="POST":raise PermissionDenied
    try:e=crear_expediente_desde_solicitud(context=_context(request),solicitud_id=solicitud_id);return redirect("compras:expediente_detalle",pk=e.pk)
    except Exception as exc:messages.error(request,str(exc));return redirect("compras:solicitud_detalle",pk=solicitud_id)

@login_required
@modulo_requerido("modulo_compras")
def rfq_agregar(request,pk,tipo):
    if request.method!="POST":raise PermissionDenied
    forms={"criterio":CriterioRFQForm,"regla":ReglaRFQForm,"proveedor":InvitacionRFQForm}
    if tipo not in forms:raise PermissionDenied
    form=forms[tipo](request.POST,empresa=_empresa(request))
    try:
        if not form.is_valid():raise ValidationError(form.errors)
        if tipo=="criterio":agregar_criterio(context=_context(request),rfq_id=pk,datos=form.cleaned_data)
        elif tipo=="regla":agregar_regla_participacion(context=_context(request),rfq_id=pk,datos=form.cleaned_data)
        else:agregar_proveedor_a_rfq(context=_context(request),rfq_id=pk,proveedor_id=form.cleaned_data["proveedor"].pk,contacto_id=getattr(form.cleaned_data.get("contacto"),"pk",None))
        messages.success(request,"Registro agregado.")
    except Exception as exc:messages.error(request,str(exc))
    return redirect("compras:rfq_detalle",pk=pk)

@login_required
@modulo_requerido("modulo_compras")
def rfq_extender_view(request,pk):
    if request.method!="POST":raise PermissionDenied
    form=ExtensionRFQForm(request.POST)
    try:
        if not form.is_valid():raise ValidationError(form.errors)
        extender_plazo_rfq(context=_context(request),rfq_id=pk,**form.cleaned_data);messages.success(request,"Plazo extendido.")
    except Exception as exc:messages.error(request,str(exc))
    return redirect("compras:rfq_detalle",pk=pk)

@login_required
@modulo_requerido("modulo_compras")
def rfq_linea_editar(request,pk):
    linea=get_object_or_404(DetalleRFQ.objects.select_related("rfq"),pk=pk,empresa=_empresa(request))
    if request.method!="POST":raise PermissionDenied
    form=DetalleRFQForm(request.POST,instance=linea,empresa=_empresa(request))
    try:
        if not form.is_valid():raise ValidationError(form.errors)
        actualizar_linea_rfq(context=_context(request),linea_id=pk,datos=form.cleaned_data);messages.success(request,"Línea actualizada.")
    except Exception as exc:messages.error(request,str(exc))
    return redirect("compras:rfq_detalle",pk=linea.rfq_id)

@login_required
@modulo_requerido("modulo_compras")
def rfq_accion(request,pk,accion):
    if request.method!="POST":raise PermissionDenied
    try:
        funcs={"lineas":lambda:generar_lineas_desde_solicitudes(context=_context(request),rfq_id=pk),"revision":lambda:enviar_rfq_revision(context=_context(request),rfq_id=pk),"borrador":lambda:devolver_rfq_borrador(context=_context(request),rfq_id=pk,motivo=request.POST.get("motivo","")),"publicar":lambda:publicar_rfq(context=_context(request),rfq_id=pk),"abrir":lambda:abrir_rfq(context=_context(request),rfq_id=pk),"cerrar":lambda:cerrar_rfq(context=_context(request),rfq_id=pk),"cancelar":lambda:cancelar_rfq(context=_context(request),rfq_id=pk,motivo=request.POST.get("motivo","")),"versionar":lambda:crear_nueva_version_rfq(context=_context(request),rfq_id=pk)};funcs[accion]();messages.success(request,"Acción completada.")
    except Exception as exc:messages.error(request,str(exc))
    return redirect("compras:rfq_detalle",pk=pk)

@login_required
@modulo_requerido("modulo_compras")
def invitacion_accion(request,pk,accion):
    if request.method!="POST":raise PermissionDenied
    i=get_object_or_404(InvitacionProveedorRFQ,pk=pk,empresa=_empresa(request));funcs={"enviar":lambda:marcar_invitacion_enviada(context=_context(request),invitacion_id=pk),"confirmar":lambda:confirmar_participacion(context=_context(request),invitacion_id=pk),"declinar":lambda:declinar_participacion(context=_context(request),invitacion_id=pk,motivo=request.POST.get("motivo","")),"sin-respuesta":lambda:marcar_sin_respuesta(context=_context(request),invitacion_id=pk),"retirar":lambda:retirar_proveedor_de_rfq(context=_context(request),invitacion_id=pk,motivo=request.POST.get("motivo",""))}
    try:funcs[accion]();messages.success(request,"Invitación actualizada.")
    except Exception as exc:messages.error(request,str(exc))
    return redirect("compras:rfq_detalle",pk=i.rfq_id)

@login_required
@modulo_requerido("modulo_compras")
def invitacion_contacto(request,pk):
    if request.method!="POST":raise PermissionDenied
    i=get_object_or_404(InvitacionProveedorRFQ,pk=pk,empresa=_empresa(request));form=CambioContactoForm(request.POST,empresa=_empresa(request),proveedor=i.proveedor)
    try:
        if not form.is_valid():raise ValidationError(form.errors)
        cambiar_contacto_invitacion_rfq(context=_context(request),invitacion_id=pk,contacto_id=form.cleaned_data["contacto"].pk);messages.success(request,"Contacto actualizado.")
    except Exception as exc:messages.error(request,str(exc))
    return redirect("compras:rfq_detalle",pk=i.rfq_id)

def _csv_safe(v):
    t=str(v or "");return "'"+t if t[:1] in "=+-@" else t
@login_required
@modulo_requerido("modulo_compras","compras.exportar_rfq")
def p2p_exportar(request):
    e_qs,r_qs,i_qs=_p2p_querysets(request);response=HttpResponse(content_type="text/csv; charset=utf-8");response["Content-Disposition"]='attachment; filename="expedientes_rfq.csv"';w=csv.writer(response);w.writerow(["Tipo","Número","Título/Proveedor","Estado","Responsable","Centro costo","Tipo compra","Moneda","Monto","Salud","Riesgo","Duración días"])
    for e in e_qs:w.writerow(["EXP",_csv_safe(e.numero),_csv_safe(e.titulo),e.estado,_csv_safe(e.responsable.username),_csv_safe(e.centro_costo.nombre),_csv_safe(e.tipo_compra.nombre),e.moneda.moneda.codigo,e.presupuesto_estimado,e.indice_salud,e.nivel_riesgo,(e.fecha_cierre-e.fecha_creacion).days if e.fecha_cierre else (timezone.now()-e.fecha_creacion).days])
    for r in r_qs:w.writerow(["RFQ",_csv_safe(r.numero),_csv_safe(r.titulo),r.estado,_csv_safe(r.expediente.responsable.username),_csv_safe(r.expediente.centro_costo.nombre),_csv_safe(r.expediente.tipo_compra.nombre),r.moneda.moneda.codigo,r.expediente.presupuesto_estimado,r.expediente.indice_salud,r.expediente.nivel_riesgo,(r.fecha_publicacion-r.fecha_creacion).days if r.fecha_publicacion else ""])
    for i in i_qs:w.writerow(["INV",_csv_safe(i.rfq.numero),_csv_safe(i.proveedor.razon_social),i.estado,_csv_safe(i.rfq.expediente.responsable.username),_csv_safe(i.rfq.expediente.centro_costo.nombre),_csv_safe(i.rfq.expediente.tipo_compra.nombre),i.rfq.moneda.moneda.codigo,"","","",""])
    registrar_evento(empresa=_empresa(request),usuario=request.user,request=request,modulo="compras",accion=EventoAuditoria.Accion.OTRO,descripcion="Exportación de expedientes y RFQ.");return response
