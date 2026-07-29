from django.contrib import admin
from .models import Cliente, ContactoCliente, DetallePedido, DireccionCliente, HistorialEstadoPedido, Pedido


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
