from datetime import date,timedelta
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client,TestCase
from django.urls import reverse
from auditoria.models import EventoAuditoria
from conduces.models import Empresa
from documentos.models import Documento,TipoDocumento
from .models import Capacitacion,CentroTrabajo,ContratoEmpleado,Departamento,Empleado,HistorialLaboral,ParticipacionCapacitacion,Puesto,SalidaEmpleado,SolicitudVacacion
from .forms import EmpleadoForm

class RRHHCoreTests(TestCase):
 @classmethod
 def setUpTestData(cls):
  cls.user=User.objects.create_superuser("hr-admin","hr@example.test","test-only");cls.other_user=User.objects.create_superuser("hr-other","other@example.test","test-only")
  cls.empresa=Empresa.objects.create(usuario=cls.user,nombre="Empresa RRHH");cls.other=Empresa.objects.create(usuario=cls.other_user,nombre="Otra RRHH")
  cls.dep=Departamento.objects.create(empresa=cls.empresa,codigo="ADM",nombre="Administración");cls.pos=Puesto.objects.create(empresa=cls.empresa,codigo="ANA",nombre="Analista");cls.centro=CentroTrabajo.objects.create(empresa=cls.empresa,codigo="SDQ",nombre="Principal")
  cls.other_dep=Departamento.objects.create(empresa=cls.other,codigo="ADM",nombre="Ajeno");cls.other_pos=Puesto.objects.create(empresa=cls.other,codigo="ANA",nombre="Ajeno");cls.other_centro=CentroTrabajo.objects.create(empresa=cls.other,codigo="SDQ",nombre="Ajeno")
  cls.emp=Empleado.objects.create(empresa=cls.empresa,codigo="E-001",nombres="Ana",apellidos="Pérez",identificacion="001",puesto=cls.pos,departamento=cls.dep,centro=cls.centro,fecha_ingreso=date.today()-timedelta(days=365),salario=50000)
  cls.ajeno=Empleado.objects.create(empresa=cls.other,codigo="E-001",nombres="Otro",apellidos="Tenant",identificacion="002",puesto=cls.other_pos,departamento=cls.other_dep,centro=cls.other_centro,fecha_ingreso=date.today(),salario=1)
 def setUp(self):self.client.force_login(self.user)
 def test_dashboard_list_and_360_are_canonical(self):
  for name,args in (("rrhh:dashboard",()),("rrhh:empleados",()),("rrhh:empleado_360",(self.emp.pk,))):
   response=self.client.get(reverse(name,args=args));self.assertEqual(response.status_code,200);self.assertContains(response,"RRHH")
  response=self.client.get(reverse("rrhh:empleados"));self.assertContains(response,"Ana Pérez");self.assertNotContains(response,"Otro Tenant")
 def test_employee_creation_is_tenant_safe_and_audited(self):
  response=self.client.post(reverse("rrhh:empleado_crear"),{"codigo":"E-002","nombres":"Luis","apellidos":"Díaz","identificacion":"003","puesto":self.pos.pk,"departamento":self.dep.pk,"centro":self.centro.pk,"fecha_ingreso":date.today(),"salario":"45000","forma_pago":"TRANSFERENCIA","frecuencia_pago":"MENSUAL","estado":"ACTIVO"})
  self.assertEqual(response.status_code,302);nuevo=Empleado.objects.get(identificacion="003");self.assertEqual(nuevo.codigo,"EMP-000001");self.assertEqual(nuevo.empresa,self.empresa);self.assertTrue(HistorialLaboral.objects.filter(empleado=nuevo,accion="INGRESO").exists());self.assertTrue(EventoAuditoria.objects.filter(empresa=self.empresa,object_id=nuevo.pk,modulo="rrhh").exists())
 def test_other_tenant_employee_is_404(self):self.assertEqual(self.client.get(reverse("rrhh:empleado_360",args=[self.ajeno.pk])).status_code,404)
 def test_vacation_state_requires_post_and_records_history(self):
  vac=SolicitudVacacion.objects.create(empresa=self.empresa,empleado=self.emp,desde=date.today(),hasta=date.today()+timedelta(days=2),dias=3)
  url=reverse("rrhh:recurso_estado",args=["vacaciones",vac.pk]);self.assertEqual(self.client.get(url).status_code,405);self.assertEqual(self.client.post(url,{"estado":"APROBADA"}).status_code,302);vac.refresh_from_db();self.assertEqual(vac.estado,"APROBADA");self.assertTrue(HistorialLaboral.objects.filter(empleado=self.emp,accion="ESTADO_VACACIONES").exists())
 def test_contract_and_exit_preserve_employee_history(self):
  ContratoEmpleado.objects.create(empresa=self.empresa,empleado=self.emp,tipo="INDEFINIDO",inicio=date.today(),salario=50000,puesto=self.pos,estado="ACTIVO")
  response=self.client.post(reverse("rrhh:recurso_crear",args=["salidas"]),{"empleado":self.emp.pk,"fecha_salida":date.today(),"tipo":"RENUNCIA","motivo":"Prueba","ultima_fecha_laborada":date.today(),"responsable":"RRHH","checklist":"{}","vacaciones_pendientes":"0","estado":"FINALIZADA"})
  self.assertEqual(response.status_code,302,getattr(response.context.get("form") if response.context else None,"errors",None));self.emp.refresh_from_db();self.assertEqual(self.emp.estado,"INACTIVO");self.assertTrue(SalidaEmpleado.objects.filter(empleado=self.emp).exists())
 def test_employee_document_uses_canonical_store(self):
  tipo=TipoDocumento.objects.create(empresa=self.empresa,codigo="CED",nombre="Cédula")
  archivo=SimpleUploadedFile("cedula.pdf",b"%PDF-1.4\n%%EOF",content_type="application/pdf")
  response=self.client.post(reverse("rrhh:documento_cargar",args=[self.emp.pk]),{"tipo_documento":tipo.pk,"titulo":"Cédula","archivo":archivo,"fecha_documento":date.today()})
  self.assertEqual(response.status_code,302);doc=Documento.objects.get(object_id=self.emp.pk);self.assertEqual(doc.empresa,self.empresa);self.assertTrue(EventoAuditoria.objects.filter(empresa=self.empresa,accion="CARGAR_DOCUMENTO").exists())
 def test_sidebar_and_360_have_responsive_enterprise_contracts(self):
  from pathlib import Path
  root=Path(__file__).resolve().parents[1];base=(root/"panaderia_saas/templates/base.html").read_text(encoding="utf-8");detail=(root/"rrhh/templates/rrhh/empleado_360.html").read_text(encoding="utf-8")
  self.assertIn('data-group="rrhh"',base);self.assertIn("ds-tabs",detail);self.assertIn("ds-kpi-grid",detail)
 def test_csv_report_is_tenant_safe(self):
  response=self.client.get(reverse("rrhh:reporte_empleados"));self.assertEqual(response.status_code,200);body=response.content.decode("utf-8-sig");self.assertIn("Ana Pérez",body);self.assertNotIn("Otro Tenant",body)
 def test_course_assignment_updates_employee_360_history(self):
  curso=Capacitacion.objects.create(empresa=self.empresa,nombre="Seguridad",inicio=date.today(),fin=date.today(),horas=4)
  response=self.client.post(reverse("rrhh:curso_asignar",args=[self.emp.pk]),{"capacitacion":curso.pk,"resultado":"Aprobado"});self.assertEqual(response.status_code,302);self.assertTrue(ParticipacionCapacitacion.objects.filter(empleado=self.emp,capacitacion=curso).exists());self.assertTrue(HistorialLaboral.objects.filter(empleado=self.emp,accion="CURSO").exists())
 def test_resource_idor_is_404_for_other_tenant(self):
  vac=SolicitudVacacion.objects.create(empresa=self.empresa,empleado=self.emp,desde=date.today(),hasta=date.today(),dias=1)
  self.client.force_login(self.other_user);response=self.client.post(reverse("rrhh:recurso_estado",args=["vacaciones",vac.pk]),{"estado":"APROBADA"});self.assertEqual(response.status_code,404)
 def test_critical_post_rejects_missing_csrf(self):
  vac=SolicitudVacacion.objects.create(empresa=self.empresa,empleado=self.emp,desde=date.today(),hasta=date.today(),dias=1)
  client=Client(enforce_csrf_checks=True);client.force_login(self.user);response=client.post(reverse("rrhh:recurso_estado",args=["vacaciones",vac.pk]),{"estado":"APROBADA"});self.assertEqual(response.status_code,403)
 def test_employee_sequence_is_progressive_and_tenant_isolated(self):
  a=Empleado.siguiente_codigo(self.empresa);b=Empleado.siguiente_codigo(self.empresa);other=Empleado.siguiente_codigo(self.other)
  self.assertEqual((a,b,other),("EMP-000001","EMP-000002","EMP-000001"))
 def test_duplicate_identification_is_a_form_error(self):
  form=EmpleadoForm({"nombres":"Duplicado","apellidos":"Seguro","identificacion":"001","puesto":self.pos.pk,"departamento":self.dep.pk,"centro":self.centro.pk,"fecha_ingreso":date.today(),"salario":"1000","forma_pago":"TRANSFERENCIA","frecuencia_pago":"MENSUAL","estado":"ACTIVO"},empresa=self.empresa)
  self.assertFalse(form.is_valid());self.assertIn("identificacion",form.errors)
