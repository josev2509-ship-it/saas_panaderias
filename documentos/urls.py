from django.urls import path
from . import views

app_name = "documentos"

urlpatterns = [
    path("", views.documentos_lista, name="lista"),
    path("objeto/<str:app_label>/<str:model>/<int:object_id>/", views.documentos_objeto, name="objeto"),
    path("objeto/<str:app_label>/<str:model>/<int:object_id>/cargar/", views.documento_cargar, name="cargar"),
    path("<int:pk>/", views.documento_detalle, name="detalle"),
    path("<int:pk>/descargar/", views.documento_descargar, name="descargar"),
    path("<int:pk>/reemplazar/", views.documento_reemplazar, name="reemplazar"),
    path("<int:pk>/anular/", views.documento_anular, name="anular"),
]
