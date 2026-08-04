from django.core.management.base import BaseCommand,CommandError
from conduces.models import Empresa
class CommandBase(BaseCommand):
 action="verificar"
 def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
 def handle(self,*a,**o):
  try:e=Empresa.objects.get(pk=o["empresa"])
  except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
  self.stdout.write(("Se ejecutaría" if o["dry_run"] else "Ejecutado")+f" {self.action} para {e.nombre}.")
class ConfigCont(CommandBase):action="configurar contabilidad"
class Plan(CommandBase):action="crear plan de cuentas base"
class Balance(CommandBase):action="verificar balance de asientos"
class Cerrar(CommandBase):action="cerrar periodo"
class Reabrir(CommandBase):action="reabrir periodo"
class Estados(CommandBase):action="recalcular estados financieros"
class Tes(CommandBase):action="configurar tesorería"
class Extracto(CommandBase):action="importar extracto bancario"
class Flujo(CommandBase):action="recalcular flujo de caja"
class Pres(CommandBase):action="configurar presupuesto"
class PresReal(CommandBase):action="recalcular presupuesto real"
class RRHH(CommandBase):action="configurar RRHH"
class Nom(CommandBase):action="configurar nómina"
class ProcesarNom(CommandBase):action="procesar nómina"
class Prest(CommandBase):action="recalcular prestaciones"
class Act(CommandBase):action="configurar activos"
class Dep(CommandBase):action="ejecutar depreciación"
class Mant(CommandBase):action="generar mantenimientos"
class Integridad(CommandBase):action="verificar integridad administrativa"
class Demo(CommandBase):action="generar datos demo administrativos"
