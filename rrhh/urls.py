from django.urls import path
from . import views
app_name="rrhh"
urlpatterns=[
 path("",views.dashboard,name="dashboard"),path("reportes/empleados.csv",views.reporte_empleados,name="reporte_empleados"),
 path("empleados/",views.empleados,name="empleados"),path("empleados/nuevo/",views.empleado_form,name="empleado_crear"),path("empleados/<int:pk>/",views.empleado_360,name="empleado_360"),path("empleados/<int:pk>/editar/",views.empleado_form,name="empleado_editar"),path("empleados/<int:pk>/documentos/nuevo/",views.documento_cargar,name="documento_cargar"),path("empleados/<int:pk>/cursos/nuevo/",views.curso_asignar,name="curso_asignar"),
 path("<str:recurso>/",views.recurso_lista,name="recurso_lista"),path("<str:recurso>/nuevo/",views.recurso_crear,name="recurso_crear"),path("<str:recurso>/<int:pk>/estado/",views.recurso_estado,name="recurso_estado")]
