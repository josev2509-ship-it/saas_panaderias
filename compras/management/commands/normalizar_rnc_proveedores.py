from django.core.management.base import BaseCommand,CommandError
from compras.domain.identity import normalizar_identificacion
from compras.models import Proveedor
class Command(BaseCommand):
 help="Simula o aplica normalización de identificaciones por empresa."
 def add_arguments(self,p):
  p.add_argument("--empresa",type=int,required=True); p.add_argument("--confirmar",action="store_true")
 def handle(self,*a,**o):
  qs=Proveedor.objects.filter(empresa_id=o["empresa"]); cambios=0
  for x in qs:
   nuevo=normalizar_identificacion(x.rnc_identificacion)
   if nuevo!=x.rnc_normalizado:
    cambios+=1
    if o["confirmar"]: x.rnc_normalizado=nuevo; x.save(update_fields=["rnc_normalizado","fecha_actualizacion"])
  self.stdout.write(f"{'Aplicados' if o['confirmar'] else 'Simulados'}: {cambios}")
