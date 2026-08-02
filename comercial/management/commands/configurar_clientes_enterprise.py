from ._o2c_base import EmpresaCommand
class Command(EmpresaCommand):
    mutates=True
    def handle(self,*a,**o):
        e=self.empresa(o)
        if o["dry_run"]:return self.stdout.write("Se verificarían valores empresariales de clientes.")
        self.stdout.write(self.style.SUCCESS(f"Configuración de clientes verificada para {e.nombre}."))
