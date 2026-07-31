from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from documentos.models import Documento
from compras.models import ProcesoRFQ
from ._rfq_common import add_scope,scoped
class Command(BaseCommand):
 def add_arguments(self,p):add_scope(p)
 def handle(self,*a,**o):
  qs=scoped(ProcesoRFQ,o["empresa"]);ct=ContentType.objects.get_for_model(ProcesoRFQ);missing=qs.exclude(pk__in=Documento.objects.filter(content_type=ct,estado="ACTIVO").values("object_id"));self.stdout.write(f"RFQ sin documentos activos: {missing.count()}")
