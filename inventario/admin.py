from django.contrib import admin

from .models import (
    CategoriaInventario,
    ProductoInventario,
    ProductoProduccion,
    Receta,
    DetalleReceta,
    MovimientoInventario,
    ProduccionProgramada,
    PrestamoMateriaPrima,
    OrdenCompra,
    DetalleOrdenCompra,
    LoteInventario,
)


class DetalleRecetaInline(admin.TabularInline):
    model = DetalleReceta
    extra = 1


class DetalleOrdenCompraInline(admin.TabularInline):
    model = DetalleOrdenCompra
    extra = 1


@admin.register(CategoriaInventario)
class CategoriaInventarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "empresa", "activa")
    list_filter = ("tipo", "activa", "empresa")
    search_fields = ("nombre",)


@admin.register(ProductoInventario)
class ProductoInventarioAdmin(admin.ModelAdmin):

    list_display = (
        "codigo",
        "nombre",
        "tipo",
        "unidad_medida",
        "unidad_compra",
        "existencia_visual",
        "stock_minimo",
        "precio_unitario_compra",
        "porcentaje_itbis",
        "estado_stock",
        "activo",
    )

    list_filter = (
        "tipo",
        "unidad_medida",
        "activo",
    )

    search_fields = (
        "codigo",
        "nombre",
    )

    list_per_page = 30

    fieldsets = (

        ("Información general", {
            "fields": (
                "empresa",
                "categoria",
                "codigo",
                "nombre",
                "tipo",
                "activo",
            )
        }),

        ("Unidades y empaques", {
            "fields": (
                "unidad_medida",
                "unidad_compra",
                "cantidad_por_empaque",
            )
        }),

        ("Inventario", {
            "fields": (
                "stock_actual",
                "stock_minimo",
            )
        }),

        ("Compras y costos", {
            "fields": (
                "precio_unitario_compra",
                "porcentaje_itbis",
                "proveedor",
            )
        }),
    )

    def existencia_visual(self, obj):
        return obj.existencia_formateada()

    existencia_visual.short_description = "Existencia"

    def estado_stock(self, obj):

        if obj.esta_bajo_minimo():
            return "⚠ Bajo"

        return "✅ Normal"

    estado_stock.short_description = "Estado"

    list_display = (
        "nombre",
        "tipo",
        "unidad_medida",
        "stock_actual",
        "stock_minimo",
        "costo_unitario",
        "empresa",
        "activo",
    )
    list_filter = ("tipo", "unidad_medida", "activo", "empresa")
    search_fields = ("nombre", "codigo")


@admin.register(ProductoProduccion)
class ProductoProduccionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "empresa", "activo")
    list_filter = ("tipo", "activo", "empresa")
    search_fields = ("nombre",)


@admin.register(Receta)
class RecetaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "producto", "rendimiento_unidades", "empresa", "activa")
    list_filter = ("activa", "empresa", "producto")
    search_fields = ("nombre", "producto__nombre")
    inlines = [DetalleRecetaInline]


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "tipo",
        "producto",
        "cantidad",
        "costo_unitario",
        "empresa",
        "usuario",
    )
    list_filter = ("tipo", "fecha", "empresa")
    search_fields = ("producto__nombre", "referencia", "observacion")


@admin.register(ProduccionProgramada)
class ProduccionProgramadaAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "producto",
        "receta",
        "cantidad_unidades",
        "estado",
        "empresa",
        "usuario",
    )
    list_filter = ("estado", "fecha", "empresa")
    search_fields = ("producto__nombre", "receta__nombre")


@admin.register(PrestamoMateriaPrima)
class PrestamoMateriaPrimaAdmin(admin.ModelAdmin):
    list_display = (
        "fecha_prestamo",
        "tipo",
        "producto",
        "tercero",
        "cantidad",
        "cantidad_devuelta",
        "estado",
        "empresa",
    )
    list_filter = ("tipo", "estado", "fecha_prestamo", "empresa")
    search_fields = ("producto__nombre", "tercero", "responsable_entrega", "responsable_recibe")


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "proveedor",
        "fecha",
        "fecha_requerida",
        "estado",
        "empresa",
        "creada_por",
    )
    list_filter = ("estado", "fecha", "empresa")
    search_fields = ("numero", "proveedor", "observacion")
    inlines = [DetalleOrdenCompraInline]

    # =========================================
# LOTES INVENTARIO
# =========================================

@admin.register(LoteInventario)
class LoteInventarioAdmin(admin.ModelAdmin):

    list_display = (
        "producto",
        "lote",
        "fecha_ingreso",
        "fecha_vencimiento",
        "cantidad_inicial",
        "cantidad_disponible",
        "estado_vencimiento",
        "proveedor",
    )

    list_filter = (
        "fecha_ingreso",
        "fecha_vencimiento",
        "empresa",
    )

    search_fields = (
        "producto__nombre",
        "lote",
        "proveedor",
        "factura",
    )

    list_per_page = 30

    fieldsets = (

        ("Información general", {
            "fields": (
                "empresa",
                "producto",
                "lote",
            )
        }),

        ("Fechas", {
            "fields": (
                "fecha_ingreso",
                "fecha_vencimiento",
            )
        }),

        ("Cantidades", {
            "fields": (
                "cantidad_inicial",
                "cantidad_disponible",
            )
        }),

        ("Proveedor y factura", {
            "fields": (
                "proveedor",
                "factura",
            )
        }),

        ("Otros", {
            "fields": (
                "observacion",
                "creado_por",
            )
        }),
    )

    def estado_vencimiento(self, obj):

        if obj.esta_vencido():
            return "❌ Vencido"

        dias = obj.dias_para_vencer()

        if dias is not None and dias <= 15:
            return f"⚠ {dias} días"

        return "✅ Vigente"

    estado_vencimiento.short_description = "Estado"