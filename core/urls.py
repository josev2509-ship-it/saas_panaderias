from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.motor_dashboard, name="motor_dashboard"),
    path("idempotencia/", views.idempotencias_lista, name="idempotencias"),
    path("idempotencia/<int:pk>/", views.idempotencia_detalle, name="idempotencia_detalle"),
    path("eventos/", views.eventos_lista, name="eventos"),
    path("eventos/<int:pk>/", views.evento_detalle, name="evento_detalle"),
    path("eventos/fallidos/", views.eventos_fallidos, name="eventos_fallidos"),
    path("eventos/<int:pk>/reintentar/", views.evento_reintentar, name="evento_reintentar"),
    path("secuencias/", views.secuencias_lista, name="secuencias"),
    path("secuencias/<int:pk>/", views.secuencia_detalle, name="secuencia_detalle"),
    path("secuencias/<int:pk>/editar/", views.secuencia_editar, name="secuencia_editar"),
    path("conciliaciones/", views.conciliaciones_lista, name="conciliaciones"),
    path("conciliaciones/<int:pk>/", views.conciliacion_detalle, name="conciliacion_detalle"),
    path("conciliaciones/diagnosticar/", views.diagnostico_producto, name="diagnostico_producto"),
    path("conciliaciones/reconstruir/", views.reconstruir_saldo, name="reconstruir_saldo"),
]
