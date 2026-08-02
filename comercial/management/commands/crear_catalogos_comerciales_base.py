from django.core.management.base import BaseCommand,CommandError
from conduces.models import Empresa
from comercial.models import CanalVenta,SegmentoCliente,ClasificacionCliente,TipoCliente,TipoEntrega,PrioridadComercial,MotivoComercial
DATOS={CanalVenta:("DIRECTO","Venta directa"),SegmentoCliente:("GENERAL","General"),ClasificacionCliente:("ESTANDAR","Estándar"),TipoCliente:("EMPRESA","Empresa"),TipoEntrega:("DOMICILIO","Domicilio"),PrioridadComercial:("NORMAL","Normal"),MotivoComercial:("GENERAL","General")}
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        try:e=Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
        if not o["dry_run"]:
            for model,(codigo,nombre) in DATOS.items():model.objects.get_or_create(empresa=e,codigo=codigo,defaults={"nombre":nombre})
        self.stdout.write(self.style.SUCCESS("Catálogos base verificados."))
