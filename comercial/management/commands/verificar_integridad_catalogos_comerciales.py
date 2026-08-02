from django.core.management.base import BaseCommand,CommandError
from conduces.models import Empresa
from comercial.models import CanalVenta,SegmentoCliente,ClasificacionCliente,TipoCliente,TipoEntrega,PrioridadComercial,MotivoComercial
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True)
    def handle(self,*a,**o):
        try:e=Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
        faltan=[m.__name__ for m in (CanalVenta,SegmentoCliente,ClasificacionCliente,TipoCliente,TipoEntrega,PrioridadComercial,MotivoComercial) if not m.objects.filter(empresa=e,activo=True).exists()]
        if faltan:raise CommandError("Faltan catálogos: "+", ".join(faltan))
        self.stdout.write(self.style.SUCCESS("Integridad de catálogos correcta."))
