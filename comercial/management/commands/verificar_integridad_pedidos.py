from django.core.management.base import CommandError
from comercial.models import Pedido
from ._o2c_base import EmpresaCommand
class Command(EmpresaCommand):
    def handle(self,*a,**o):
        e=self.empresa(o);n=Pedido.objects.filter(empresa=e,estado__in=["PENDIENTE_APROBACION","APROBADO","PROGRAMADO"],detalles__isnull=True).distinct().count()
        if n:raise CommandError(f"{n} pedidos operativos sin líneas.")
        self.stdout.write(self.style.SUCCESS("Integridad de pedidos correcta."))
