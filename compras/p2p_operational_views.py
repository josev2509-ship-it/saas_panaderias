from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST

from conduces.decorators import modulo_requerido
from conduces.services import obtener_empresa_usuario
from core.application.operation_context import OperationContext

from .application.exports import render_export
from .application.financial import (aprobar_solicitud_y_orden, crear_factura_proveedor,
    crear_nota_credito, crear_nota_debito, crear_solicitud_pago, pagar_orden,
    revertir_pago, validar_e_integrar_factura)
from .application.p2p import (agregar_detalle_recepcion, aprobar_adjudicacion,
    cerrar_recepcion, congelar_comparativo, crear_adjudicacion, crear_comparativo,
    crear_oferta, crear_orden_desde_adjudicacion, crear_recepcion,
    guardar_linea_oferta, recalcular_comparativo, transicionar_oferta,
    transicionar_orden)
from .application.wizards import cancelar as cancelar_wizard, iniciar, orquestar_paso, reanudar, retroceder
from .forms_p2p import (AdjudicacionForm, ComparativoForm, ExportForm,
    FacturaProveedorForm, LineaOfertaForm, NotaProveedorForm, OfertaForm,
    OrdenDesdeAdjudicacionForm, PagoForm, RecepcionForm, SolicitudPagoForm, WizardStepForm)
from .models import (AdjudicacionCompra, ComparativoCompra, OfertaProveedor,
                     OrdenCompraEnterprise, RecepcionCompra)

def _empresa(request):return obtener_empresa_usuario(request)
def _context(request):return OperationContext(empresa=_empresa(request),usuario=request.user,request=request,referencia=request.path,clave_idempotente=request.headers.get("Idempotency-Key") or f"web:{request.path}:{uuid4()}")
def _perm(request,codename):
    if not request.user.has_perm(codename if "." in codename else f"compras.{codename}"):raise PermissionDenied

FORMS={"oferta":OfertaForm,"comparativo":ComparativoForm,"adjudicacion":AdjudicacionForm,"orden":OrdenDesdeAdjudicacionForm,"recepcion":RecepcionForm,"factura":FacturaProveedorForm,"solicitud-pago":SolicitudPagoForm,"pago":PagoForm,"nota":NotaProveedorForm}

@login_required
@modulo_requerido("modulo_compras")
def wizard(request,tipo):
    if tipo not in FORMS:raise PermissionDenied
    form=FORMS[tipo](request.POST or None,empresa=_empresa(request))
    if request.method=="POST" and form.is_valid():
        try:
            c=form.cleaned_data;ctx=_context(request)
            if tipo=="oferta":_perm(request,"add_ofertaproveedor");obj=crear_oferta(context=ctx,rfq_id=c["rfq"].pk,proveedor_id=c["proveedor"].pk,datos=c)
            elif tipo=="comparativo":_perm(request,"add_comparativocompra");obj=crear_comparativo(context=ctx,rfq_id=c["rfq"].pk,ponderaciones=c.get("ponderaciones") or None)
            elif tipo=="adjudicacion":_perm(request,"add_adjudicacioncompra");obj=crear_adjudicacion(context=ctx,comparativo_id=c["comparativo"].pk,tipo=c["tipo"],selecciones=c["selecciones"],justificacion=c["justificacion"])
            elif tipo=="orden":_perm(request,"add_ordencompraenterprise");obj=crear_orden_desde_adjudicacion(context=ctx,adjudicacion_id=c["adjudicacion"].pk,proveedor_id=getattr(c.get("proveedor"),"pk",None))
            elif tipo=="recepcion":_perm(request,"add_recepcioncompra");obj=crear_recepcion(context=ctx,orden_id=c["orden"].pk,datos=c)
            elif tipo=="factura":_perm(request,"contabilidad.add_facturaproveedor");obj=crear_factura_proveedor(context=ctx,orden_id=c["orden"].pk,recepcion_id=c["recepcion"].pk,datos=c,lineas=c["lineas"])
            elif tipo=="solicitud-pago":_perm(request,"contabilidad.view_cuentaporpagarenterprise");obj=crear_solicitud_pago(context=ctx,cuenta_id=c["cuenta"].pk,monto=c["monto"])
            elif tipo=="pago":_perm(request,"contabilidad.view_ordenpago");obj=pagar_orden(context=ctx,orden_id=c["orden"].pk,cuenta_bancaria=c.get("cuenta_bancaria"),caja=c.get("caja"),monto=c["monto"],referencia=c["referencia"],metodo=c["metodo"],retencion=c["retencion"])
            else:
                _perm(request,"contabilidad.view_facturaproveedor");obj=crear_nota_credito(context=ctx,factura_id=c["factura"].pk,numero=c["numero"],monto=c["monto"],motivo=c["motivo"],impuesto=c["impuesto"],retencion=c["retencion"]) if c["tipo"]=="CREDITO" else crear_nota_debito(context=ctx,factura_id=c["factura"].pk,numero=c["numero"],monto=c["monto"],motivo=c["motivo"],impuesto=c["impuesto"])
            messages.success(request,"Operación P2P completada.");return redirect("compras:p2p_dashboard")
        except Exception as exc:form.add_error(None,exc)
    return render(request,"compras/p2p/wizard.html",{"form":form,"tipo":tipo,"pasos":{"oferta":["RFQ y proveedor","Condiciones","Líneas","Revisión y envío"],"recepcion":["Orden","Cantidades","Lotes/series","Inspección","InventoryEngine"],"factura":["Orden y recepción","Factura","Validación","CxP"],"pago":["Orden","Medio","Aplicación","Tesorería y asiento"]}.get(tipo,["Datos","Validación","Confirmación"])})

