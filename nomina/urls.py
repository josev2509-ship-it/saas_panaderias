from django.urls import path
from . import views
app_name="nomina"
urlpatterns=[path("",views.dashboard,name="dashboard"),path("periodos/nuevo/",views.periodo_crear,name="periodo_crear"),path("periodos/<int:periodo_id>/calcular/",views.calcular,name="calcular"),path("<int:pk>/",views.detalle,name="detalle"),path("<int:pk>/estado/",views.estado,name="estado"),path("<int:pk>/exportar.csv",views.exportar,name="exportar"),path("conceptos/",views.conceptos,name="conceptos"),path("conceptos/nuevo/",views.concepto_crear,name="concepto_crear"),path("prestaciones/",views.prestaciones,name="prestaciones"),path("prestaciones/nueva/",views.prestacion_crear,name="prestacion_crear"),path("prestaciones/<int:pk>/",views.prestacion_detalle,name="prestacion_detalle")]
