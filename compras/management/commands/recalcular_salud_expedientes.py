from django.core.management.base import BaseCommand
from django.db import transaction
from core.application.operation_context import OperationContext
from compras.application.expedientes_rfq import recalcular_salud_expediente
from compras.models import ExpedienteCompra
class Command(BaseCommand):
 def add_arguments(self,p):p.add_argument("--empresa",type=int);p.add_argument("--dry-run",action="store_true")
 @transaction.atomic
 def handle(self,*a,**o):
  qs=ExpedienteCompra.objects.exclude(estado__in=["CANCELADA","CERRADA"]);qs=qs.filter(empresa_id=o["empresa"]) if o["empresa"] else qs
  if not o["dry_run"]:
   for e in qs:recalcular_salud_expediente(context=OperationContext(empresa=e.empresa,origen="COMMAND"),expediente_id=e.pk)
  else:transaction.set_rollback(True)
  self.stdout.write(f"Expedientes: {qs.count()}")
