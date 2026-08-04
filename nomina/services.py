from decimal import Decimal
from django.db import transaction
from .models import Nomina,DetalleNominaEmpleado,LineaDetalleNomina,ConceptoNomina
from rrhh.models import Empleado
@transaction.atomic
def procesar_nomina(*,empresa,periodo,usuario=None):
 n,_=Nomina.objects.get_or_create(empresa=empresa,periodo=periodo,defaults={"numero":f"NOM-{periodo.pk:06d}"});ing=ded=Decimal(0)
 salario=ConceptoNomina.objects.filter(empresa=empresa,codigo="SALARIO").first()
 for e in Empleado.objects.filter(empresa=empresa,estado="ACTIVO"):
  d,_=DetalleNominaEmpleado.objects.get_or_create(nomina=n,empleado=e,defaults={"ingresos":e.salario,"deducciones":0,"aportes":0,"neto":e.salario});ing+=d.ingresos;ded+=d.deducciones
  if salario:LineaDetalleNomina.objects.get_or_create(detalle=d,concepto=salario,defaults={"monto":e.salario,"snapshot":{"version":1}})
 n.total_ingresos=ing;n.total_deducciones=ded;n.total_neto=ing-ded;n.estado="CALCULADA";n.save();return n
