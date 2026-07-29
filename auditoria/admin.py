from django.contrib import admin
from .models import EventoAuditoria


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "empresa", "usuario", "modulo", "accion", "descripcion")
    list_filter = ("empresa", "modulo", "accion", "fecha")
    search_fields = ("descripcion", "usuario__username", "object_id")
    readonly_fields = tuple(field.name for field in EventoAuditoria._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
