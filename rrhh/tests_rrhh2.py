from datetime import date,datetime,timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import Client,TestCase
from django.urls import reverse
from django.utils import timezone
from auditoria.models import EventoAuditoria
from conduces.models import Empresa
from nomina.models import ConceptoNomina,PeriodoNomina,TipoNomina
from nomina.services import procesar_nomina
from .models import CentroTrabajo,CierreAsistencia,Departamento,Empleado,HoraExtra,NovedadTSS,Puesto,RegistroAsistencia,ReingresoEmpleado

class WorkforceEnterpriseTests(TestCase):
 @classmethod
 def setUpTestData(cls):
  cls.u=User.objects.create_superuser("rrhh2","rrhh2@example.test","x");cls.e=Empresa.objects.create(usuario=cls.u,nombre="RRHH2");cls.d=Departamento.objects.create(empresa=cls.e,codigo="D",nombre="Demo");cls.p=Puesto.objects.create(empresa=cls.e,codigo="P",nombre="Puesto");cls.c=CentroTrabajo.objects.create(empresa=cls.e,codigo="C",nombre="Centro");cls.emp=Empleado.objects.create(empresa=cls.e,codigo="E1",nombres="Persona",apellidos="Sintética",identificacion="DEMO-1",puesto=cls.p,departamento=cls.d,centro=cls.c,fecha_ingreso=date.today(),salario=Decimal("1000"))
 def setUp(self):self.client.force_login(self.u)
 def test_manual_punch_correction_and_close_are_audited(self):
  entrada=timezone.make_aware(datetime.combine(date.today(),datetime.min.time())+timedelta(hours=8));salida=entrada+timedelta(hours=8)
  r=self.client.post(reverse("rrhh:ponche_crear"),{"empleado":self.emp.pk,"fecha":date.today(),"entrada":entrada.strftime("%Y-%m-%dT%H:%M"),"salida":salida.strftime("%Y-%m-%dT%H:%M"),"origen":"MANUAL","estado":"ABIERTO"});self.assertEqual(r.status_code,302);p=RegistroAsistencia.objects.get();self.assertEqual(p.horas_trabajadas,8)
  self.client.post(reverse("rrhh:ponche_editar",args=[p.pk]),{"empleado":self.emp.pk,"fecha":date.today(),"entrada":entrada.strftime("%Y-%m-%dT%H:%M"),"salida":salida.strftime("%Y-%m-%dT%H:%M"),"origen":"MANUAL","estado":"ABIERTO"});p.refresh_from_db();self.assertTrue(p.corregido)
  self.assertEqual(self.client.get(reverse("rrhh:cerrar_asistencia")).status_code,405);self.assertEqual(self.client.post(reverse("rrhh:cerrar_asistencia"),{"desde":date.today(),"hasta":date.today()}).status_code,302);self.assertTrue(CierreAsistencia.objects.exists());self.assertTrue(EventoAuditoria.objects.filter(empresa=self.e).exists())
 def test_overtime_approval_and_explicit_amount_reach_payroll(self):
  extra=HoraExtra.objects.create(empresa=self.e,empleado=self.emp,fecha=date.today(),horas=2,monto=200)
  self.client.post(reverse("rrhh:hora_extra_estado",args=[extra.pk]),{"estado":"APROBADA"});extra.refresh_from_db();self.assertEqual(extra.estado,"APROBADA")
  tipo=TipoNomina.objects.create(empresa=self.e,nombre="Mensual",periodicidad="MENSUAL");periodo=PeriodoNomina.objects.create(empresa=self.e,tipo=tipo,desde=date.today(),hasta=date.today());ConceptoNomina.objects.create(empresa=self.e,codigo="SALARIO",nombre="Salario",tipo="INGRESO");ConceptoNomina.objects.create(empresa=self.e,codigo="HORA_EXTRA",nombre="Horas extra",tipo="INGRESO")
  n=procesar_nomina(empresa=self.e,periodo=periodo,usuario=self.u);self.assertEqual(n.detalles.get().ingresos,1200);extra.refresh_from_db();self.assertEqual(extra.estado,"APLICADA");self.assertEqual(extra.nomina_id,n.pk)
 def test_tss_export_and_reentry_keep_employee(self):
  NovedadTSS.objects.create(empresa=self.e,empleado=self.emp,periodo="2026-08",tipo="ALTA",fecha_efectiva=date.today(),salario_reportable=1000)
  self.assertEqual(self.client.get(reverse("rrhh:tss_exportar")).status_code,200);old=self.emp.pk;self.emp.estado="INACTIVO";self.emp.save()
  r=self.client.post(reverse("rrhh:reingresar",args=[old]),{"empleado":old,"fecha_reingreso":date.today(),"puesto":self.p.pk,"departamento":self.d.pk,"centro":self.c.pk,"salario":"1100","tipo_contrato":"INDEFINIDO"});self.assertEqual(r.status_code,302);self.emp.refresh_from_db();self.assertEqual(self.emp.pk,old);self.assertEqual(self.emp.estado,"ACTIVO");self.assertTrue(ReingresoEmpleado.objects.exists())
 def test_critical_mutation_rejects_missing_csrf(self):
  x=HoraExtra.objects.create(empresa=self.e,empleado=self.emp,fecha=date.today(),horas=1)
  c=Client(enforce_csrf_checks=True);c.force_login(self.u);self.assertEqual(c.post(reverse("rrhh:hora_extra_estado",args=[x.pk]),{"estado":"APROBADA"}).status_code,403)
