from django.db.models import Count
from comercial.models import ListaPrecio
from ._o2c_base import EmpresaCommand
class Command(EmpresaCommand):
    def handle(self,*a,**o):
        e=self.empresa(o); n=ListaPrecio.objects.filter(empresa=e,estado="ACTIVA").values("prioridad","moneda_id","cliente_id","segmento_id","canal_id","zona_id").annotate(n=Count("id")).filter(n__gt=1).count()
        self.stdout.write((self.style.WARNING if n else self.style.SUCCESS)(f"Ambigüedades potenciales: {n}."))
