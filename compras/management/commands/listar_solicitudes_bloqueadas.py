from django.core.management.base import BaseCommand
from compras.models import SolicitudCompra
class Command(BaseCommand):
    def add_arguments(self,p): p.add_argument("--empresa",type=int)
    def handle(self,*a,**o):
        qs=SolicitudCompra.objects.filter(estado="EN_APROBACION",workflow_instancia__isnull=True);qs=qs.filter(empresa_id=o["empresa"]) if o["empresa"] else qs
        for s in qs:self.stdout.write(f"{s.empresa_id} {s.numero}")
        self.stdout.write(f"Bloqueadas: {qs.count()}")
