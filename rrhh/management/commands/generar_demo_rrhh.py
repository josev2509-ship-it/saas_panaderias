from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand,CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from conduces.models import Empresa
from nomina.models import ConceptoNomina,CuotaPrestamoEmpleado,LiquidacionLaboral,Nomina,NovedadNomina,PeriodoNomina,PlantillaDocumentoRRHH,PrestamoEmpleado,TipoNomina
from nomina.labor_settlement import calculate_settlement
from nomina.payroll_engine import ensure_legal_parameters
from nomina.services import procesar_nomina
from documentos.models import Documento,TipoDocumento
from documentos.services import crear_documento_asociado
from rrhh.models import (AccionDisciplinaria,Capacitacion,CentroTrabajo,ContratoEmpleado,Departamento,Empleado,HoraExtra,
 IncidenciaAsistencia,LicenciaEmpleado,NovedadTSS,ParticipacionCapacitacion,Puesto,RegistroAsistencia,ReingresoEmpleado,SaldoVacacion,SalidaEmpleado,SolicitudVacacion)

class Command(BaseCommand):
 help="Crea un escenario RRHH sintético e idempotente para una empresa."
 def add_arguments(self,p):p.add_argument("--usuario",required=True,help="Usuario propietario de la empresa")
 def handle(self,*args,**o):
  try:e=Empresa.objects.get(usuario__username=o["usuario"])
  except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada para ese usuario.")
  hoy=timezone.localdate();d,_=Departamento.objects.get_or_create(empresa=e,codigo="DEMO-RRHH",defaults={"nombre":"Operaciones Demo"});p,_=Puesto.objects.get_or_create(empresa=e,codigo="DEMO-ANA",defaults={"nombre":"Analista Demo"});c,_=CentroTrabajo.objects.get_or_create(empresa=e,codigo="DEMO-SDQ",defaults={"nombre":"Centro Demo"})
  emp,_=Empleado.objects.update_or_create(empresa=e,codigo="DEMO-RRHH-001",defaults={"nombres":"Persona","apellidos":"Demostración","identificacion":"DEMO-RRHH-001","puesto":p,"departamento":d,"centro":c,"fecha_ingreso":hoy-timedelta(days=400),"salario":Decimal("45000"),"estado":"ACTIVO"})
  emp_b,_=Empleado.objects.update_or_create(empresa=e,codigo="DEMO-RRHH-003",defaults={"nombres":"Persona","apellidos":"Incentivo Demo","identificacion":"DEMO-RRHH-003","puesto":p,"departamento":d,"centro":c,"fecha_ingreso":hoy-timedelta(days=500),"salario":Decimal("52000"),"estado":"ACTIVO"})
  emp_c,_=Empleado.objects.update_or_create(empresa=e,codigo="DEMO-RRHH-004",defaults={"nombres":"Persona","apellidos":"Préstamo Demo","identificacion":"DEMO-RRHH-004","puesto":p,"departamento":d,"centro":c,"fecha_ingreso":hoy-timedelta(days=700),"salario":Decimal("60000"),"estado":"ACTIVO"})
  inactivo,_=Empleado.objects.update_or_create(empresa=e,codigo="DEMO-RRHH-002",defaults={"nombres":"Persona","apellidos":"Inactiva Demo","identificacion":"DEMO-RRHH-002","puesto":p,"departamento":d,"centro":c,"fecha_ingreso":hoy-timedelta(days=800),"salario":Decimal("38000"),"estado":"INACTIVO"})
  ContratoEmpleado.objects.get_or_create(empresa=e,empleado=emp,inicio=emp.fecha_ingreso,defaults={"tipo":"INDEFINIDO","salario":emp.salario,"puesto":p,"estado":"ACTIVO"});SaldoVacacion.objects.update_or_create(empleado=emp,defaults={"disponibles":Decimal("8"),"tomados":Decimal("4")});SolicitudVacacion.objects.get_or_create(empresa=e,empleado=emp,desde=hoy+timedelta(days=10),defaults={"hasta":hoy+timedelta(days=12),"dias":3,"estado":"APROBADA"})
  curso,_=Capacitacion.objects.get_or_create(empresa=e,nombre="Seguridad laboral Demo",inicio=hoy,defaults={"fin":hoy,"horas":4});ParticipacionCapacitacion.objects.get_or_create(capacitacion=curso,empleado=emp,defaults={"resultado":"Aprobado"})
  LicenciaEmpleado.objects.get_or_create(empresa=e,empleado=emp,tipo="MÉDICA",desde=hoy-timedelta(days=20),defaults={"hasta":hoy-timedelta(days=19),"motivo":"Escenario sintético","estado":"APROBADA"});AccionDisciplinaria.objects.get_or_create(empresa=e,empleado=emp,tipo="VERBAL",fecha=hoy-timedelta(days=30),defaults={"motivo":"Escenario sintético","estado":"CERRADA"})
  ponche=RegistroAsistencia.objects.filter(empresa=e,empleado=emp,fecha=hoy,origen="DEMO").order_by("pk").first() or RegistroAsistencia.objects.create(empresa=e,empleado=emp,fecha=hoy,minutos_tardanza=10,horas_trabajadas=8,origen="DEMO");IncidenciaAsistencia.objects.get_or_create(empresa=e,registro=ponche,tipo="TARDANZA",defaults={"descripcion":"Escenario sintético","minutos":10});extra=HoraExtra.objects.filter(empresa=e,empleado=emp,fecha=hoy).order_by("pk").first() or HoraExtra.objects.create(empresa=e,empleado=emp,fecha=hoy,horas=2,monto=Decimal("500"),estado="APROBADA");NovedadTSS.objects.get_or_create(empresa=e,empleado=emp,periodo=hoy.strftime("%Y-%m"),tipo="ALTA",defaults={"fecha_efectiva":emp.fecha_ingreso,"salario_reportable":emp.salario})
  tipo=TipoNomina.objects.filter(empresa=e,nombre="Mensual Demo").order_by("pk").first() or TipoNomina.objects.create(empresa=e,nombre="Mensual Demo",periodicidad="MENSUAL")
  bloqueados=Nomina.objects.filter(empresa=e,estado__in=("APROBADA","CERRADA","PAGADA")).values_list("periodo_id",flat=True)
  periodo=PeriodoNomina.objects.filter(empresa=e,tipo=tipo,desde=hoy.replace(day=1)).exclude(pk__in=bloqueados).order_by("pk").first() or PeriodoNomina.objects.create(empresa=e,tipo=tipo,desde=hoy.replace(day=1),hasta=hoy,estado="ABIERTO")
  def concepto(codigo,**defaults):
   obj=ConceptoNomina.objects.filter(empresa=e,codigo=codigo).order_by("pk").first()
   if obj:
    for clave,valor in defaults.items():setattr(obj,clave,valor)
    obj.save()
    return obj
   return ConceptoNomina.objects.create(empresa=e,codigo=codigo,**defaults)
  concepto("SALARIO",nombre="Salario",tipo="INGRESO",gravable=True,cotiza_tss=True,cotiza_infotep=True,origen="SALARIO")
  concepto("HORA_EXTRA",nombre="Horas extra",tipo="INGRESO",gravable=True,cotiza_tss=False,origen="ASISTENCIA")
  incentivo=concepto("INCENTIVO_DEMO",nombre="Incentivo demo",tipo="INGRESO",gravable=True,cotiza_tss=False,origen="NOVEDAD")
  descuento=concepto("DESCUENTO_DEMO",nombre="Descuento demo",tipo="DEDUCCION",origen="NOVEDAD")
  for concepto_novedad,monto in ((incentivo,Decimal("1500")),(descuento,Decimal("350"))):
   novedad=NovedadNomina.objects.filter(empresa=e,empleado=emp,periodo=periodo,concepto=concepto_novedad).order_by("pk").first()
   if novedad:NovedadNomina.objects.filter(pk=novedad.pk).update(monto=monto,estado="APROBADA")
   else:NovedadNomina.objects.create(empresa=e,empleado=emp,periodo=periodo,concepto=concepto_novedad,monto=monto,estado="APROBADA")
  ensure_legal_parameters(e,periodo.hasta);procesar_nomina(empresa=e,periodo=periodo)
  loan=PrestamoEmpleado.objects.filter(empresa=e,codigo__startswith="PRE-DEMO-").first()
  if not loan:
   loan=PrestamoEmpleado(empresa=e,codigo="PRE-DEMO-000001",empleado=emp_c,fecha=hoy-timedelta(days=120),principal=Decimal("30000"),saldo=Decimal("21000"),cuotas=10,monto_cuota=Decimal("3000"),estado="ACTIVO",observacion="Escenario sintético: tres cuotas aplicadas")
   loan.save()
  for number in range(1,4):
   hist_start=hoy-timedelta(days=120-number*20);hist_period,_=PeriodoNomina.objects.get_or_create(empresa=e,tipo=tipo,desde=hist_start,defaults={"hasta":hist_start+timedelta(days=14),"estado":"CERRADO"});hist_payroll,_=Nomina.objects.get_or_create(empresa=e,periodo=hist_period,defaults={"numero":f"NOM-DEMO-PRE-{number:02d}","estado":"CERRADA"});CuotaPrestamoEmpleado.objects.update_or_create(prestamo=loan,nomina=hist_payroll,defaults={"numero":number,"monto":Decimal("3000"),"pagada":True,"fecha":hist_period.hasta,"saldo_anterior":Decimal("30000")-Decimal("3000")*(number-1),"saldo_posterior":Decimal("30000")-Decimal("3000")*number,"estado":"APLICADA"})
  salida,_=SalidaEmpleado.objects.get_or_create(empresa=e,empleado=inactivo,defaults={"fecha_salida":hoy-timedelta(days=60),"tipo":"RENUNCIA","motivo":"Escenario sintético","ultima_fecha_laborada":hoy-timedelta(days=60),"responsable":"RRHH Demo","estado":"FINALIZADA"});ReingresoEmpleado.objects.get_or_create(empresa=e,empleado=emp,fecha_reingreso=emp.fecha_ingreso,defaults={"puesto":p,"departamento":d,"centro":c,"salario":emp.salario,"tipo_contrato":"INDEFINIDO","observaciones":"Historial sintético"});liquidacion,_=LiquidacionLaboral.objects.get_or_create(empresa=e,empleado=inactivo,fecha=salida.fecha_salida,defaults={"fecha_salida":salida.fecha_salida,"tipo_terminacion":"RENUNCIA"});calculate_settlement(settlement=liquidacion)
  bodies={"CONTRATO":"Entre {{empresa}} y {{empleado}} se documentan las condiciones laborales registradas para el puesto {{puesto}}, salario {{salario}} y fecha de ingreso {{fecha_ingreso}}. Las cláusulas específicas deben ser configuradas y revisadas por la empresa.","LABORAL":"Por medio de la presente certificamos que {{empleado}}, identificación {{identificacion}}, labora en {{empresa}} como {{puesto}} desde {{fecha_ingreso}}.","CONSULAR":"Se expide la presente constancia laboral de {{empleado}} para los fines consulares que la parte interesada estime pertinentes.","BANCARIA":"Se certifica la relación laboral registrada de {{empleado}} para fines de apertura de cuenta bancaria.","ANEXO":"Descripción / manual de funciones correspondiente al puesto {{puesto}} del departamento {{departamento}}."}
  for plantilla_tipo in ("VOLANTE","NOMINA","PRESTACIONES","LIQUIDACION","CONTRATO","LABORAL","CONSULAR","BANCARIA","ANEXO"):
   PlantillaDocumentoRRHH.objects.get_or_create(empresa=e,tipo=plantilla_tipo,defaults={"encabezado":"Documento empresarial de Gestión Humana","cuerpo":bodies.get(plantilla_tipo,""),"firmante":"Responsable RRHH Demo","cargo_firmante":"Gestión Humana","pie":"Generado por SASTRE ERP Enterprise"})
  doc_tipo,_=TipoDocumento.objects.get_or_create(empresa=e,codigo="DEMO-RRHH",defaults={"nombre":"Documento RRHH Demo"})
  if not Documento.objects.filter(empresa=e,titulo="Documento sintético RRHH",object_id=emp.pk).exists():crear_documento_asociado(empresa=e,objeto=emp,archivo=SimpleUploadedFile("rrhh-demo.pdf",b"%PDF-1.4\n%%EOF",content_type="application/pdf"),usuario=e.usuario,titulo="Documento sintético RRHH",tipo_documento=doc_tipo,fecha_documento=hoy)
  self.stdout.write(self.style.SUCCESS("Demo RRHH creada/actualizada sin datos personales reales."))
