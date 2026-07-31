from django.core.management.base import BaseCommand
from core.application.operation_context import OperationContext
from compras.application.solicitudes.services import recalcular_totales_solicitud
from compras.models import SolicitudCompra
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        qs=SolicitudCompra.objects.filter(empresa_id=o["empresa"],estado__in=["BORRADOR","DEVUELTA"])
        if not o["dry_run"]:
            for s in qs:recalcular_totales_solicitud(context=OperationContext(empresa=s.empresa,origen="COMMAND"),solicitud_id=s.pk)
        self.stdout.write(f"Solicitudes {'a recalcular' if o['dry_run'] else 'recalculadas'}: {qs.count()}")
