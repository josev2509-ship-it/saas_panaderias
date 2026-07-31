from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


ROLE_PERMISSIONS = {
    "Administrador de empresa": {
        "view_transaction_engine", "view_registroidempotencia",
        "view_eventodominio", "view_conciliacioninventario",
        "retry_registroidempotencia", "retry_eventodominio",
        "run_inventory_diagnosis", "rebuild_inventory_balance",
        "manage_document_sequences",
    },
    "Supervisor tecnico": {
        "view_transaction_engine", "view_registroidempotencia",
        "view_eventodominio", "view_conciliacioninventario",
        "retry_registroidempotencia", "retry_eventodominio",
        "run_inventory_diagnosis", "rebuild_inventory_balance",
        "manage_document_sequences",
    },
    "Operador tecnico": {
        "view_transaction_engine", "view_registroidempotencia",
        "view_eventodominio", "view_conciliacioninventario",
        "run_inventory_diagnosis",
    },
    "Auditor": {
        "view_transaction_engine", "view_registroidempotencia",
        "view_eventodominio", "view_conciliacioninventario",
    },
    "Consulta tecnica": {
        "view_transaction_engine", "view_registroidempotencia",
        "view_eventodominio", "view_conciliacioninventario",
    },
}


class Command(BaseCommand):
    help = "Crea o actualiza idempotentemente los grupos del Centro Tecnico."

    def handle(self, *args, **options):
        for name, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=name)
            permissions = Permission.objects.filter(
                content_type__app_label="core", codename__in=codenames
            )
            group.permissions.set(permissions)
            self.stdout.write(f"{name}: {permissions.count()} permisos")
        self.stdout.write(self.style.SUCCESS("Roles Core configurados."))
