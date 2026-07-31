from django.contrib.auth.models import Group,Permission
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from comercial.models import SecuenciaDocumento
from conduces.models import Empresa
ROLES={"Administrador de Compras":["view_solicitudcompra","add_solicitudcompra","change_solicitudcompra","enviar_solicitudcompra","cancelar_solicitudcompra","duplicar_solicitudcompra","corregir_solicitudcompra","view_historial_solicitudcompra","view_todas_solicitudescompra","exportar_solicitudescompra","administrar_solicitudescompra","gestionar_documentos_solicitudcompra","marcar_lista_solicitudcompra","devolver_borrador_solicitudcompra"],"Solicitante de Compras":["view_solicitudcompra","add_solicitudcompra","change_solicitudcompra","enviar_solicitudcompra","cancelar_solicitudcompra","duplicar_solicitudcompra","corregir_solicitudcompra","marcar_lista_solicitudcompra","devolver_borrador_solicitudcompra"],"Comprador":["view_solicitudcompra","view_todas_solicitudescompra","view_historial_solicitudcompra"],"Supervisor de Compras":["view_solicitudcompra","view_todas_solicitudescompra","view_historial_solicitudcompra","exportar_solicitudescompra"],"Auditor de Compras":["view_solicitudcompra","view_todas_solicitudescompra","view_historial_solicitudcompra","exportar_solicitudescompra"],"Consulta de Compras":["view_solicitudcompra"]}
class Command(BaseCommand):
    help="Configura permisos, grupos y secuencia SC de forma idempotente."
    def add_arguments(self,p): p.add_argument("--empresa",type=int);p.add_argument("--dry-run",action="store_true")
    @transaction.atomic
    def handle(self,*args,**opts):
        for name,codes in ROLES.items():
            group,_=Group.objects.get_or_create(name=name);group.permissions.add(*Permission.objects.filter(content_type__app_label__in=["compras","workflow"],codename__in=codes+["iniciar_workflow"]))
        qs=Empresa.objects.filter(pk=opts["empresa"]) if opts["empresa"] else Empresa.objects.all()
        for empresa in qs: SecuenciaDocumento.objects.get_or_create(empresa=empresa,tipo="SC",periodo=timezone.localdate().year,defaults={"prefijo":"SC","longitud":6,"ultimo_numero":0})
        if opts["dry_run"]: transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS("Configuración de solicitudes verificada."))
