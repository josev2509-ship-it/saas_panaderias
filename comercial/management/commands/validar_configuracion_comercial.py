from django.core.management.base import BaseCommand
from conduces.models import Empresa
from comercial.api.configuracion import validar_empresa_lista_para_vender
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        r=validar_empresa_lista_para_vender(empresa=Empresa.objects.get(pk=o["empresa"]),persistir=not o["dry_run"]);self.stdout.write(f"ready={r.ready} percentage={r.percentage} blockers={','.join(r.blockers)}")
