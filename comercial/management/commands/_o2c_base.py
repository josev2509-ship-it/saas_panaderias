from django.core.management.base import BaseCommand, CommandError
from conduces.models import Empresa

class EmpresaCommand(BaseCommand):
    mutates=False
    def add_arguments(self, parser):
        parser.add_argument("--empresa", type=int, required=True)
        if self.mutates: parser.add_argument("--dry-run", action="store_true")
    def empresa(self, options):
        try:return Empresa.objects.get(pk=options["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
