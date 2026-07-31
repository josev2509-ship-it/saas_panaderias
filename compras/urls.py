from django.urls import path
from . import views

app_name="compras"
urlpatterns=[
    path("",views.dashboard,name="dashboard"),
    path("proveedores/",views.lista,name="lista"),
    path("proveedores/nuevo/",views.editar,name="crear"),
    path("proveedores/exportar/",views.exportar,name="exportar"),
    path("proveedores/<int:pk>/",views.detalle,name="detalle"),
    path("proveedores/<int:pk>/editar/",views.editar,name="editar"),
    path("proveedores/<int:pk>/estado/<str:accion>/",views.estado,name="estado"),
    path("proveedores/<int:pk>/agregar/<str:tipo>/",views.agregar_relacion,name="agregar_relacion"),
    path("cuentas/<int:pk>/ver/",views.ver_cuenta,name="ver_cuenta"),
    path("cuentas/<int:pk>/<str:accion>/",views.revisar_cuenta,name="revisar_cuenta"),
    path("solicitudes/",views.solicitudes_lista,name="solicitudes_lista"),
    path("solicitudes/dashboard/",views.solicitudes_dashboard,name="solicitudes_dashboard"),
    path("solicitudes/nueva/",views.solicitud_editar,name="solicitud_crear"),
    path("solicitudes/exportar/",views.solicitudes_exportar,name="solicitudes_exportar"),
    path("solicitudes/<int:pk>/",views.solicitud_detalle,name="solicitud_detalle"),
    path("solicitudes/<int:pk>/editar/",views.solicitud_editar,name="solicitud_editar"),
    path("solicitudes/<int:pk>/lineas/agregar/",views.solicitud_linea_agregar,name="solicitud_linea_agregar"),
    path("solicitudes/<int:pk>/lineas/<int:linea_id>/retirar/",views.solicitud_linea_retirar,name="solicitud_linea_retirar"),
    path("solicitudes/<int:pk>/<str:accion>/",views.solicitud_accion,name="solicitud_accion"),
    path("expedientes/",views.expedientes_lista,name="expedientes_lista"),path("expedientes/<int:pk>/",views.expediente_detalle,name="expediente_detalle"),
    path("rfq/",views.rfq_lista,name="rfq_lista"),path("rfq/<int:pk>/",views.rfq_detalle,name="rfq_detalle"),
    path("p2p/dashboard/",views.p2p_dashboard,name="p2p_dashboard"),path("p2p/exportar/",views.p2p_exportar,name="p2p_exportar"),
    path("expedientes/<int:pk>/<str:accion>/",views.expediente_accion,name="expediente_accion"),path("expedientes/<int:expediente_id>/rfq/nueva/",views.rfq_crear_view,name="rfq_crear"),
    path("rfq/<int:pk>/accion/<str:accion>/",views.rfq_accion,name="rfq_accion"),path("invitaciones/<int:pk>/<str:accion>/",views.invitacion_accion,name="invitacion_accion"),
    path("rfq/lineas/<int:pk>/editar/",views.rfq_linea_editar,name="rfq_linea_editar"),
    path("solicitudes/<int:solicitud_id>/crear-expediente/",views.expediente_desde_solicitud_view,name="expediente_desde_solicitud"),path("rfq/<int:pk>/agregar/<str:tipo>/",views.rfq_agregar,name="rfq_agregar"),path("rfq/<int:pk>/extender/",views.rfq_extender_view,name="rfq_extender"),
    path("expedientes/<int:pk>/editar/",views.expediente_editar_view,name="expediente_editar"),path("rfq/<int:pk>/editar/",views.rfq_editar_view,name="rfq_editar"),path("invitaciones/<int:pk>/contacto/",views.invitacion_contacto,name="invitacion_contacto"),
]
