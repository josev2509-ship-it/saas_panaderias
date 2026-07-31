from django.core.management.base import BaseCommand
from workflow.models import InstanciaWorkflow
class Command(BaseCommand):
 help="Lista workflows activos sin asignaciones operativas."
 def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True)
 def handle(self,*a,**o):
  qs=InstanciaWorkflow.objects.filter(empresa_id=o['empresa'],estado="EN_APROBACION").exclude(asignaciones__activa=True)
  for x in qs:self.stdout.write(f"{x.pk}|{x.referencia_externa}|nivel={x.nivel_actual}")
  self.stdout.write(f"Total: {qs.count()}")
