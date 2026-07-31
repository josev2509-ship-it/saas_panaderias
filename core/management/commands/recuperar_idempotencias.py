from django.core.management.base import BaseCommand

from conduces.models import Empresa
from core.application.idempotency import recover_stale


class Command(BaseCommand):
    help = "Marca como fallidas las operaciones INICIADA abandonadas."

    def add_arguments(self, parser):
        parser.add_argument("--empresa", type=int)
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        empresa = None
        if options["empresa"]:
            empresa = Empresa.objects.get(pk=options["empresa"])
        records = recover_stale(empresa=empresa, limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"Operaciones recuperadas: {len(records)}"))
