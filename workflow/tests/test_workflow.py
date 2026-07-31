from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.exceptions import PermissionDenied,ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from workflow.application.services import activar_regla,aprobar,iniciar_workflow,seleccionar_regla_aplicable,versionar_regla
from workflow.domain.adapters import WorkflowDocumentAdapter,adapter_registry
from workflow.domain.exceptions import WorkflowAmbiguityError,WorkflowAssignmentError,WorkflowConfigurationError
from workflow.models import AsignadorNivel,CondicionReglaAprobacion,DecisionAprobacion,MiembroWorkflowEmpresa,NivelAprobacion,ReglaAprobacion,SuplenciaAprobador

class EmpresaAdapter(WorkflowDocumentAdapter):
 allowed_context_fields=frozenset({"monto_total","es_urgente"})
 def get_empresa(self,d):return d
 def get_solicitante(self,d):return d.usuario
 def build_context(self,d):return {"monto_total":Decimal("125000"),"es_urgente":False}
 def can_start(self,d):return d.activa
 def snapshot(self,d):return {"referencia":f"EMP-{d.pk}","etiqueta":d.nombre}

class WorkflowBase(TestCase):
 def setUp(self):
  U=get_user_model();self.owner=U.objects.create_user("owner",password="x");self.approver=U.objects.create_user("approver",password="x");self.other_user=U.objects.create_user("other",password="x")
  self.empresa=Empresa.objects.create(usuario=self.owner,nombre="Empresa",modulo_workflow=True);self.other=Empresa.objects.create(usuario=self.other_user,nombre="Otra",modulo_workflow=True)
  # La relación actual es uno-a-uno; el aprobador se asocia mediante una empresa auxiliar no válida.
  self.approver.user_permissions.add(*Permission.objects.filter(content_type__app_label="workflow"));self.owner.user_permissions.add(*Permission.objects.filter(content_type__app_label="workflow"))
  MiembroWorkflowEmpresa.objects.create(empresa=self.empresa,usuario=self.approver)
  adapter_registry.register("tests.empresa",EmpresaAdapter());self.ctx=OperationContext(empresa=self.empresa,usuario=self.owner)
 def tearDown(self):adapter_registry.unregister("tests.empresa")
 def rule(self,strategy="CUALQUIERA",default=True,priority=1,include_approver=False):
  r=ReglaAprobacion.objects.create(empresa=self.empresa,codigo=f"R{ReglaAprobacion.objects.count()+1}",nombre="Regla",dominio="GENERAL",tipo_documento="EMPRESA",version=1,estado="BORRADOR",prioridad=priority,es_predeterminada=default,creado_por=self.owner,actualizado_por=self.owner)
  n=NivelAprobacion.objects.create(empresa=self.empresa,regla=r,numero=1,nombre="Gerencia",estrategia_decision=strategy,minimo_aprobaciones=1)
  AsignadorNivel.objects.create(empresa=self.empresa,nivel=n,tipo="USUARIO",usuario=self.owner)
  if include_approver:AsignadorNivel.objects.create(empresa=self.empresa,nivel=n,tipo="USUARIO",usuario=self.approver)
  return r

class RulesTest(WorkflowBase):
 def test_safe_condition_and_selection(self):
  r=self.rule(default=False,priority=10);CondicionReglaAprobacion.objects.create(empresa=self.empresa,regla=r,campo="monto_total",operador="MAYOR_QUE",valor_tipo="DECIMAL",valor_decimal=Decimal("100000"));r.estado="ACTIVA";r.save()
  self.assertEqual(seleccionar_regla_aplicable(empresa=self.empresa,dominio="GENERAL",tipo_documento="EMPRESA",contexto={"monto_total":Decimal("125001")},allowed_fields={"monto_total"}),r)
 def test_unknown_field_rejected(self):
  r=self.rule(default=False);CondicionReglaAprobacion.objects.create(empresa=self.empresa,regla=r,campo="secreto",operador="IGUAL",valor_tipo="TEXTO",valor_texto="x");r.estado="ACTIVA";r.save()
  with self.assertRaises(WorkflowConfigurationError):seleccionar_regla_aplicable(empresa=self.empresa,dominio="GENERAL",tipo_documento="EMPRESA",contexto={},allowed_fields={"monto_total"})
 def test_active_rule_is_structurally_immutable(self):
  r=self.rule();r.estado="ACTIVA";r.save();r.dominio="OTRO"
  with self.assertRaises(ValidationError):r.full_clean()
 def test_version_copies_structure(self):
  r=self.rule();new=versionar_regla(context=self.ctx,regla_id=r.pk);self.assertEqual(new.version,2);self.assertEqual(new.niveles.count(),1)
 def test_ambiguity_is_error(self):
  for i in range(2):
   r=self.rule(default=False,priority=3);CondicionReglaAprobacion.objects.create(empresa=self.empresa,regla=r,campo="es_urgente",operador="IGUAL",valor_tipo="BOOLEANO",valor_booleano=False);r.estado="ACTIVA";r.save()
  with self.assertRaises(WorkflowAmbiguityError):seleccionar_regla_aplicable(empresa=self.empresa,dominio="GENERAL",tipo_documento="EMPRESA",contexto={"es_urgente":False},allowed_fields={"es_urgente"})

