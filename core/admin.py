from django.contrib import admin

from .models import ConciliacionInventario, EventoDominio, RegistroIdempotencia
from comercial.models import SecuenciaDocumento
from conduces.services import obtener_empresa_usuario


class ImmutableAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        empresa = obtener_empresa_usuario(request)
        return queryset.filter(empresa=empresa) if empresa else queryset.none()


@admin.register(RegistroIdempotencia)
class RegistroIdempotenciaAdmin(ImmutableAdmin):
    list_display = ("operacion", "clave", "estado", "empresa", "fecha_inicio", "fecha_finalizacion")
    list_filter = ("empresa", "estado", "operacion")
    search_fields = ("clave", "referencia", "resultado_referencia")
    readonly_fields = tuple(field.name for field in RegistroIdempotencia._meta.fields)


@admin.register(EventoDominio)
class EventoDominioAdmin(ImmutableAdmin):
    list_display = ("tipo_evento", "agregado_tipo", "agregado_id", "estado", "empresa", "fecha_creacion")
    list_filter = ("empresa", "estado", "tipo_evento")
    search_fields = ("referencia", "clave_idempotente", "agregado_id")
    readonly_fields = tuple(field.name for field in EventoDominio._meta.fields)


@admin.register(ConciliacionInventario)
class ConciliacionInventarioAdmin(ImmutableAdmin):
    list_display = ("producto", "estado", "modo", "saldo_movimientos", "saldo_cacheado", "saldo_lotes", "empresa", "fecha")
    list_filter = ("empresa", "estado", "modo")
    search_fields = ("producto__codigo", "producto__nombre", "motivo")
    readonly_fields = tuple(field.name for field in ConciliacionInventario._meta.fields)


@admin.register(SecuenciaDocumento)
class SecuenciaDocumentoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "prefijo", "periodo", "ultimo_numero", "activo", "empresa")
    list_filter = ("empresa", "tipo", "periodo", "activo")
    search_fields = ("tipo", "prefijo")
    readonly_fields = ("empresa", "tipo", "periodo", "ultimo_numero", "fecha_ultima_emision", "creado_por", "fecha_creacion")
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.has_perm("core.manage_document_sequences")
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        empresa = obtener_empresa_usuario(request)
        return queryset.filter(empresa=empresa) if empresa else queryset.none()
