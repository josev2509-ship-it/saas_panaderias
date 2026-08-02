from django.core.management.base import BaseCommand
from conduces.models import Empresa
from comercial.models import ConfiguracionComercialEmpresa
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        qs=Empresa.objects.filter(pk=o["empresa"]) if o["empresa"] else Empresa.objects.all()
        for e in qs:
            if not o["dry_run"]:ConfiguracionComercialEmpresa.objects.get_or_create(empresa=e)
        self.stdout.write(f"Empresas procesadas: {qs.count()}")
