from django.core.management.base import BaseCommand,CommandError
from conduces.models import Empresa
from comercial.models import OportunidadComercial
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        try:e=Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
        qs=OportunidadComercial.objects.filter(empresa=e)
        if not o["dry_run"]:
            for x in qs:x.save(update_fields=["monto_ponderado"])
        self.stdout.write(self.style.SUCCESS(f"{qs.count()} oportunidades procesadas."))
