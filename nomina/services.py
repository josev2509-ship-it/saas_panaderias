from decimal import Decimal
from django.db import transaction
from django.db.models import Q,Sum
from .models import Nomina,DetalleNominaEmpleado,LineaDetalleNomina,ConceptoNomina,NovedadNomina
from rrhh.models import Empleado,HoraExtra
@transaction.atomic
def procesar_nomina(*,empresa,periodo,usuario=None):
 n,_=Nomina.objects.get_or_create(empresa=empresa,periodo=periodo,defaults={"numero":f"NOM-{periodo.pk:06d}"});ing=ded=Decimal(0)
 salario=ConceptoNomina.objects.filter(empresa=empresa,codigo="SALARIO").first()
 hora_extra=ConceptoNomina.objects.filter(empresa=empresa,codigo="HORA_EXTRA",activo=True).first()
 for e in Empleado.objects.filter(empresa=empresa,estado="ACTIVO"):
  novedades=NovedadNomina.objects.filter(empresa=empresa,empleado=e,periodo=periodo,estado="APROBADA").select_related("concepto");extras=HoraExtra.objects.filter(empresa=empresa,empleado=e,fecha__range=(periodo.desde,periodo.hasta)).filter(Q(estado="APROBADA")|Q(estado="APLICADA",nomina_id=n.pk));monto_extra=extras.aggregate(v=Sum("monto"))["v"] or Decimal(0);ingresos=e.salario+monto_extra;deducciones=Decimal(0);aportes=Decimal(0)
  for nov in novedades:
   if nov.concepto.tipo=="INGRESO":ingresos+=nov.monto
   elif nov.concepto.tipo=="DEDUCCION":deducciones+=nov.monto
   else:aportes+=nov.monto
  d,_=DetalleNominaEmpleado.objects.update_or_create(nomina=n,empleado=e,defaults={"ingresos":ingresos,"deducciones":deducciones,"aportes":aportes,"neto":ingresos-deducciones});ing+=d.ingresos;ded+=d.deducciones
  d.lineas.all().delete()
  if salario:LineaDetalleNomina.objects.create(detalle=d,concepto=salario,monto=e.salario,snapshot={"version":1,"fuente":"salario_empleado"})
  if hora_extra and monto_extra:LineaDetalleNomina.objects.create(detalle=d,concepto=hora_extra,monto=monto_extra,snapshot={"fuente":"horas_extra_aprobadas"})
  for nov in novedades:LineaDetalleNomina.objects.create(detalle=d,concepto=nov.concepto,monto=nov.monto,snapshot={"novedad_id":nov.pk})
  extras.filter(estado="APROBADA").update(estado="APLICADA",nomina_id=n.pk)
 n.total_ingresos=ing;n.total_deducciones=ded;n.total_neto=ing-ded;n.estado="CALCULADA";n.save();return n
