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
]
