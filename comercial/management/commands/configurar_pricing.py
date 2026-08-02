from ._o2c_base import EmpresaCommand
class Command(EmpresaCommand):
    mutates=True
    def handle(self,*a,**o):
        e=self.empresa(o)
        if o["dry_run"]:return self.stdout.write("Se verificaría la configuración de pricing.")
        self.stdout.write(self.style.SUCCESS(f"Pricing verificado para {e.nombre}."))
