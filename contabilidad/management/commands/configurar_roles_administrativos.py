from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction


ROLES = {
    "Administrador Contable": ({"contabilidad", "tesoreria", "presupuesto"}, None),
    "Contador": ({"contabilidad"}, ("view_", "add_", "change_", "contabilizar_", "cerrar_")),
    "Auxiliar Contable": ({"contabilidad"}, ("view_", "add_", "change_")),
    "Auditor Financiero": ({"contabilidad", "tesoreria", "presupuesto"}, ("view_",)),
    "Tesorería": ({"tesoreria"}, ("view_", "add_", "change_")),
    "Cuentas por Pagar": ({"contabilidad"}, ("view_factura", "add_factura", "change_factura", "view_cuentaporpagar", "add_solicitud", "change_solicitud", "view_ordenpago")),
    "Presupuesto": ({"presupuesto"}, ("view_", "add_", "change_")),
    "Consulta Financiera": ({"contabilidad", "tesoreria", "presupuesto"}, ("view_",)),
    "Administrador RRHH": ({"rrhh", "nomina"}, None),
    "Analista RRHH": ({"rrhh"}, ("view_", "add_", "change_")),
    "Nómina": ({"nomina"}, ("view_", "add_", "change_")),
    "Supervisor": ({"rrhh"}, ("view_", "change_solicitud", "change_horaextra")),
    "Empleado Consulta": ({"rrhh", "nomina"}, ("view_",)),
    "Auditor RRHH": ({"rrhh", "nomina"}, ("view_",)),
    "Administrador Activos": ({"activos", "mantenimiento"}, None),
    "Mantenimiento": ({"mantenimiento"}, ("view_", "add_", "change_")),
    "Técnico Mantenimiento": ({"mantenimiento"}, ("view_", "change_ordenmantenimiento")),
    "Consulta Activos": ({"activos", "mantenimiento"}, ("view_",)),
}


class Command(BaseCommand):
    help = "Crea o actualiza los roles administrativos sin retirar permisos externos."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        for nombre, (apps, prefijos) in ROLES.items():
            disponibles = Permission.objects.filter(content_type__app_label__in=apps)
            seleccionados = list(disponibles) if prefijos is None else [p for p in disponibles if p.codename.startswith(prefijos)]
            if not options["dry_run"]:
                grupo, _ = Group.objects.get_or_create(name=nombre)
                # add() conserva permisos externos asignados deliberadamente.
                grupo.permissions.add(*seleccionados)
            self.stdout.write(f"{nombre}: {len(seleccionados)} permisos administrados")
