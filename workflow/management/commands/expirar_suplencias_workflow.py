from django.core.management.base import BaseCommand
from django.utils import timezone
from workflow.models import SuplenciaAprobador
class Command(BaseCommand):
 help="Simula o inactiva suplencias vencidas."
 def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--confirmar",action="store_true");p.add_argument("--dry-run",action="store_true")
 def handle(self,*a,**o):
  qs=SuplenciaAprobador.objects.filter(empresa_id=o['empresa'],activa=True,vigente_hasta__lt=timezone.now());n=qs.count()
  if o['confirmar']:qs.update(activa=False)
  self.stdout.write(f"{'Expiradas' if o['confirmar'] else 'Por expirar'}: {n}")
