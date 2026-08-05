from django.urls import path

from . import views
from . import experience_views

app_name = "core"

urlpatterns = [
    path("workspace/", experience_views.workspace_home, name="workspace_home"),
    path("workspace/<str:dominio>/", experience_views.workspace, name="workspace"),
    path("buscar/", experience_views.busqueda_global, name="busqueda_global"),
    path("favoritos/toggle/", experience_views.favorito_toggle, name="favorito_toggle"),
    path("alertas/", experience_views.alertas, name="alertas"),
    path("alertas/<int:pk>/<str:accion>/", experience_views.alerta_accion, name="alerta_accion"),
    path("actividad/", experience_views.actividad, name="actividad"),
    path("", views.motor_dashboard, name="motor_dashboard"),
    path("design-system/", views.design_system, name="design_system"),
    path("idempotencia/", views.idempotencias_lista, name="idempotencias"),
    path("idempotencia/<int:pk>/", views.idempotencia_detalle, name="idempotencia_detalle"),
    path("idempotencia/<int:pk>/cerrar/", views.idempotencia_cerrar, name="idempotencia_cerrar"),
    path("eventos/", views.eventos_lista, name="eventos"),
    path("eventos/<int:pk>/", views.evento_detalle, name="evento_detalle"),
    path("eventos/fallidos/", views.eventos_fallidos, name="eventos_fallidos"),
    path("eventos/<int:pk>/reintentar/", views.evento_reintentar, name="evento_reintentar"),
    path("secuencias/", views.secuencias_lista, name="secuencias"),
    path("secuencias/crear/", views.secuencia_crear, name="secuencia_crear"),
    path("secuencias/<int:pk>/", views.secuencia_detalle, name="secuencia_detalle"),
    path("secuencias/<int:pk>/editar/", views.secuencia_editar, name="secuencia_editar"),
    path("conciliaciones/", views.conciliaciones_lista, name="conciliaciones"),
    path("conciliaciones/<int:pk>/", views.conciliacion_detalle, name="conciliacion_detalle"),
    path("conciliaciones/diagnosticar/", views.diagnostico_producto, name="diagnostico_producto"),
    path("conciliaciones/reconstruir/", views.reconstruir_saldo, name="reconstruir_saldo"),
    path("conciliaciones/previsualizar/", views.previsualizar_saldo, name="previsualizar_saldo"),
]
