from django.core.management.base import BaseCommand,CommandError
from conduces.models import Empresa
from comercial.models import FuenteProspecto
FUENTES=(("REFERIDO","Referido"),("WEB","Web"),("REDES","Redes sociales"),("FERIA","Feria"),("VISITA","Visita"),("TELEFONO","Teléfono"),("INABIE","INABIE"),("PUBLICIDAD","Publicidad"),("OTRO","Otro"))
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        try:e=Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
        if not o["dry_run"]:
            for codigo,nombre in FUENTES:FuenteProspecto.objects.get_or_create(empresa=e,codigo=codigo,defaults={"nombre":nombre})
        self.stdout.write(self.style.SUCCESS("Fuentes de prospecto verificadas."))
