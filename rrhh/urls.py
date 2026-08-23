from django.urls import include,path
from . import views,workforce_views
app_name="rrhh"
urlpatterns=[
 path("",views.dashboard,name="dashboard"),
 path("configuracion/",views.configuracion,name="configuracion"),
 path("asistencia/",workforce_views.ponches,name="ponches"),path("asistencia/nuevo/",workforce_views.ponche_form,name="ponche_crear"),path("asistencia/<int:pk>/corregir/",workforce_views.ponche_form,name="ponche_editar"),path("asistencia/incidencias/nueva/",workforce_views.incidencia_crear,name="incidencia_crear"),path("asistencia/cerrar/",workforce_views.cerrar_asistencia,name="cerrar_asistencia"),
 path("horas-extra/",workforce_views.horas_extra,name="horas_extra"),path("horas-extra/nueva/",workforce_views.hora_extra_crear,name="hora_extra_crear"),path("horas-extra/<int:pk>/estado/",workforce_views.hora_extra_estado,name="hora_extra_estado"),
 path("tss/",workforce_views.tss,name="tss"),path("tss/nueva/",workforce_views.tss_crear,name="tss_crear"),path("tss/exportar.csv",workforce_views.tss_exportar,name="tss_exportar"),path("empleados/<int:pk>/reingresar/",workforce_views.reingresar,name="reingresar"),
 path("reportes/",views.reportes,name="reportes"),path("reportes/empleados.csv",views.reporte_empleados,name="reporte_empleados"),path("documentos-y-cartas/",views.documentos_centro,name="documentos_centro"),path("empleados/",views.empleados,name="empleados"),path("empleados/nuevo/",views.empleado_form,name="empleado_crear"),path("empleados/<int:pk>/",views.empleado_360,name="empleado_360"),path("empleados/<int:pk>/editar/",views.empleado_form,name="empleado_editar"),path("empleados/<int:pk>/documentos/nuevo/",views.documento_cargar,name="documento_cargar"),path("empleados/<int:pk>/cursos/nuevo/",views.curso_asignar,name="curso_asignar"),
 path("<str:recurso>/",views.recurso_lista,name="recurso_lista"),path("<str:recurso>/nuevo/",views.recurso_crear,name="recurso_crear"),path("<str:recurso>/<int:pk>/estado/",views.recurso_estado,name="recurso_estado")]
