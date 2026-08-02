from django.core.management.base import CommandError
from django.db.models import F
from comercial.models import Cliente
from ._o2c_base import EmpresaCommand
class Command(EmpresaCommand):
    def handle(self,*a,**o):
        e=self.empresa(o); n=Cliente.objects.filter(empresa=e,credito_utilizado__gt=F("limite_credito")).count()
        if n:raise CommandError(f"{n} clientes exceden el límite de crédito.")
        self.stdout.write(self.style.SUCCESS("Crédito de clientes íntegro."))
