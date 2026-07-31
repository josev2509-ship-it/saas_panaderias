from django.core.management.base import BaseCommand,CommandError
from compras.models import ProcesoRFQ
from ._rfq_common import add_scope,scoped
class Command(BaseCommand):
 def add_arguments(self,p):add_scope(p)
 def handle(self,*a,**o):
  qs=scoped(ProcesoRFQ,o["empresa"]);bad=[r.numero for r in qs if r.fecha_limite<=r.fecha_inicio or r.empresa_id!=r.expediente.empresa_id];self.stdout.write(f"RFQ revisadas: {qs.count()}; inconsistentes: {len(bad)}")
  if bad:raise CommandError(", ".join(bad))
