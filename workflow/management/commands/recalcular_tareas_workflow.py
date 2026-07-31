from django.core.management.base import BaseCommand
from workflow.models import AsignacionAprobacion
class Command(BaseCommand):
 help="Diagnostica tareas; no altera asignaciones congeladas."
 def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
 def handle(self,*a,**o):self.stdout.write(f"Tareas activas: {AsignacionAprobacion.objects.filter(empresa_id=o['empresa'],activa=True,revocada=False,nivel_instancia__estado='ACTIVO').count()}. Sin cambios.")
