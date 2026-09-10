from django.urls import path
from . import views
from . import produccion_views
from . import produccion_inabie_views

app_name = "inventario"

urlpatterns = [
    path("produccion/dashboard/", produccion_views.produccion_dashboard, name="produccion_dashboard"),
    path("produccion/recetas/", produccion_views.recetas_lista, name="recetas_lista"),
    path("produccion/recetas/nueva/", produccion_views.receta_crear, name="receta_crear"),
    path("produccion/recetas/<int:pk>/", produccion_views.receta_detalle, name="receta_detalle"),
    path("produccion/recetas/<int:pk>/editar/", produccion_views.receta_editar, name="receta_editar"),
    path("produccion/recetas/<int:pk>/duplicar/", produccion_views.receta_duplicar, name="receta_duplicar"),
    path("produccion/recetas/<int:pk>/estado/", produccion_views.receta_cambiar_estado, name="receta_cambiar_estado"),
    path("produccion/planes/", produccion_views.planes_lista, name="planes_lista"),
    path("produccion/planes/nuevo/", produccion_views.plan_crear, name="plan_crear"),
    path("produccion/planes/generar-pedidos/", produccion_views.plan_generar_desde_pedidos, name="plan_generar_desde_pedidos"),
    path("produccion/planes/<int:pk>/", produccion_views.plan_detalle, name="plan_detalle"),
    path("produccion/planes/<int:pk>/editar/", produccion_views.plan_editar, name="plan_editar"),
    path("produccion/planes/<int:pk>/aprobar/", produccion_views.plan_aprobar, name="plan_aprobar"),
    path("produccion/planes/<int:pk>/cancelar/", produccion_views.plan_cancelar, name="plan_cancelar"),
    path("produccion/planes/<int:pk>/generar-ordenes/", produccion_views.plan_generar_ordenes, name="plan_generar_ordenes"),
    path("produccion/ordenes/", produccion_views.ordenes_lista, name="ordenes_lista"),
    path("produccion/ordenes/nueva/", produccion_views.orden_crear, name="orden_crear"),
    path("produccion/ordenes/<int:pk>/", produccion_views.orden_detalle, name="orden_detalle"),
    path("produccion/ordenes/<int:pk>/editar/", produccion_views.orden_editar, name="orden_editar"),
    path("produccion/ordenes/<int:pk>/programar/", produccion_views.orden_programar, name="orden_programar"),
    path("produccion/ordenes/<int:pk>/iniciar/", produccion_views.orden_iniciar, name="orden_iniciar"),
    path("produccion/ordenes/<int:pk>/completar/", produccion_views.orden_completar, name="orden_completar"),
    path("produccion/ordenes/<int:pk>/cancelar/", produccion_views.orden_cancelar, name="orden_cancelar"),
    path("produccion/programacion/diaria/", produccion_views.produccion_programacion_diaria, name="produccion_programacion_diaria"),
    path("produccion/programacion/semanal/", produccion_views.produccion_programacion_semanal, name="produccion_programacion_semanal"),
    path("produccion/necesidades/", produccion_views.necesidades_materia_prima, name="necesidades_materia_prima"),
    path("produccion/inabie/generar/", produccion_inabie_views.generar_orden, name="orden_inabie_generar"),
    path("produccion/ordenes/<int:pk>/ajustar/", produccion_inabie_views.ajustar_orden, name="orden_inabie_ajustar"),
    path("produccion/ordenes/<int:pk>/iniciar-inabie/", produccion_inabie_views.iniciar, name="orden_inabie_iniciar"),
    path("produccion/ordenes/<int:pk>/cerrar/", produccion_inabie_views.cerrar, name="orden_inabie_cerrar"),
    path("produccion/ordenes/<int:pk>/pdf/", produccion_inabie_views.orden_pdf, name="orden_pdf"),
    path("produccion/ordenes/<int:pk>/cambio-producto/", produccion_inabie_views.cambio_producto, name="orden_cambio_producto"),
    path("produccion/ordenes/<int:pk>/cambio-producto/<int:solicitud_pk>/decidir/", produccion_inabie_views.decidir_cambio, name="orden_cambio_producto_decidir"),
    path("produccion/proyeccion-materia-prima/", produccion_inabie_views.proyeccion, name="proyeccion_materia_prima"),

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
