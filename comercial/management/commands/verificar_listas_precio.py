from django.core.management.base import CommandError
from django.db.models import F
from comercial.models import ListaPrecio
from ._o2c_base import EmpresaCommand
class Command(EmpresaCommand):
    def handle(self,*a,**o):
        e=self.empresa(o); n=ListaPrecio.objects.filter(empresa=e,vigencia_hasta__lt=F("vigencia_desde")).count()
        if n:raise CommandError(f"{n} listas con vigencia inválida.")
        self.stdout.write(self.style.SUCCESS("Listas de precios íntegras."))
