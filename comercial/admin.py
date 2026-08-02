from django.contrib import admin
from .models import *


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre_comercial", "empresa", "tipo_cliente", "condicion_pago", "estado")
    list_filter = ("empresa", "tipo_cliente", "condicion_pago", "estado")
    search_fields = ("codigo", "nombre_comercial", "razon_social", "rnc_cedula", "telefono")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    autocomplete_fields = ("empresa", "creado_por")


@admin.register(DireccionCliente)
class DireccionClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cliente", "tipo", "es_principal", "activa")
    list_filter = ("tipo", "es_principal", "activa", "cliente__empresa")
    search_fields = ("nombre", "cliente__nombre_comercial", "direccion", "municipio")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    autocomplete_fields = ("cliente",)


@admin.register(ContactoCliente)
class ContactoClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cliente", "cargo", "telefono", "es_principal", "activo")
    list_filter = ("es_principal", "activo", "recibe_facturas", "cliente__empresa")
    search_fields = ("nombre", "cliente__nombre_comercial", "telefono", "correo")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    autocomplete_fields = ("cliente",)


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = tuple(field.name for field in DetallePedido._meta.fields)
    can_delete = False
    def has_add_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("numero", "empresa", "cliente", "fecha_entrega", "estado", "moneda", "total")
    list_filter = ("empresa", "estado", "prioridad", "moneda", "fecha_entrega")
    search_fields = ("numero", "cliente__nombre_comercial", "cliente__rnc_cedula")
    readonly_fields = (
        "numero", "subtotal", "descuento_total", "impuesto_total", "total", "estado",
        "creado_por", "actualizado_por", "aprobado_por", "fecha_aprobacion",
        "rechazado_por", "fecha_rechazo", "fecha_creacion", "fecha_actualizacion",
    )
    inlines = (DetallePedidoInline,)


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario", "total")
    readonly_fields = tuple(field.name for field in DetallePedido._meta.fields)
    search_fields = ("pedido__numero", "producto__nombre")
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(HistorialEstadoPedido)
class HistorialEstadoPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado_anterior", "estado_nuevo", "usuario", "fecha")
    readonly_fields = tuple(field.name for field in HistorialEstadoPedido._meta.fields)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

class ConfigScopedAdmin(admin.ModelAdmin):
    list_display=("codigo","nombre","activo","orden");list_filter=("empresa","activo");search_fields=("codigo","nombre")
    def has_delete_permission(self,request,obj=None):return False
for model in (CanalVenta,SegmentoCliente,ClasificacionCliente,TipoCliente,TipoEntrega,PrioridadComercial,MotivoComercial,ZonaComercial,RutaComercial,EquipoComercial,VendedorComercial):admin.site.register(model,ConfigScopedAdmin)
@admin.register(ConfiguracionComercialEmpresa)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display=("empresa","estado","version","lista_para_vender","porcentaje_preparacion");readonly_fields=("version","lista_para_vender","porcentaje_preparacion","ultima_validacion","resultado_validacion")
    def has_delete_permission(self,request,obj=None):return False
for model in (PoliticaCredito,PoliticaDescuento,PoliticaEntrega,PoliticaFacturacion,PoliticaDevolucion,PoliticaComision):admin.site.register(model,admin.ModelAdmin)
@admin.register(VersionPoliticaComercial)
class VersionPoliticaAdmin(admin.ModelAdmin):
    list_display=("tipo_politica","codigo","version","estado","fecha_creacion")
    list_filter=("empresa","tipo_politica","estado")
    readonly_fields=tuple(field.name for field in VersionPoliticaComercial._meta.fields)
    def has_add_permission(self,request):return False
    def has_change_permission(self,request,obj=None):return False
    def has_delete_permission(self,request,obj=None):return False

@admin.register(FuenteProspecto)
class FuenteProspectoAdmin(ConfigScopedAdmin):pass
@admin.register(Prospecto)
class ProspectoAdmin(admin.ModelAdmin):
    list_display=("numero","nombre","empresa","estado","vendedor","fecha_proxima_accion");list_filter=("empresa","estado","fuente","vendedor");search_fields=("numero","nombre","nombre_comercial","identificacion_fiscal","correo");readonly_fields=("numero","estado","cliente_convertido","convertido_por","fecha_conversion","fecha_creacion","fecha_actualizacion")
    def has_delete_permission(self,request,obj=None):return False
@admin.register(OportunidadComercial)
class OportunidadAdmin(admin.ModelAdmin):
    list_display=("numero","titulo","empresa","etapa","monto_estimado","probabilidad","monto_ponderado");list_filter=("empresa","etapa","vendedor","moneda");search_fields=("numero","titulo");readonly_fields=("numero","etapa","monto_ponderado","cerrado_por","fecha_cierre_real","fecha_creacion","fecha_actualizacion")
    def has_delete_permission(self,request,obj=None):return False
@admin.register(ActividadComercial)
class ActividadCRMAdmin(admin.ModelAdmin):
    list_display=("asunto","empresa","tipo","estado","responsable","fecha_inicio");list_filter=("empresa","tipo","estado","prioridad");search_fields=("asunto","descripcion");readonly_fields=("estado","completado_por","fecha_creacion","fecha_actualizacion")
    def has_delete_permission(self,request,obj=None):return False
for model in (HistorialEstadoProspecto,HistorialEtapaOportunidad,HistorialActividadComercial):
    admin.site.register(model,type(f"{model.__name__}Admin",(admin.ModelAdmin,),{"readonly_fields":tuple(f.name for f in model._meta.fields),"has_add_permission":lambda self,request:False,"has_change_permission":lambda self,request,obj=None:False,"has_delete_permission":lambda self,request,obj=None:False}))
for model in (ProductoComercial,ListaPrecio,DetalleListaPrecio,ReglaPrecio,PoliticaDescuentoComercial,PromocionComercial,ReglaPromocion,CotizacionVenta,DetalleCotizacionVenta,ProgramacionPedido):
    admin.site.register(model,admin.ModelAdmin)
for model in (ReservaComercial,PreparacionPedido,TareaPicking,PackingPedido,DespachoComercial,ConduceComercial,EntregaComercial,FacturaVenta,CuentaPorCobrar,ReciboCobro,CesionFactoring):
    admin.site.register(model,admin.ModelAdmin)
for model in (VersionCotizacionVenta,HistorialCotizacionVenta):
    admin.site.register(model,type(f"{model.__name__}Admin",(admin.ModelAdmin,),{"readonly_fields":tuple(f.name for f in model._meta.fields),"has_add_permission":lambda self,request:False,"has_change_permission":lambda self,request,obj=None:False,"has_delete_permission":lambda self,request,obj=None:False}))
