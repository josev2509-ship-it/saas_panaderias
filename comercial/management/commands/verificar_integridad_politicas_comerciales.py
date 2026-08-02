from django.core.management.base import BaseCommand,CommandError
from conduces.models import Empresa
from comercial.models import PoliticaCredito,PoliticaDescuento,PoliticaEntrega,PoliticaFacturacion,PoliticaDevolucion,PoliticaComision
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True)
    def handle(self,*a,**o):
        try:e=Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
        ambiguas=[]
        for m in (PoliticaCredito,PoliticaDescuento,PoliticaEntrega,PoliticaFacturacion,PoliticaDevolucion,PoliticaComision):
            vistos=set()
            for p in m.objects.filter(empresa=e,estado="ACTIVA"):
                clave=(p.prioridad,str(p.ambito))
                if clave in vistos:ambiguas.append(m.__name__)
                vistos.add(clave)
        if ambiguas:raise CommandError("Políticas ambiguas: "+", ".join(ambiguas))
        self.stdout.write(self.style.SUCCESS("Integridad de políticas correcta."))
