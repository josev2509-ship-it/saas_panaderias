from django.contrib import admin
from .models import Documento, TipoDocumento


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "empresa", "requiere_vencimiento", "activo")
    list_filter = ("empresa", "requiere_vencimiento", "activo")
    search_fields = ("codigo", "nombre", "descripcion")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "empresa", "tipo_documento", "version", "estado", "fecha_creacion")
    list_filter = ("empresa", "tipo_documento", "estado", "confidencial")
    search_fields = ("titulo", "descripcion", "nombre_original")
    readonly_fields = (
        "empresa", "archivo", "nombre_original", "extension", "tamano_bytes", "estado",
        "version", "documento_anterior", "creado_por", "content_type", "object_id",
        "fecha_creacion", "fecha_actualizacion",
    )
