from django.urls import path

from . import views

app_name = "nomina"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("periodos/nuevo/", views.periodo_crear, name="periodo_crear"),
    path("periodos/<int:periodo_id>/calcular/", views.calcular, name="calcular"),
    path("novedades/nueva/", views.novedad_crear, name="novedad_crear"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/estado/", views.estado, name="estado"),
    path("<int:pk>/empleados/<int:detalle_id>/", views.empleado_detalle, name="empleado_detalle"),
    path("<int:pk>/empleados/<int:detalle_id>/volante.pdf", views.volante_pdf, name="volante_pdf"),
    path("<int:pk>/volantes.zip", views.volantes_zip, name="volantes_zip"),
    path("<int:pk>/nomina.pdf", views.nomina_pdf, name="nomina_pdf"),
    path("<int:pk>/exportar.csv", views.exportar, name="exportar"),
    path("<int:pk>/exportar.xlsx", views.exportar_excel, name="exportar_excel"),
    path("conceptos/", views.conceptos, name="conceptos"),
    path("conceptos/nuevo/", views.concepto_crear, name="concepto_crear"),
    path("prestaciones/", views.prestaciones, name="prestaciones"),
    path("prestaciones/nueva/", views.prestacion_crear, name="prestacion_crear"),
    path("prestaciones/<int:pk>/", views.prestacion_detalle, name="prestacion_detalle"),
    path("prestaciones/<int:pk>/recalcular/", views.prestacion_recalcular, name="prestacion_recalcular"),
    path("prestaciones/<int:pk>/calculo.pdf", views.prestacion_pdf, name="prestacion_pdf"),
    path("prestaciones/<int:pk>/carta.pdf", views.liquidacion_carta, name="liquidacion_carta"),
    path("plantillas/", views.plantillas, name="plantillas"),
    path("plantillas/nueva/", views.plantilla_editar, name="plantilla_crear"),
    path("plantillas/<int:pk>/", views.plantilla_editar, name="plantilla_editar"),
    path("prestamos/", views.prestamos, name="prestamos"),
    path("prestamos/nuevo/", views.prestamo_crear, name="prestamo_crear"),
    path("prestamos/<int:pk>/", views.prestamo_detalle, name="prestamo_detalle"),
    path("prestamos/<int:pk>/estado.pdf", views.prestamo_pdf, name="prestamo_pdf"),
    path("documentos/empleados/<int:empleado_id>/<str:tipo>/", views.documento_empleado, name="documento_empleado"),
]
