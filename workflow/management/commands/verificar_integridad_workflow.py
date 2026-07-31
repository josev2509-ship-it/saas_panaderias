from django.core.management.base import BaseCommand,CommandError
from django.db.models import Count
from workflow.models import InstanciaWorkflow,NivelInstanciaWorkflow,RondaWorkflow
class Command(BaseCommand):
 help="Verifica integridad operativa sin modificar."
 def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True)
 def handle(self,*a,**o):
  e=o["empresa"];bad=NivelInstanciaWorkflow.objects.filter(empresa_id=e,estado="ACTIVO").values("instancia").annotate(n=Count("id")).filter(n__gt=1).count()
  if bad:raise CommandError(f"Instancias con múltiples niveles activos: {bad}")
  self.stdout.write(self.style.SUCCESS("Integridad verificada."))
