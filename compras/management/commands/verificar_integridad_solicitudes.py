from django.core.management.base import BaseCommand
from django.db.models import Sum
from compras.models import SolicitudCompra
class Command(BaseCommand):
    def add_arguments(self,p): p.add_argument("--empresa",type=int)
    def handle(self,*a,**o):
        qs=SolicitudCompra.objects.all();qs=qs.filter(empresa_id=o["empresa"]) if o["empresa"] else qs;bad=0
        for s in qs:
            total=s.lineas.filter(activo=True).aggregate(v=Sum("total"))["v"] or 0
            if total!=s.total_estimado: bad+=1;self.stdout.write(f"{s.numero}: total inconsistente")
        self.stdout.write(f"Solicitudes revisadas: {qs.count()}; inconsistencias: {bad}")
