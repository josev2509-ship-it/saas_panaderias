from django.urls import path

from . import views
from . import pedidos_views

app_name = "comercial"

urlpatterns = [
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