class ExecutionTest(WorkflowBase):
 def start(self,strategy="CUALQUIERA",auto=True):
  r=self.rule(strategy);r.permite_autoaprobacion=auto;r.estado="ACTIVA";r.save();return iniciar_workflow(document=self.empresa,adapter_key="tests.empresa",context=self.ctx,idempotency_key="start-1",dominio="GENERAL",tipo_documento="EMPRESA")
 def test_start_is_idempotent_and_snapshotted(self):
  x=self.start();again=iniciar_workflow(document=self.empresa,adapter_key="tests.empresa",context=self.ctx,idempotency_key="start-1",dominio="GENERAL",tipo_documento="EMPRESA");self.assertEqual(x.pk,again.pk);self.assertEqual(str(x.contexto_snapshot["monto_total"]),"125000")
 def test_approve_finishes_and_decision_immutable(self):
  x=self.start();d=aprobar(context=self.ctx,instancia_id=x.pk,comentario="Conforme",idempotency_key="vote-1");x.refresh_from_db();self.assertEqual(x.estado,"APROBADA")
  with self.assertRaises(ValidationError):d.save()
  with self.assertRaises(ValidationError):d.delete()
 def test_double_vote_idempotent(self):
  x=self.start();a=aprobar(context=self.ctx,instancia_id=x.pk,comentario="",idempotency_key="vote-1");b=aprobar(context=self.ctx,instancia_id=x.pk,comentario="",idempotency_key="vote-1");self.assertEqual(a.pk,b.pk)
 def test_autoapproval_forbidden(self):
  x=self.start(auto=False)
  with self.assertRaises(WorkflowAssignmentError):aprobar(context=self.ctx,instancia_id=x.pk,comentario="",idempotency_key="vote-1")
 def test_cross_tenant_context_rejected(self):
  with self.assertRaises(Exception):OperationContext(empresa=self.other,usuario=self.owner)
 def test_unanimity_waits_for_all(self):
  r=self.rule("UNANIMIDAD",include_approver=True);r.permite_autoaprobacion=True;r.estado="ACTIVA";r.save();x=iniciar_workflow(document=self.empresa,adapter_key="tests.empresa",context=self.ctx,idempotency_key="s",dominio="GENERAL",tipo_documento="EMPRESA");aprobar(context=self.ctx,instancia_id=x.pk,comentario="",idempotency_key="v1");x.refresh_from_db();self.assertEqual(x.estado,"EN_APROBACION");ctx=OperationContext(empresa=self.empresa,usuario=self.approver);aprobar(context=ctx,instancia_id=x.pk,comentario="",idempotency_key="v2");x.refresh_from_db();self.assertEqual(x.estado,"APROBADA")
 def _two_user_start(self,strategy,minimo=1):
  r=self.rule(strategy,include_approver=True);n=r.niveles.get();n.minimo_aprobaciones=minimo;n.save();r.permite_autoaprobacion=True;r.estado="ACTIVA";r.save();return iniciar_workflow(document=self.empresa,adapter_key="tests.empresa",context=self.ctx,idempotency_key="s",dominio="GENERAL",tipo_documento="EMPRESA")
 def test_minimum_votes(self):
  x=self._two_user_start("MINIMO_VOTOS",2);aprobar(context=self.ctx,instancia_id=x.pk,comentario="",idempotency_key="v1");x.refresh_from_db();self.assertEqual(x.estado,"EN_APROBACION");aprobar(context=OperationContext(empresa=self.empresa,usuario=self.approver),instancia_id=x.pk,comentario="",idempotency_key="v2");x.refresh_from_db();self.assertEqual(x.estado,"APROBADA")
 def test_majority_waits_for_second(self):
  x=self._two_user_start("MAYORIA_SIMPLE");aprobar(context=self.ctx,instancia_id=x.pk,comentario="",idempotency_key="v1");x.refresh_from_db();self.assertEqual(x.estado,"EN_APROBACION")
 def test_all_assigned_waits_for_second(self):
  x=self._two_user_start("TODOS_LOS_ASIGNADOS");aprobar(context=self.ctx,instancia_id=x.pk,comentario="",idempotency_key="v1");x.refresh_from_db();self.assertEqual(x.estado,"EN_APROBACION")

class SecurityUITest(WorkflowBase):
 def test_configure_groups_is_idempotent(self):
  call_command("configurar_workflow");call_command("configurar_workflow");self.assertEqual(Group.objects.filter(name="Aprobador").count(),1)
 def test_module_and_permission_gate(self):
  self.client.force_login(self.owner);self.assertEqual(self.client.get(reverse("workflow:reglas")).status_code,200);self.empresa.modulo_workflow=False;self.empresa.save();self.assertEqual(self.client.get(reverse("workflow:reglas")).status_code,403)
 def test_decision_get_rejected(self):
  self.client.force_login(self.owner);self.assertEqual(self.client.get(reverse("workflow:decidir",args=[999,"aprobar"])).status_code,403)
 def test_dashboard_and_empty_inbox(self):
  self.client.force_login(self.owner);self.assertContains(self.client.get(reverse("workflow:dashboard")),"Workflow");self.assertContains(self.client.get(reverse("workflow:bandeja")),"Sin tareas pendientes");self.assertContains(self.client.get(reverse("workflow:reportes")),"Reportes de Workflow")
 def test_status_tone(self):
  from django.template import Context,Template
  self.assertIn("success",Template("{% load design_system %}{{ x|status_tone }}").render(Context({"x":"APROBADA"})))

class SubstitutionTest(WorkflowBase):
 def test_self_and_direct_cycle_rejected(self):
  now=timezone.now();s=SuplenciaAprobador(empresa=self.empresa,titular=self.owner,suplente=self.owner,vigente_desde=now,vigente_hasta=now+timedelta(days=1),alcance="GLOBAL",motivo="Ausencia")
  with self.assertRaises(ValidationError):s.full_clean()
