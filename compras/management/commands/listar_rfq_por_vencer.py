from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from compras.models import ProcesoRFQ
from ._rfq_common import add_scope,scoped
class Command(BaseCommand):
 def add_arguments(self,p):add_scope(p);p.add_argument("--dias",type=int,default=7)
 def handle(self,*a,**o):
  qs=scoped(ProcesoRFQ,o["empresa"]).filter(estado__in=["ABIERTA","EXTENDIDA"],fecha_limite__range=(timezone.now(),timezone.now()+timedelta(days=o["dias"])))
  for r in qs:self.stdout.write(f"{r.empresa_id} {r.numero} {r.fecha_limite.isoformat()}")
  self.stdout.write(f"Total: {qs.count()}")
