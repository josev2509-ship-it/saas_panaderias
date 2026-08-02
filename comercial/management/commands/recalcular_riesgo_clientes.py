from core.application.operation_context import OperationContext
from comercial.application.o2c import calcular_riesgo_cliente
from comercial.models import Cliente
from ._o2c_base import EmpresaCommand
class Command(EmpresaCommand):
    mutates=True
    def handle(self,*a,**o):
        e=self.empresa(o); qs=Cliente.objects.filter(empresa=e)
        if o["dry_run"]:return self.stdout.write(f"Se recalcularían {qs.count()} clientes.")
        ctx=OperationContext(empresa=e,usuario=e.usuario,origen="comando-riesgo")
        for c in qs:calcular_riesgo_cliente(context=ctx,cliente_id=c.pk)
        self.stdout.write(self.style.SUCCESS(f"Riesgo recalculado: {qs.count()} clientes."))
