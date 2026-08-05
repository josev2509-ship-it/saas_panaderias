from django.contrib import admin

from .models import (
    CategoriaProveedor, ContactoProveedor, CuentaBancariaProveedor,
    DireccionProveedor, HistorialEstadoProveedor, ProductoProveedor, Proveedor,
    ProveedorLegadoMap, RequisitoDocumentoProveedor, RevisionDocumentoProveedor,
    SolicitudCompra, DetalleSolicitudCompra, HistorialEstadoSolicitudCompra,
    ExpedienteCompra,SolicitudExpedienteCompra,ProcesoRFQ,DetalleRFQ,CriterioEvaluacionRFQ,ReglaParticipacionRFQ,InvitacionProveedorRFQ,HistorialEstadoExpedienteCompra,HistorialEstadoRFQ,
    OfertaProveedor, LineaOferta, VersionOferta, HistorialOferta, AclaracionOferta,
    ComparativoCompra, LineaComparativo, EscenarioComparativo, HistorialComparativo,
    AdjudicacionCompra, DetalleAdjudicacion, HistorialAdjudicacion,
    OrdenCompraEnterprise, DetalleOrdenCompraEnterprise, VersionOrdenCompra, HistorialOrdenCompra,
    RecepcionCompra, DetalleRecepcionCompra, InspeccionRecepcion,
    DevolucionCompra, DetalleDevolucionCompra, WizardSession, WizardStepState, WizardAuditTrail,
)


class EmpresaScopedAdmin(admin.ModelAdmin):
    exclude=("empresa",)
    def get_queryset(self,request):
        qs=super().get_queryset(request)
        empresa=getattr(request.user,"empresa_principal",None)
        return qs if request.user.is_superuser and not empresa else qs.filter(empresa=empresa)
    def save_model(self,request,obj,form,change):
        obj.empresa=getattr(request.user,"empresa_principal",None)
        if hasattr(obj,"actualizado_por"): obj.actualizado_por=request.user
        if hasattr(obj,"creado_por") and not obj.creado_por_id: obj.creado_por=request.user
        super().save_model(request,obj,form,change)


@admin.register(Proveedor)
class ProveedorAdmin(EmpresaScopedAdmin):
    list_display=("codigo","razon_social","estado","nivel_riesgo","documentacion_completa")
    list_filter=("estado","nivel_riesgo","documentacion_completa")
    search_fields=("codigo","razon_social","nombre_comercial","rnc_normalizado")
    readonly_fields=("rnc_normalizado","estado","bloqueado","fecha_bloqueo","bloqueado_por")


@admin.register(CuentaBancariaProveedor)
class CuentaBancariaProveedorAdmin(EmpresaScopedAdmin):
    list_display=("proveedor","banco","numero_enmascarado","estado","principal")
    readonly_fields=("numero_enmascarado","estado","verificada","fecha_verificacion","verificada_por")
    exclude=("empresa","numero_cuenta")

@admin.register(SolicitudCompra)
class SolicitudCompraAdmin(EmpresaScopedAdmin):
    list_display=("numero","titulo","estado","prioridad","solicitante","total_estimado")
    list_filter=("estado","prioridad","naturaleza","fecha_solicitud")
    search_fields=("numero","titulo","referencia_externa")
    readonly_fields=("numero","estado","version_documento","subtotal_estimado","descuento_estimado","impuesto_estimado","total_estimado","workflow_instancia","estado_workflow_snapshot","ronda_workflow_actual","enviada_en","aprobada_en","rechazada_en","devuelta_en","cancelada_en","cerrada_en")
    def has_delete_permission(self,request,obj=None): return False

@admin.register(DetalleSolicitudCompra)
class DetalleSolicitudCompraAdmin(EmpresaScopedAdmin):
    list_display=("solicitud","orden","tipo_linea","descripcion","cantidad","total","activo")
    readonly_fields=("codigo_producto_snapshot","unidad_producto_snapshot","cantidad_base","impuesto_porcentaje_snapshot","impuesto_monto","subtotal","total")
    def has_delete_permission(self,request,obj=None): return False

@admin.register(HistorialEstadoSolicitudCompra)
class HistorialEstadoSolicitudCompraAdmin(EmpresaScopedAdmin):
    list_display=("solicitud","estado_anterior","estado_nuevo","origen","fecha")
    readonly_fields=tuple(f.name for f in HistorialEstadoSolicitudCompra._meta.fields)
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False

for model in (ExpedienteCompra,SolicitudExpedienteCompra,ProcesoRFQ,DetalleRFQ,CriterioEvaluacionRFQ,ReglaParticipacionRFQ,InvitacionProveedorRFQ,HistorialEstadoExpedienteCompra,HistorialEstadoRFQ):
    admin.site.register(model,EmpresaScopedAdmin)


for model in (CategoriaProveedor,ContactoProveedor,DireccionProveedor,ProductoProveedor,
              ProveedorLegadoMap,RequisitoDocumentoProveedor,
              RevisionDocumentoProveedor,HistorialEstadoProveedor):
    admin.site.register(model,EmpresaScopedAdmin)

for model in (
    OfertaProveedor, LineaOferta, VersionOferta, HistorialOferta, AclaracionOferta,
    ComparativoCompra, LineaComparativo, EscenarioComparativo, HistorialComparativo,
    AdjudicacionCompra, DetalleAdjudicacion, HistorialAdjudicacion,
    OrdenCompraEnterprise, DetalleOrdenCompraEnterprise, VersionOrdenCompra, HistorialOrdenCompra,
    RecepcionCompra, DetalleRecepcionCompra, InspeccionRecepcion,
    DevolucionCompra, DetalleDevolucionCompra,
    WizardSession, WizardStepState, WizardAuditTrail,
):
    admin.site.register(model, EmpresaScopedAdmin if hasattr(model, "empresa") else admin.ModelAdmin)
