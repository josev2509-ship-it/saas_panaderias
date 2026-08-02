from django.contrib.auth.models import Group,Permission
from django.core.management.base import BaseCommand
ROLES={"Administrador Comercial":None,"Gerente Comercial":("view_","add_","change_","validar_","exportar_","calificar_","descartar_","convertir_","reasignar_","cambiar_","ganar_","perder_","cancelar_","completar_","reprogramar_"),"Supervisor Comercial":("view_","add_","change_","calificar_","descartar_","reasignar_","cambiar_","completar_","reprogramar_"),"Vendedor":("view_","add_prospecto","change_prospecto","add_oportunidad","change_oportunidad","add_actividad","change_actividad","completar_actividad","reprogramar_actividad"),"Facturación":("view_",),"Crédito y Cobros":("view_",),"Despacho":("view_",),"Auditor Comercial":("view_","exportar_"),"Consulta Comercial":("view_",),"Operador INABIE":("view_","gestionar_inabie_")}
ROLES.update({
    "Almacén":("view_","gestionar_reserva_"),
    "Preparación":("view_","gestionar_preparacion_","gestionar_picking_","gestionar_packing_"),
    "Chofer":("view_conducecomercial","view_entregacomercial","gestionar_entrega_"),
    "Cobranzas":("view_","gestionar_cxc","registrar_cobro","revertir_cobro"),
})
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        perms=Permission.objects.filter(content_type__app_label="comercial")
        for nombre,prefixes in ROLES.items():
            selected=perms if prefixes is None else [p for p in perms if p.codename.startswith(prefixes)]
            if not o["dry_run"]:
                group,_=Group.objects.get_or_create(name=nombre);group.permissions.add(*selected)
            self.stdout.write(f"{nombre}: {len(selected)}")
