from django.contrib import admin
from .models import Cliente, ContactoCliente, DireccionCliente


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
