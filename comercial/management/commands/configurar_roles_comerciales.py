from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group,Permission
ROLES={"Administrador Comercial":None,"Gerente Comercial":("view_","add_","change_","validar_","exportar_"),"Supervisor Comercial":("view_","add_","change_"),"Vendedor":("view_",),"Facturación":("view_",),"Crédito y Cobros":("view_",),"Despacho":("view_",),"Auditor Comercial":("view_","exportar_"),"Consulta Comercial":("view_",),"Operador INABIE":("view_","gestionar_inabie_")}
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        perms=Permission.objects.filter(content_type__app_label="comercial")
        for nombre,prefixes in ROLES.items():
            selected=perms if prefixes is None else [p for p in perms if p.codename.startswith(prefixes)]
            if not o["dry_run"]:
                g,_=Group.objects.get_or_create(name=nombre);g.permissions.add(*selected)
            self.stdout.write(f"{nombre}: {len(selected)}")
