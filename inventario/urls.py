from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [

    # =====================================================
    # DASHBOARD
    # =====================================================
    path("", views.dashboard_inventario, name="dashboard"),

    # =====================================================
    # PRODUCTOS / INVENTARIO
    # =====================================================
    path("productos/", views.productos_inventario, name="productos"),
    path("producto/<int:producto_id>/editar/", views.editar_producto_inventario, name="editar_producto_inventario"),
    path("producto/<int:producto_id>/desactivar/", views.desactivar_producto_inventario, name="desactivar_producto_inventario"),
    path("producto/<int:producto_id>/kardex/", views.kardex_producto, name="kardex_producto"),

    path("plantilla-excel/", views.descargar_plantilla_inventario, name="descargar_plantilla"),
    path("cargar-excel/", views.cargar_inventario_excel, name="cargar_excel"),
    path("inventario/pdf/", views.pdf_inventario, name="pdf_inventario"),

    # =====================================================
    # MOVIMIENTOS
    # =====================================================
    path("movimientos/", views.movimientos, name="movimientos"),
    path("movimiento/registrar/", views.registrar_movimiento_manual, name="registrar_movimiento_manual"),

    # =====================================================
    # RECETAS
    # =====================================================
    path("recetas/", views.recetas, name="recetas"),
    path("recetas/producto/crear/", views.crear_producto_produccion, name="crear_producto_produccion"),
    path("recetas/crear/", views.crear_receta, name="crear_receta"),
    path("recetas/<int:receta_id>/", views.detalle_receta, name="detalle_receta"),
    path("recetas/<int:receta_id>/ingrediente/agregar/", views.agregar_ingrediente_receta, name="agregar_ingrediente_receta"),
    path("recetas/ingrediente/<int:detalle_id>/eliminar/", views.eliminar_ingrediente_receta, name="eliminar_ingrediente_receta"),

    # =====================================================
    # PRODUCCIÓN
    # =====================================================
    path("produccion/", views.produccion, name="produccion"),
    path("produccion/generar/", views.generar_produccion_desde_menu, name="generar_produccion_desde_menu"),
    path("produccion/<int:produccion_id>/", views.detalle_produccion, name="detalle_produccion"),
    path("produccion/<int:produccion_id>/ejecutar/", views.ejecutar_produccion, name="ejecutar_produccion"),
    path("produccion/<int:produccion_id>/consumo-manual/", views.registrar_consumo_manual, name="registrar_consumo_manual"),

    # =====================================================
    # PROYECCIÓN
    # =====================================================
    path("proyeccion/generar/", views.generar_proyeccion_consumo, name="generar_proyeccion_consumo"),

    # =====================================================
    # PRÉSTAMOS
    # =====================================================
    path("prestamos/", views.prestamos, name="prestamos"),
    path("prestamos/crear/", views.crear_prestamo, name="crear_prestamo"),
path("prestamos/<int:prestamo_id>/devolucion/", views.registrar_devolucion_prestamo, name="registrar_devolucion_prestamo"),

    # =====================================================
    # ÓRDENES DE COMPRA
    # =====================================================
    path("ordenes-compra/", views.ordenes_compra, name="ordenes_compra"),
    path("ordenes-compra/generar/", views.generar_orden_compra_sugerida, name="generar_orden_compra"),

    path("orden-compra/<int:orden_id>/", views.detalle_orden_compra, name="detalle_orden_compra"),
    path("orden-compra/<int:orden_id>/calcular/", views.calcular_orden_compra, name="calcular_orden_compra"),
    path("orden-compra/<int:orden_id>/pdf/", views.pdf_orden_compra, name="pdf_orden_compra"),
    path("orden-compra/<int:orden_id>/pdf/descargar/", views.descargar_pdf_orden_compra, name="descargar_pdf_orden_compra"),
    path("orden-compra/<int:orden_id>/agregar-producto/", views.agregar_producto_manual_orden, name="agregar_producto_manual_orden"),
    path("orden-compra/<int:orden_id>/recibir/", views.recibir_orden_compra, name="recibir_orden_compra"),
    path("orden-compra/<int:orden_id>/eliminar/", views.eliminar_orden_compra, name="eliminar_orden_compra"),

    path("detalle-orden/<int:detalle_id>/actualizar/", views.actualizar_detalle_orden, name="actualizar_detalle_orden"),
    path("detalle-orden/<int:detalle_id>/eliminar/", views.eliminar_detalle_orden, name="eliminar_detalle_orden"),
]