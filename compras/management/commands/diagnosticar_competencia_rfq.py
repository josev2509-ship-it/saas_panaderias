from django.core.management.base import BaseCommand
from django.db.models import Count,F
from compras.models import ProcesoRFQ
from ._rfq_common import add_scope,scoped
class Command(BaseCommand):
 def add_arguments(self,p):add_scope(p)
 def handle(self,*a,**o):
  qs=scoped(ProcesoRFQ,o["empresa"]).annotate(invitados=Count("invitaciones")).filter(invitados__lt=F("minimo_proveedores"))
  for r in qs:self.stdout.write(f"{r.numero}: {r.invitados}/{r.minimo_proveedores}")
  self.stdout.write(f"Baja competencia: {qs.count()}")
