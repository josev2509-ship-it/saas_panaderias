from django.core.management.base import BaseCommand

from conduces.models import Empresa
from core.application.event_bus import event_bus


class Command(BaseCommand):
    help = "Recupera eventos abandonados en estado PROCESANDO."

    def add_arguments(self, parser):
        parser.add_argument("--empresa", type=int)
        parser.add_argument("--limit", type=int)

    def handle(self, *args, **options):
        empresa = None
        if options["empresa"]:
            empresa = Empresa.objects.get(pk=options["empresa"])
        records = event_bus.recover_stuck(empresa=empresa, limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"Eventos recuperados: {len(records)}"))
