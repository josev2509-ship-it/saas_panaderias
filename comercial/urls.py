from django.urls import path

from . import views

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
]
