from django.contrib import admin

from .models import (
    CategoriaProveedor, ContactoProveedor, CuentaBancariaProveedor,
    DireccionProveedor, HistorialEstadoProveedor, ProductoProveedor, Proveedor,
    ProveedorLegadoMap, RequisitoDocumentoProveedor, RevisionDocumentoProveedor,
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


for model in (CategoriaProveedor,ContactoProveedor,DireccionProveedor,ProductoProveedor,
              ProveedorLegadoMap,RequisitoDocumentoProveedor,
              RevisionDocumentoProveedor,HistorialEstadoProveedor):
    admin.site.register(model,EmpresaScopedAdmin)
