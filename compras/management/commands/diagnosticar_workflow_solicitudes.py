from django.core.management.base import BaseCommand
from workflow.domain.adapters import adapter_registry
from workflow.models import ReglaAprobacion
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int)
    def handle(self,*a,**o):
        adapter_registry.get("compras.solicitud_compra");qs=ReglaAprobacion.objects.filter(dominio="COMPRAS",tipo_documento="SOLICITUD_COMPRA",estado="ACTIVA");qs=qs.filter(empresa_id=o["empresa"]) if o["empresa"] else qs;self.stdout.write(f"Adaptador registrado; reglas activas: {qs.count()}")