@login_required
@modulo_requerido("modulo_compras")
def linea_oferta(request,pk):
    oferta=get_object_or_404(OfertaProveedor,pk=pk,empresa=_empresa(request));form=LineaOfertaForm(request.POST or None,empresa=_empresa(request),rfq=oferta.rfq)
    if request.method=="POST" and form.is_valid():
        _perm(request,"change_ofertaproveedor");c=form.cleaned_data;guardar_linea_oferta(context=_context(request),oferta_id=oferta.pk,linea_rfq_id=c.pop("linea_rfq").pk,datos=c);return redirect("compras:p2p_recurso_detalle","ofertas",pk)
    return render(request,"compras/p2p/wizard.html",{"form":form,"tipo":"línea de oferta","pasos":["Línea RFQ","Precio e impuestos","Cumplimiento"]})

@login_required
@require_POST
@modulo_requerido("modulo_compras")
def accion(request,recurso,pk,accion):
    ctx=_context(request)
    if recurso=="oferta":
        _perm(request,"change_ofertaproveedor");mapping={"enviar":"ENVIADA","retirar":"RETIRADA","evaluar":"EVALUADA","descalificar":"DESCALIFICADA"};transicionar_oferta(context=ctx,oferta_id=pk,nuevo=mapping[accion],motivo=request.POST.get("motivo",""))
    elif recurso=="comparativo":
        _perm(request,"change_comparativocompra");recalcular_comparativo(context=ctx,comparativo_id=pk) if accion=="recalcular" else congelar_comparativo(context=ctx,comparativo_id=pk)
    elif recurso=="adjudicacion":_perm(request,"aprobar_adjudicacion");aprobar_adjudicacion(context=ctx,adjudicacion_id=pk)
    elif recurso=="orden":
        _perm(request,"change_ordencompraenterprise");mapping={"aprobar":"APROBADA","enviar":"ENVIADA","aceptar":"ACEPTADA","cancelar":"CANCELADA"};transicionar_orden(context=ctx,orden_id=pk,nuevo=mapping[accion],comentario=request.POST.get("motivo",""))
    elif recurso=="recepcion":_perm(request,"cerrar_recepcion");cerrar_recepcion(context=ctx,recepcion_id=pk)
    elif recurso=="factura":_perm(request,"contabilidad.change_facturaproveedor");validar_e_integrar_factura(context=ctx,factura_id=pk)
    elif recurso=="solicitud-pago":_perm(request,"contabilidad.view_ordenpago");aprobar_solicitud_y_orden(context=ctx,solicitud_id=pk)
    elif recurso=="pago" and accion=="revertir":_perm(request,"contabilidad.view_ordenpago");revertir_pago(context=ctx,orden_id=pk,motivo=request.POST.get("motivo",""))
    else:raise PermissionDenied
    messages.success(request,"Acción completada.");return redirect("compras:p2p_dashboard")

@login_required
@require_POST
@modulo_requerido("modulo_compras")
def exportar(request):
    _perm(request,"exportar_rfq");form=ExportForm(request.POST,empresa=_empresa(request))
    if not form.is_valid():raise ValidationError(form.errors)
    return render_export(context=_context(request),**form.cleaned_data)

@login_required
@modulo_requerido("modulo_compras")
def wizard_enterprise_iniciar(request,tipo):
    _perm(request,"operar_wizard_p2p");mapping={"compra":"COMPRA","recepcion":"RECEPCION","factura-pago":"FACTURA_PAGO"}
    if tipo not in mapping:raise PermissionDenied
    clave=request.POST.get("clave") or request.GET.get("clave") or f"web:{request.user.pk}:{tipo}:{timezone.localdate()}"
    sesion=iniciar(context=_context(request),tipo=mapping[tipo],clave_idempotencia=clave);return redirect("compras:p2p_wizard_enterprise",sesion.pk)

@login_required
@modulo_requerido("modulo_compras")
def wizard_enterprise(request,sesion_id):
    _perm(request,"operar_wizard_p2p");ctx=_context(request);sesion=reanudar(context=ctx,sesion_id=sesion_id);paso=sesion.pasos.get(numero=sesion.paso_actual);form=WizardStepForm(request.POST or None,empresa=_empresa(request),initial={"datos":paso.datos})
    if request.method=="POST":
        accion=request.POST.get("accion","avanzar")
        try:
            if accion=="cancelar":cancelar_wizard(context=ctx,sesion_id=sesion.pk)
            elif accion=="atras":retroceder(context=ctx,sesion_id=sesion.pk)
            elif form.is_valid():orquestar_paso(context=ctx,sesion_id=sesion.pk,numero=sesion.paso_actual,datos=form.cleaned_data["datos"])
            else:return render(request,"compras/p2p/wizard_enterprise.html",{"sesion":sesion,"paso":paso,"form":form})
            return redirect("compras:p2p_wizard_enterprise",sesion.pk)
        except (ValidationError,PermissionDenied) as exc:form.add_error(None,exc)
    return render(request,"compras/p2p/wizard_enterprise.html",{"sesion":sesion,"paso":paso,"form":form})
