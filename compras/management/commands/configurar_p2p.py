from django.contrib.auth.models import Group,Permission
from django.core.management.base import BaseCommand

ROLES={"Administrador Compras":None,"Comprador":["view","add","change"],"Supervisor Compras":["view","aprobar","cancelar","exportar"],"Evaluador":["view","evaluar","recalcular","congelar"],"Almacén":["view","cerrar_recepcion"],"Recepción":["view","add","change","cerrar_recepcion"],"Cuentas por Pagar":["view"],"Tesorería":["view"],"Auditor Compras":["view","exportar"],"Consulta Compras":["view"]}
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        perms=Permission.objects.filter(content_type__app_label__in=["compras","contabilidad","tesoreria"])
        for name,prefixes in ROLES.items():
            if o["dry_run"]:continue
            group,_=Group.objects.get_or_create(name=name);selected=perms if prefixes is None else perms.filter(codename__regex=r"^("+"|".join(prefixes)+r")");group.permissions.add(*selected)
        self.stdout.write(f"Roles P2P {'verificados' if o['dry_run'] else 'configurados'} para empresa {o['empresa']}.")
