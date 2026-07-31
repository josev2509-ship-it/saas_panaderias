from django.core.management.base import BaseCommand
from workflow.models import AsignacionAprobacion
class Command(BaseCommand):
 help="Diagnostica asignaciones por empresa."
 def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True)
 def handle(self,*a,**o):
  qs=AsignacionAprobacion.objects.filter(empresa_id=o['empresa']);self.stdout.write(f"Total={qs.count()} activas={qs.filter(activa=True,revocada=False).count()} revocadas={qs.filter(revocada=True).count()}")
