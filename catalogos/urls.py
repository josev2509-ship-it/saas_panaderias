from django.urls import path

from . import views

app_name = "catalogos"
urlpatterns = [
    path("", views.centro, name="centro"),
    path("<slug:clave>/", views.lista, name="lista"),
    path("<slug:clave>/nuevo/", views.editar, name="crear"),
    path("<slug:clave>/<int:pk>/editar/", views.editar, name="editar"),
    path("<slug:clave>/<int:pk>/actividad/", views.actividad, name="actividad"),
]
