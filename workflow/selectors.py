from django.db.models import Q
from .models import InstanciaWorkflow,ReglaAprobacion
from .application.services import obtener_tareas_usuario
def reglas_empresa(*,empresa,q="",estado=""):
 qs=ReglaAprobacion.objects.filter(empresa=empresa)
 if q:qs=qs.filter(Q(codigo__icontains=q)|Q(nombre__icontains=q)|Q(dominio__icontains=q)|Q(tipo_documento__icontains=q))
 if estado:qs=qs.filter(estado=estado)
 return qs
def tareas_usuario(*,empresa,usuario):return obtener_tareas_usuario(empresa=empresa,usuario=usuario)
def instancias_empresa(*,empresa):return InstanciaWorkflow.objects.filter(empresa=empresa).select_related("regla","solicitante")
