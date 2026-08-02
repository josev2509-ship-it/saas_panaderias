from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from comercial.application.crm import marcar_actividades_vencidas
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        try:e=Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
        if o["dry_run"]:
            from comercial.models import ActividadComercial
            self.stdout.write(str(ActividadComercial.objects.filter(empresa=e,estado__in=["PENDIENTE","EN_PROGRESO"]).count()));return
        u=get_user_model().objects.filter(is_superuser=True).first()
        if not u:raise CommandError("Se requiere administrador.")
        ids=marcar_actividades_vencidas(context=OperationContext(empresa=e,usuario=u,origen="command"));self.stdout.write(self.style.SUCCESS(f"{len(ids)} actividades vencidas."))
