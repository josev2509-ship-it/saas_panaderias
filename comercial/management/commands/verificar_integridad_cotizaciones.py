from django.core.management.base import CommandError
from comercial.models import CotizacionVenta
from ._o2c_base import EmpresaCommand
class Command(EmpresaCommand):
    def handle(self,*a,**o):
        e=self.empresa(o);n=CotizacionVenta.objects.filter(empresa=e,estado__in=["EN_REVISION","APROBADA_INTERNA","ENVIADA","ACEPTADA","CONVERTIDA"],detalles__isnull=True).distinct().count()
        if n:raise CommandError(f"{n} cotizaciones operativas sin líneas.")
        self.stdout.write(self.style.SUCCESS("Integridad de cotizaciones correcta."))
