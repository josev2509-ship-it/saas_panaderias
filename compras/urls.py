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
]
