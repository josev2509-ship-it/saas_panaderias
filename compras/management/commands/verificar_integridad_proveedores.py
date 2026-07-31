from django.core.management.base import BaseCommand,CommandError
from django.db.models import Count,Q
from compras.models import ContactoProveedor,DireccionProveedor,ProductoProveedor,Proveedor
class Command(BaseCommand):
 help="Diagnóstico no destructivo de integridad del maestro."
 def add_arguments(self,p): p.add_argument("--empresa",type=int,required=True)
 def handle(self,*a,**o):
  eid=o["empresa"]; errors=[]
  if Proveedor.objects.filter(empresa_id=eid,estado="BLOQUEADO",bloqueado=False).exists(): errors.append("Bloqueos incoherentes")
  if ContactoProveedor.objects.filter(empresa_id=eid,principal=True,activo=True).values("proveedor").annotate(n=Count("id")).filter(n__gt=1).exists(): errors.append("Contactos principales duplicados")
  if errors: raise CommandError("; ".join(errors))
  self.stdout.write(self.style.SUCCESS("Integridad verificada."))
