from django.contrib import admin
from .models import AccionDisciplinaria,Capacitacion,CentroTrabajo,CierreAsistencia,ContratoEmpleado,Departamento,Empleado,EntidadFinancieraRRHH,HoraExtra,IncidenciaAsistencia,LicenciaEmpleado,NovedadTSS,Puesto,RegistroAsistencia,ReingresoEmpleado,SalidaEmpleado,SolicitudDocumentoRRHH,SolicitudVacacion
from .models import DescripcionPuesto, DocumentoEmpleado, SecuenciaEmpleado
@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
 list_display=("codigo","nombres","apellidos","empresa","departamento","puesto","estado");list_filter=("empresa","estado","departamento");search_fields=("codigo","nombres","apellidos","identificacion")
admin.site.register([Departamento,Puesto,CentroTrabajo,EntidadFinancieraRRHH,SolicitudDocumentoRRHH,ContratoEmpleado,SolicitudVacacion,LicenciaEmpleado,AccionDisciplinaria,Capacitacion,SalidaEmpleado,RegistroAsistencia,IncidenciaAsistencia,HoraExtra,CierreAsistencia,NovedadTSS,ReingresoEmpleado,DescripcionPuesto,DocumentoEmpleado,SecuenciaEmpleado])
