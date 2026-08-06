from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from conduces.models import Empresa


TARGETS = {
    "clientes": 20, "proveedores": 15, "prospectos": 15,
    "oportunidades": 10, "cotizaciones": 20, "pedidos": 25,
    "entregas": 15, "facturas_cliente": 20, "cobros": 15,
    "cuentas_vencidas": 10, "solicitudes": 15, "rfq": 10,
    "ofertas": 15, "ordenes": 10, "recepciones": 12,
    "facturas_proveedor": 15, "pagos": 12,
}

PIPELINE = (
    "generar_datos_demo_configuracion_comercial",
    "generar_datos_demo_o2c_parte_1",
    "generar_datos_demo_crm",
    "generar_datos_demo_o2c_completo",
    "generar_datos_demo_p2p",
    "generar_datos_demo_administrativos",
)


class Command(BaseCommand):
    help = "Orquesta datos sintéticos demo mediante generadores certificados y tenant-safe."

    def add_arguments(self, parser):
        parser.add_argument("--empresa", type=int, required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        try:
            empresa = Empresa.objects.get(pk=options["empresa"])
        except Empresa.DoesNotExist as exc:
            raise CommandError("Empresa no encontrada.") from exc
        if options["dry_run"]:
            self.stdout.write(f"Empresa {empresa.pk}; objetivos: {TARGETS}")
            self.stdout.write("Pipeline certificado: " + ", ".join(PIPELINE))
            return
        for command in PIPELINE:
            call_command(command, empresa=empresa.pk)
        self.stdout.write(self.style.SUCCESS(
            "Pipeline demo ejecutado idempotentemente. Las transacciones O2C/P2P "
            "permanecen gobernadas por sus generadores y servicios certificados."
        ))
