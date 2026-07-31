from django.contrib.auth.models import Group,Permission
from django.core.management.base import BaseCommand
M={"Administrador de Workflow":None,"Diseñador de Aprobaciones":{"view_reglaaprobacion","add_reglaaprobacion","change_reglaaprobacion","versionar_regla_aprobacion","activar_regla_aprobacion","retirar_regla_aprobacion","validar_regla_aprobacion","view_condicionreglaaprobacion","add_condicionreglaaprobacion","change_condicionreglaaprobacion","view_nivelaprobacion","add_nivelaprobacion","change_nivelaprobacion","gestionar_asignadores_workflow","gestionar_suplencias_workflow"},"Aprobador":{"view_instanciaworkflow","aprobar_workflow","rechazar_workflow","devolver_workflow","view_historial_workflow","view_tareas_workflow"},"Auditor de Workflow":{"view_reglaaprobacion","view_instanciaworkflow","view_historial_workflow","view_tareas_workflow","exportar_workflow"},"Consulta de Workflow":{"view_instanciaworkflow","view_historial_workflow","view_tareas_workflow"}}
class Command(BaseCommand):
 help="Configura grupos idempotentes del motor Workflow."
 def handle(self,*a,**o):
  perms=Permission.objects.filter(content_type__app_label="workflow")
  for name,codes in M.items():g,_=Group.objects.get_or_create(name=name);selected=perms if codes is None else perms.filter(codename__in=codes);g.permissions.add(*selected);self.stdout.write(f"{name}: {selected.count()}")
