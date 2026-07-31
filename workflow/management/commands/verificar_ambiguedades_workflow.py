from django.core.management.base import BaseCommand,CommandError
from django.db.models import Count
from workflow.models import ReglaAprobacion
class Command(BaseCommand):
 help="Detecta prioridades y predeterminadas ambiguas."
 def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True)
 def handle(self,*a,**o):
  q=ReglaAprobacion.objects.filter(empresa_id=o["empresa"],estado="ACTIVA").values("dominio","tipo_documento","prioridad").annotate(n=Count("id")).filter(n__gt=1)
  if q.exists():raise CommandError(f"Ambigüedades: {q.count()}")
  self.stdout.write(self.style.SUCCESS("Sin ambigüedades evidentes."))
