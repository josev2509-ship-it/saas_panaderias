from django.core.management.base import BaseCommand,CommandError
from workflow.models import ReglaAprobacion
from workflow.application.services import validar_regla_objeto
class Command(BaseCommand):
 help="Valida reglas sin modificar datos."
 def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True)
 def handle(self,*a,**o):
  errors=[f"{r}: {', '.join(validar_regla_objeto(r))}" for r in ReglaAprobacion.objects.filter(empresa_id=o['empresa']) if validar_regla_objeto(r)]
  if errors:raise CommandError("\n".join(errors))
  self.stdout.write(self.style.SUCCESS("Reglas válidas."))
