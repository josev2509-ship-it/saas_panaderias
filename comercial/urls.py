from django.urls import path

from . import views
from . import pedidos_views
from . import configuracion_views
from . import crm_views
from . import o2c_views
from . import o2c_full_views

app_name = "comercial"

urlpatterns = [
    path("o2c/",o2c_full_views.dashboard,name="o2c_full_dashboard"),path("o2c/<str:tipo>/",o2c_full_views.listado,name="o2c_full_lista"),
    path("o2c/pedido/<int:pk>/reservar/",o2c_full_views.pedido_reservar,name="o2c_pedido_reservar"),path("o2c/reserva/<int:pk>/preparar/",o2c_full_views.reserva_preparar,name="o2c_reserva_preparar"),path("o2c/preparacion/<int:pk>/validar/",o2c_full_views.preparacion_validar,name="o2c_preparacion_validar"),path("o2c/picking/<int:pk>/completar/",o2c_full_views.picking_completar,name="o2c_picking_completar"),path("o2c/packing/<int:pk>/despachar/",o2c_full_views.packing_despachar,name="o2c_packing_despachar"),path("o2c/despacho/<int:pk>/conduce/",o2c_full_views.despacho_conduce,name="o2c_despacho_conduce"),path("o2c/conduce/<int:pk>/entregar/",o2c_full_views.conduce_entregar,name="o2c_conduce_entregar"),path("o2c/entrega/<int:pk>/facturar/",o2c_full_views.entrega_facturar,name="o2c_entrega_facturar"),path("o2c/cxc/<int:pk>/cobrar/",o2c_full_views.cobrar,name="o2c_cobrar"),path("o2c/exportar/<str:tipo>/<str:formato>/",o2c_full_views.exportar,name="o2c_full_exportar"),
    path("o2c/",o2c_views.dashboard,name="o2c_dashboard"),path("clientes/<int:pk>/360/",o2c_views.cliente_360,name="cliente_360"),path("clientes/<int:pk>/360/<str:accion>/",o2c_views.cliente_accion,name="cliente_360_accion"),
    path("productos-comerciales/",o2c_views.productos_lista,name="productos_comerciales"),path("productos-comerciales/nuevo/",o2c_views.producto_form,name="producto_comercial_crear"),path("productos-comerciales/<int:pk>/",o2c_views.producto_detalle,name="producto_detalle"),path("productos-comerciales/<int:pk>/editar/",o2c_views.producto_form,name="producto_editar"),
    path("precios/listas/",o2c_views.listas,name="listas_precio"),path("precios/listas/nueva/",o2c_views.lista_form,name="lista_crear"),path("precios/listas/<int:pk>/",o2c_views.lista_detalle,name="lista_detalle"),path("precios/listas/<int:pk>/editar/",o2c_views.lista_form,name="lista_editar"),path("precios/listas/<int:pk>/activar/",o2c_views.lista_activar,name="lista_activar"),path("precios/simulador/",o2c_views.simulador,name="simulador_precio"),
    path("cotizaciones/",o2c_views.cotizaciones_lista,name="cotizaciones_lista"),path("cotizaciones/nueva/",o2c_views.cotizacion_form,name="cotizacion_crear"),path("cotizaciones/<int:pk>/",o2c_views.cotizacion_detalle,name="cotizacion_detalle"),path("cotizaciones/<int:pk>/editar/",o2c_views.cotizacion_form,name="cotizacion_editar"),path("cotizaciones/<int:pk>/pdf/",o2c_views.cotizacion_pdf,name="cotizacion_pdf"),path("cotizaciones/<int:pk>/<str:accion>/",o2c_views.cotizacion_accion,name="cotizacion_accion"),
    path("programacion-comercial/",o2c_views.programacion,name="programacion_comercial"),path("programacion-comercial/<str:vista>/",o2c_views.programacion,name="programacion_comercial_vista"),path("o2c/reportes/",o2c_views.reportes,name="o2c_reportes"),path("o2c/exportar/<str:tipo>/<str:formato>/",o2c_views.exportar,name="o2c_exportar"),
    path("crm/",crm_views.dashboard,name="crm_dashboard"),
    path("crm/prospectos/",crm_views.prospectos_lista,name="prospectos_lista"),path("crm/prospectos/nuevo/",crm_views.prospecto_form,name="prospecto_crear"),path("crm/prospectos/<int:pk>/",crm_views.prospecto_detalle,name="prospecto_detalle"),path("crm/prospectos/<int:pk>/editar/",crm_views.prospecto_form,name="prospecto_editar"),path("crm/prospectos/<int:pk>/<str:accion>/",crm_views.prospecto_accion,name="prospecto_accion"),
    path("crm/oportunidades/",crm_views.oportunidades_lista,name="oportunidades_lista"),path("crm/oportunidades/nueva/",crm_views.oportunidad_form,name="oportunidad_crear"),path("crm/oportunidades/<int:pk>/",crm_views.oportunidad_detalle,name="oportunidad_detalle"),path("crm/oportunidades/<int:pk>/editar/",crm_views.oportunidad_form,name="oportunidad_editar"),path("crm/oportunidades/<int:pk>/<str:accion>/",crm_views.oportunidad_accion,name="oportunidad_accion"),path("crm/pipeline/",crm_views.pipeline_view,name="pipeline"),
    path("crm/actividades/",crm_views.actividades_lista,name="actividades_lista"),path("crm/actividades/nueva/",crm_views.actividad_form,name="actividad_crear"),path("crm/actividades/<int:pk>/",crm_views.actividad_detalle,name="actividad_detalle"),path("crm/actividades/<int:pk>/editar/",crm_views.actividad_form,name="actividad_editar"),path("crm/actividades/<int:pk>/<str:accion>/",crm_views.actividad_accion,name="actividad_accion"),path("crm/agenda/",crm_views.agenda_view,name="agenda"),path("crm/agenda/<str:vista>/",crm_views.agenda_view,name="agenda_vista"),
    path("crm/masivo/<str:tipo>/<str:accion>/",crm_views.accion_masiva,name="crm_accion_masiva"),path("crm/reportes/",crm_views.reportes,name="crm_reportes"),path("crm/exportar/<str:tipo>/<str:formato>/",crm_views.exportar,name="crm_exportar"),
    path("configuracion/", configuracion_views.dashboard, name="configuracion_dashboard"),
    path("configuracion/editar/", configuracion_views.configuracion_editar, name="configuracion_editar"),
    path("configuracion/validar/", configuracion_views.readiness_ejecutar, name="readiness_ejecutar"),
    path("configuracion/catalogos/<str:tipo>/", configuracion_views.catalogo_lista, name="catalogo_lista"),
    path("configuracion/catalogos/<str:tipo>/nuevo/", configuracion_views.catalogo_editar, name="catalogo_crear"),
    path("configuracion/catalogos/<str:tipo>/<int:pk>/", configuracion_views.catalogo_detalle, name="catalogo_detalle"),
    path("configuracion/catalogos/<str:tipo>/<int:pk>/editar/", configuracion_views.catalogo_editar, name="catalogo_editar"),
    path("configuracion/catalogos/<str:tipo>/<int:pk>/estado/", configuracion_views.catalogo_estado, name="catalogo_estado"),
    path("configuracion/politicas/<str:tipo>/", configuracion_views.politica_lista, name="politica_lista"),
    path("configuracion/politicas/<str:tipo>/nueva/", configuracion_views.politica_editar, name="politica_crear"),
    path("configuracion/politicas/<str:tipo>/<int:pk>/", configuracion_views.politica_detalle, name="politica_detalle"),
    path("configuracion/politicas/<str:tipo>/<int:pk>/editar/", configuracion_views.politica_editar, name="politica_editar"),
    path("configuracion/politicas/<str:tipo>/<int:pk>/<str:accion>/", configuracion_views.politica_accion, name="politica_accion"),
    path("configuracion/secuencias/", configuracion_views.secuencias, name="secuencias"),
    path("configuracion/reportes/", configuracion_views.reportes, name="configuracion_reportes"),
    path("configuracion/exportar/<str:formato>/", configuracion_views.exportar, name="configuracion_exportar"),
    path("", views.dashboard, name="dashboard"),
    path("clientes/", views.clientes_lista, name="clientes_lista"),
    path("clientes/nuevo/", views.cliente_crear, name="cliente_crear"),
    path("clientes/<int:pk>/", views.cliente_detalle, name="cliente_detalle"),
    path("clientes/<int:pk>/editar/", views.cliente_editar, name="cliente_editar"),
    path("clientes/<int:pk>/estado/", views.cliente_cambiar_estado, name="cliente_cambiar_estado"),
    path("clientes/<int:cliente_pk>/direcciones/nueva/", views.direccion_crear, name="direccion_crear"),
    path("direcciones/<int:pk>/editar/", views.direccion_editar, name="direccion_editar"),
    path("clientes/<int:cliente_pk>/contactos/nuevo/", views.contacto_crear, name="contacto_crear"),
    path("contactos/<int:pk>/editar/", views.contacto_editar, name="contacto_editar"),
    path("pedidos/dashboard/", pedidos_views.pedidos_dashboard, name="pedidos_dashboard"),
    path("pedidos/", pedidos_views.pedidos_lista, name="pedidos_lista"),
    path("pedidos/nuevo/", pedidos_views.pedido_crear, name="pedido_crear"),
    path("pedidos/<int:pk>/", pedidos_views.pedido_detalle, name="pedido_detalle"),
    path("pedidos/<int:pk>/editar/", pedidos_views.pedido_editar, name="pedido_editar"),
    path("pedidos/<int:pk>/enviar/", pedidos_views.pedido_enviar_aprobacion, name="pedido_enviar_aprobacion"),
    path("pedidos/<int:pk>/aprobar/", pedidos_views.pedido_aprobar, name="pedido_aprobar"),
    path("pedidos/<int:pk>/rechazar/", pedidos_views.pedido_rechazar, name="pedido_rechazar"),
    path("pedidos/<int:pk>/reabrir/", pedidos_views.pedido_reabrir, name="pedido_reabrir"),
    path("pedidos/<int:pk>/cancelar/", pedidos_views.pedido_cancelar, name="pedido_cancelar"),
    path("pedidos/<int:pk>/duplicar/", pedidos_views.pedido_duplicar, name="pedido_duplicar"),
    path("programacion/diaria/", pedidos_views.programacion_diaria, name="programacion_diaria"),
    path("programacion/semanal/", pedidos_views.programacion_semanal, name="programacion_semanal"),
]
