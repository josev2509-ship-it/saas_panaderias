from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from documentos.models import Documento
from compras.models import SolicitudCompra
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int)
    def handle(self,*a,**o):
        qs=SolicitudCompra.objects.all();qs=qs.filter(empresa_id=o["empresa"]) if o["empresa"] else qs;ct=ContentType.objects.get_for_model(SolicitudCompra);missing=qs.exclude(pk__in=Documento.objects.filter(content_type=ct,estado="ACTIVO").values("object_id"));self.stdout.write(f"Sin documentos activos: {missing.count()}")
