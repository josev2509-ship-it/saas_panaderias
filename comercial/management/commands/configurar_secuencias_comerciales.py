from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from comercial.application.configuracion_operativa import TIPOS_SECUENCIA,configurar_secuencia
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        try:e=Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
        if o["dry_run"]:self.stdout.write(f"Se configurarían {len(TIPOS_SECUENCIA)} secuencias.");return
        u=get_user_model().objects.filter(is_superuser=True).first()
        if not u:raise CommandError("Se requiere un usuario administrador.")
        c=OperationContext(empresa=e,usuario=u,origen="command")
        for tipo in TIPOS_SECUENCIA:configurar_secuencia(context=c,tipo=tipo)
        self.stdout.write(self.style.SUCCESS("14 secuencias configuradas."))
