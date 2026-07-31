from django.core.management.base import BaseCommand
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from compras.application.proveedores import recalcular_estado_documental
from compras.models import Proveedor
class Command(BaseCommand):
 help="Recalcula cumplimiento documental; simulación por defecto."
 def add_arguments(self,p):
  p.add_argument("--empresa",type=int,required=True);p.add_argument("--confirmar",action="store_true")
 def handle(self,*a,**o):
  empresa=Empresa.objects.get(pk=o["empresa"]); qs=Proveedor.objects.filter(empresa=empresa)
  if o["confirmar"]:
   ctx=OperationContext(empresa=empresa,origen="comando")
   for x in qs: recalcular_estado_documental(context=ctx,proveedor_id=x.pk)
  self.stdout.write(f"{'Recalculados' if o['confirmar'] else 'Por recalcular'}: {qs.count()}")
