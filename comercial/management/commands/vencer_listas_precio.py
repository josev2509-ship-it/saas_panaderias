from django.utils import timezone
from comercial.models import ListaPrecio
from ._o2c_base import EmpresaCommand
class Command(EmpresaCommand):
    mutates=True
    def handle(self,*a,**o):
        e=self.empresa(o);q=ListaPrecio.objects.filter(empresa=e,estado="ACTIVA",vigencia_hasta__lt=timezone.localdate());n=q.count()
        if not o["dry_run"]:q.update(estado="VENCIDA")
        self.stdout.write(f"Listas a vencer: {n}." if o["dry_run"] else self.style.SUCCESS(f"Listas vencidas: {n}."))
