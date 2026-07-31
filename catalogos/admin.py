from django.contrib import admin

from conduces.services import obtener_empresa_usuario
from .models import Almacen, CentroCosto, CondicionPago, ConversionUnidad, Impuesto, Moneda, MonedaEmpresa, TipoCompra, UnidadMedida


class EmpresaAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        empresa = obtener_empresa_usuario(request)
        return qs.filter(empresa=empresa) if empresa else qs.none()

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "empresa_id") and not obj.empresa_id:
            obj.empresa = obtener_empresa_usuario(request)
        super().save_model(request, obj, form, change)


admin.site.register(Moneda)
for model in (MonedaEmpresa, CondicionPago, UnidadMedida, ConversionUnidad, Almacen, CentroCosto, Impuesto, TipoCompra):
    admin.site.register(model, EmpresaAdmin)
