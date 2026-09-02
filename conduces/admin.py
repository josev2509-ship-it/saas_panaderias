from django.contrib import admin
from .models import DiaNoDocencia

from .models import (
    Empresa,
    CentroEducativo,
    MenuDiario,
    Conduce,
    ProductoFacturacion,
    ComprobanteFiscal,
    RangoComprobanteGubernamental,
    Factura,
    DetalleFactura,
    CalendarioEscolar,
    DiaCalendarioEscolar,
    FechaOficialCalendario,
    AnalisisDocumentoCalendario,
    TotalMensualCalendario,
    EventoDocumentoCalendario,
    ProgramaMenu,
    VersionProgramaMenu,
    ItemCicloMenu,
    AsignacionProgramaCentro,
    ProgramacionMenuEscolar,
    ExcepcionProgramacionMenu,
)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rnc", "telefono", "ciudad", "numero_inicial_conduce")
    search_fields = ("nombre", "rnc", "telefono")


@admin.register(CentroEducativo)
class CentroEducativoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nombre",
        "director",
        "telefono",
        "provincia",
        "regional_distrito",
        "matricula",
        "latitud",
        "longitud",
    )
    search_fields = ("codigo", "nombre", "director", "provincia", "regional_distrito")
    list_filter = ("provincia", "regional_distrito")


@admin.register(MenuDiario)
class MenuDiarioAdmin(admin.ModelAdmin):
    list_display = ("fecha", "producto")
    search_fields = ("producto",)
    list_filter = ("fecha",)


@admin.register(Conduce)
class ConduceAdmin(admin.ModelAdmin):
    list_display = ("numero", "fecha", "empresa", "centro", "producto", "cantidad", "estado")
    search_fields = ("numero", "centro__nombre", "centro__codigo", "producto")
    list_filter = ("estado", "fecha", "producto")


@admin.register(CalendarioEscolar)
class CalendarioEscolarAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "inicio_docencia", "fin_docencia", "dias_docencia_oficiales", "estado")
    list_filter = ("estado", "empresa")


@admin.register(DiaCalendarioEscolar)
class DiaCalendarioEscolarAdmin(admin.ModelAdmin):
    list_display = ("fecha", "calendario", "clasificacion", "origen")
    list_filter = ("clasificacion", "calendario")


@admin.register(FechaOficialCalendario)
class FechaOficialCalendarioAdmin(admin.ModelAdmin):
    list_display = ("fecha", "anio_inicio", "anio_fin", "clasificacion", "motivo", "activa")
    list_filter = ("anio_inicio", "clasificacion", "activa")
    search_fields = ("motivo", "fuente")


@admin.register(AnalisisDocumentoCalendario)
class AnalisisDocumentoCalendarioAdmin(admin.ModelAdmin):
    list_display = ("nombre_original", "empresa", "proveedor", "estado", "confianza", "creado_en")
    list_filter = ("estado", "proveedor", "empresa")
    readonly_fields = ("hash_sha256", "texto_extraido", "datos_detectados", "advertencias")


admin.site.register(TotalMensualCalendario)
admin.site.register(EventoDocumentoCalendario)


admin.site.register(ProgramaMenu)
admin.site.register(VersionProgramaMenu)
admin.site.register(ItemCicloMenu)
admin.site.register(AsignacionProgramaCentro)
admin.site.register(ProgramacionMenuEscolar)
admin.site.register(ExcepcionProgramacionMenu)


@admin.register(ProductoFacturacion)
class ProductoFacturacionAdmin(admin.ModelAdmin):
    list_display = (
        "categoria",
        "nombre_factura",
        "precio_sin_itbis",
        "aplica_itbis",
        "porcentaje_itbis",
        "activo",
    )
    search_fields = ("nombre_factura", "categoria")
    list_filter = ("aplica_itbis", "activo")


@admin.register(ComprobanteFiscal)
class ComprobanteFiscalAdmin(admin.ModelAdmin):
    list_display = ("ncf", "tipo", "fecha_validez", "usado", "fecha_uso")
    search_fields = ("ncf",)
    list_filter = ("tipo", "usado", "fecha_validez")


@admin.register(RangoComprobanteGubernamental)
class RangoComprobanteGubernamentalAdmin(admin.ModelAdmin):
    list_display = ("prefijo", "numero_desde", "numero_hasta", "fecha_validez", "creado_en")
    search_fields = ("prefijo",)
    list_filter = ("fecha_validez",)


class DetalleFacturaInline(admin.TabularInline):
    model = DetalleFactura
    extra = 0
    readonly_fields = (
        "producto",
        "categoria",
        "cantidad",
        "precio_sin_itbis",
        "aplica_itbis",
        "valor",
    )


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "empresa",
        "comprobante",
        "fecha_factura",
        "fecha_inicio",
        "fecha_fin",
        "cantidad_conduces",
        "subtotal",
        "itbis",
        "total",
        "estado",
    )
    search_fields = ("comprobante__ncf", "cliente_nombre", "cliente_rnc")
    list_filter = ("estado", "fecha_factura", "empresa")
    inlines = [DetalleFacturaInline]


@admin.register(DetalleFactura)
class DetalleFacturaAdmin(admin.ModelAdmin):
    list_display = (
        "factura",
        "producto",
        "categoria",
        "cantidad",
        "precio_sin_itbis",
        "aplica_itbis",
        "valor",
    )
    search_fields = ("producto", "categoria")

    # =========================================
# DÍAS NO DOCENCIA / CALENDARIO ESCOLAR
# =========================================
@admin.register(DiaNoDocencia)
class DiaNoDocenciaAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "motivo",
        "tipo",
        "empresa",
        "activo",
    )

    list_filter = (
        "tipo",
        "activo",
        "empresa",
    )

    search_fields = (
        "motivo",
        "observacion",
    )

    ordering = ("fecha",)
