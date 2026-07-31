from django.core.management.base import BaseCommand,CommandError
from compras.models import ExpedienteCompra
from ._rfq_common import add_scope,scoped
class Command(BaseCommand):
 def add_arguments(self,p):add_scope(p)
 def handle(self,*a,**o):
  qs=scoped(ExpedienteCompra,o["empresa"]);bad=[e.numero for e in qs if e.monto_aprobado_solicitudes<0 or not e.solicitudes_vinculadas.filter(activa=True).exists()];self.stdout.write(f"Revisados: {qs.count()}; inconsistentes: {len(bad)}")
  if bad:raise CommandError(", ".join(bad))
