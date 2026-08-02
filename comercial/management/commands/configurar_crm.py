from django.core.management import call_command
from django.core.management.base import BaseCommand
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        args={"empresa":o["empresa"],"dry_run":o["dry_run"]};call_command("crear_fuentes_prospecto_base",**args);call_command("configurar_secuencias_comerciales",**args);call_command("configurar_roles_comerciales",dry_run=o["dry_run"]);self.stdout.write(self.style.SUCCESS("CRM configurado."))
