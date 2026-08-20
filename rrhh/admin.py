from django.contrib import admin
from .models import AccionDisciplinaria,Capacitacion,CentroTrabajo,ContratoEmpleado,Departamento,Empleado,LicenciaEmpleado,Puesto,SalidaEmpleado,SolicitudVacacion
@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
 list_display=("codigo","nombres","apellidos","empresa","departamento","puesto","estado");list_filter=("empresa","estado","departamento");search_fields=("codigo","nombres","apellidos","identificacion")
admin.site.register([Departamento,Puesto,CentroTrabajo,ContratoEmpleado,SolicitudVacacion,LicenciaEmpleado,AccionDisciplinaria,Capacitacion,SalidaEmpleado])
