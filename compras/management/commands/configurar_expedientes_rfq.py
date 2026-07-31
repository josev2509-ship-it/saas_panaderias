from django.contrib.auth.models import Group,Permission
from django.core.management.base import BaseCommand
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        view=["view_expedientecompra","view_procesorfq","view_invitacionproveedorrfq","view_historial_expedientecompra"]
        manage=view+["add_expedientecompra","change_expedientecompra","abrir_expedientecompra","cancelar_expedientecompra","declarar_desierto_expedientecompra","recalcular_salud_expedientecompra","exportar_expedientecompra","administrar_expedientecompra","add_procesorfq","change_procesorfq","enviar_revision_rfq","devolver_borrador_rfq","publicar_rfq","abrir_rfq","extender_rfq","cerrar_rfq","cancelar_rfq","versionar_rfq","gestionar_criterios_rfq","gestionar_reglas_rfq","gestionar_proveedores_rfq","exportar_rfq","add_invitacionproveedorrfq","change_invitacionproveedorrfq","gestionar_invitacionrfq","marcar_enviada_invitacionrfq","confirmar_participacion_rfq","registrar_declinacion_rfq","marcar_sin_respuesta_rfq","retirar_proveedor_rfq"]
        mapping={"Administrador de Compras":manage,"Comprador":manage,"Supervisor de Compras":view+["publicar_rfq","abrir_rfq","extender_rfq","cerrar_rfq","cancelar_rfq","exportar_rfq","exportar_expedientecompra"],"Auditor de Compras":view+["exportar_rfq","exportar_expedientecompra"],"Consulta de Compras":view}
        for name,codes in mapping.items():
            g,_=Group.objects.get_or_create(name=name);g.permissions.add(*Permission.objects.filter(content_type__app_label="compras",codename__in=codes))
        self.stdout.write("Expedientes y RFQ configurados.")
