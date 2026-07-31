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
    RecetaProduccion, DetalleRecetaProduccion, PlanProduccion, DetallePlanProduccion,
    OrdenProduccion, NecesidadMateriaPrima, HistorialEstadoOrdenProduccion,
    ReservaInventario, DetalleReservaInventario, EjecucionInventarioOrden,
    ConsumoProduccion, MermaProduccion, DevolucionProduccion, LoteProduccion,
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
    readonly_fields = tuple(field.name for field in MovimientoInventario._meta.fields)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


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


class IngredienteProduccionInline(admin.TabularInline):
    model = DetalleRecetaProduccion
    extra = 0


@admin.register(RecetaProduccion)
class RecetaProduccionAdmin(admin.ModelAdmin):
    list_display = ("codigo","nombre","producto_terminado","version","rendimiento_base","activa","empresa")
    list_filter = ("empresa","activa","version")
    search_fields = ("codigo","nombre","producto_terminado__nombre")
    readonly_fields = ("creado_por","actualizado_por","fecha_creacion","fecha_actualizacion")
    inlines = (IngredienteProduccionInline,)
    def has_delete_permission(self, request, obj=None): return False


class DetallePlanInline(admin.TabularInline):
    model = DetallePlanProduccion
    extra = 0
    readonly_fields = tuple(f.name for f in DetallePlanProduccion._meta.fields)
    can_delete = False
    def has_add_permission(self, request, obj=None): return False


@admin.register(PlanProduccion)
class PlanProduccionAdmin(admin.ModelAdmin):
    list_display = ("numero","fecha_plan","origen","estado","empresa")
    list_filter = ("empresa","estado","origen","fecha_plan")
    search_fields = ("numero","observaciones")
    readonly_fields = ("numero","estado","creado_por","actualizado_por","aprobado_por","fecha_aprobacion","fecha_creacion","fecha_actualizacion")
    inlines = (DetallePlanInline,)
    def has_delete_permission(self, request, obj=None): return False


@admin.register(OrdenProduccion)
class OrdenProduccionAdmin(admin.ModelAdmin):
    list_display = ("numero","producto_terminado","fecha_programada","turno","estado","cantidad_planificada","empresa")
    list_filter = ("empresa","estado","turno","prioridad","fecha_programada")
    search_fields = ("numero","producto_terminado__nombre")
    readonly_fields = ("numero","estado","cantidad_iniciada","cantidad_producida","cantidad_rechazada","fecha_inicio_real","fecha_fin_real","creado_por","actualizado_por","fecha_creacion","fecha_actualizacion")
    def has_delete_permission(self, request, obj=None): return False


@admin.register(NecesidadMateriaPrima)
class NecesidadMateriaPrimaAdmin(admin.ModelAdmin):
    list_display = ("materia_prima","producto_terminado","cantidad_con_merma","fecha_requerida","estado","empresa")
    list_filter = ("empresa","estado","fecha_requerida")
    readonly_fields = tuple(f.name for f in NecesidadMateriaPrima._meta.fields)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(HistorialEstadoOrdenProduccion)
class HistorialEstadoOrdenAdmin(admin.ModelAdmin):
    list_display = ("orden","estado_anterior","estado_nuevo","usuario","fecha")
    readonly_fields = tuple(f.name for f in HistorialEstadoOrdenProduccion._meta.fields)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


class DetalleReservaInline(admin.TabularInline):
    model = DetalleReservaInventario
    extra = 0
    readonly_fields = tuple(f.name for f in DetalleReservaInventario._meta.fields)
    can_delete = False


@admin.register(ReservaInventario)
class ReservaInventarioAdmin(admin.ModelAdmin):
    list_display = ("numero", "orden", "estado", "empresa", "creado_en")
    list_filter = ("empresa", "estado")
    search_fields = ("numero", "orden__numero")
    readonly_fields = ("numero", "empresa", "orden", "estado", "creado_por", "creado_en", "actualizado_en")
    inlines = (DetalleReservaInline,)
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(EjecucionInventarioOrden)
class EjecucionInventarioOrdenAdmin(admin.ModelAdmin):
    list_display = ("orden", "estado", "empresa", "iniciado_en", "cerrado_en")
    list_filter = ("empresa", "estado")
    readonly_fields = tuple(f.name for f in EjecucionInventarioOrden._meta.fields)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


for modelo in (ConsumoProduccion, MermaProduccion, DevolucionProduccion, LoteProduccion):
    admin.site.register(modelo)
