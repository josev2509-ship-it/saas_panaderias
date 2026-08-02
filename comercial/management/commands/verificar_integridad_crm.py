from django.core.management.base import BaseCommand,CommandError
from conduces.models import Empresa
from comercial.models import OportunidadComercial,ActividadComercial
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True)
    def handle(self,*a,**o):
        try:e=Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
        errores=[]
        if OportunidadComercial.objects.filter(empresa=e,prospecto__isnull=True,cliente__isnull=True).exists():errores.append("oportunidades sin relación")
        if ActividadComercial.objects.filter(empresa=e,prospecto__isnull=True,cliente__isnull=True,oportunidad__isnull=True).exists():errores.append("actividades sin relación")
        if errores:raise CommandError(", ".join(errores))
        self.stdout.write(self.style.SUCCESS("Integridad CRM correcta."))
