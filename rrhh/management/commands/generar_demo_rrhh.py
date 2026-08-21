from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand,CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from conduces.models import Empresa
from nomina.models import ConceptoNomina,LiquidacionLaboral,PeriodoNomina,TipoNomina
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
  inactivo,_=Empleado.objects.update_or_create(empresa=e,codigo="DEMO-RRHH-002",defaults={"nombres":"Persona","apellidos":"Inactiva Demo","identificacion":"DEMO-RRHH-002","puesto":p,"departamento":d,"centro":c,"fecha_ingreso":hoy-timedelta(days=800),"salario":Decimal("38000"),"estado":"INACTIVO"})
  ContratoEmpleado.objects.get_or_create(empresa=e,empleado=emp,inicio=emp.fecha_ingreso,defaults={"tipo":"INDEFINIDO","salario":emp.salario,"puesto":p,"estado":"ACTIVO"});SaldoVacacion.objects.update_or_create(empleado=emp,defaults={"disponibles":Decimal("8"),"tomados":Decimal("4")});SolicitudVacacion.objects.get_or_create(empresa=e,empleado=emp,desde=hoy+timedelta(days=10),defaults={"hasta":hoy+timedelta(days=12),"dias":3,"estado":"APROBADA"})
  curso,_=Capacitacion.objects.get_or_create(empresa=e,nombre="Seguridad laboral Demo",inicio=hoy,defaults={"fin":hoy,"horas":4});ParticipacionCapacitacion.objects.get_or_create(capacitacion=curso,empleado=emp,defaults={"resultado":"Aprobado"})
  LicenciaEmpleado.objects.get_or_create(empresa=e,empleado=emp,tipo="MÉDICA",desde=hoy-timedelta(days=20),defaults={"hasta":hoy-timedelta(days=19),"motivo":"Escenario sintético","estado":"APROBADA"});AccionDisciplinaria.objects.get_or_create(empresa=e,empleado=emp,tipo="VERBAL",fecha=hoy-timedelta(days=30),defaults={"motivo":"Escenario sintético","estado":"CERRADA"})
  ponche,_=RegistroAsistencia.objects.get_or_create(empresa=e,empleado=emp,fecha=hoy,defaults={"minutos_tardanza":10,"horas_trabajadas":8,"origen":"DEMO"});IncidenciaAsistencia.objects.get_or_create(empresa=e,registro=ponche,tipo="TARDANZA",defaults={"descripcion":"Escenario sintético","minutos":10});HoraExtra.objects.get_or_create(empresa=e,empleado=emp,fecha=hoy,defaults={"horas":2,"monto":Decimal("500"),"estado":"APROBADA"});NovedadTSS.objects.get_or_create(empresa=e,empleado=emp,periodo=hoy.strftime("%Y-%m"),tipo="ALTA",defaults={"fecha_efectiva":emp.fecha_ingreso,"salario_reportable":emp.salario})
  tipo,_=TipoNomina.objects.get_or_create(empresa=e,nombre="Mensual Demo",defaults={"periodicidad":"MENSUAL"});periodo,_=PeriodoNomina.objects.get_or_create(empresa=e,tipo=tipo,desde=hoy.replace(day=1),defaults={"hasta":hoy,"estado":"ABIERTO"});ConceptoNomina.objects.get_or_create(empresa=e,codigo="SALARIO",defaults={"nombre":"Salario","tipo":"INGRESO"});ConceptoNomina.objects.get_or_create(empresa=e,codigo="HORA_EXTRA",defaults={"nombre":"Horas extra","tipo":"INGRESO"});procesar_nomina(empresa=e,periodo=periodo);LiquidacionLaboral.objects.get_or_create(empresa=e,empleado=emp,fecha=hoy,defaults={"total":0,"estado":"BORRADOR"})
  SalidaEmpleado.objects.get_or_create(empresa=e,empleado=inactivo,defaults={"fecha_salida":hoy-timedelta(days=60),"tipo":"RENUNCIA","motivo":"Escenario sintético","ultima_fecha_laborada":hoy-timedelta(days=60),"responsable":"RRHH Demo","estado":"FINALIZADA"});ReingresoEmpleado.objects.get_or_create(empresa=e,empleado=emp,fecha_reingreso=emp.fecha_ingreso,defaults={"puesto":p,"departamento":d,"centro":c,"salario":emp.salario,"tipo_contrato":"INDEFINIDO","observaciones":"Historial sintético"})
  doc_tipo,_=TipoDocumento.objects.get_or_create(empresa=e,codigo="DEMO-RRHH",defaults={"nombre":"Documento RRHH Demo"})
  if not Documento.objects.filter(empresa=e,titulo="Documento sintético RRHH",object_id=emp.pk).exists():crear_documento_asociado(empresa=e,objeto=emp,archivo=SimpleUploadedFile("rrhh-demo.pdf",b"%PDF-1.4\n%%EOF",content_type="application/pdf"),usuario=e.usuario,titulo="Documento sintético RRHH",tipo_documento=doc_tipo,fecha_documento=hoy)
  self.stdout.write(self.style.SUCCESS("Demo RRHH creada/actualizada sin datos personales reales."))
