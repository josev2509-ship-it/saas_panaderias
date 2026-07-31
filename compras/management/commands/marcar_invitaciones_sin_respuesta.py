from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from compras.models import InvitacionProveedorRFQ
class Command(BaseCommand):
 def add_arguments(self,p):p.add_argument("--empresa",type=int);p.add_argument("--dry-run",action="store_true")
 @transaction.atomic
 def handle(self,*a,**o):
  qs=InvitacionProveedorRFQ.objects.filter(estado="INVITADA",fecha_limite_respuesta__lt=timezone.now());qs=qs.filter(empresa_id=o["empresa"]) if o["empresa"] else qs;count=qs.count()
  if not o["dry_run"]:qs.update(estado="SIN_RESPUESTA")
  else:transaction.set_rollback(True)
  self.stdout.write(f"Invitaciones {'detectadas' if o['dry_run'] else 'actualizadas'}: {count}")
