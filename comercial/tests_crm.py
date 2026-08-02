from datetime import date,timedelta
from decimal import Decimal
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from comercial.api.crm import obtener_pipeline,obtener_resumen_crm
from comercial.application.crm import *
from comercial.models import *
from documentos.services import resolver_objeto_permitido

class CRMEnterpriseTest(TestCase):
    def setUp(self):
        U=get_user_model();self.u=U.objects.create_superuser("crm-admin","crm@example.com","x");self.e=Empresa.objects.create(usuario=self.u,nombre="CRM A");self.c=OperationContext(empresa=self.e,usuario=self.u);self.otro_u=U.objects.create_superuser("crm-otro","otro@example.com","x");self.otro=Empresa.objects.create(usuario=self.otro_u,nombre="CRM B")
    def prospecto(self,**extra):
        datos={"nombre":"Panadería Norte","nombre_comercial":"Norte","identificacion_fiscal":"1-01-12345-6","correo":"norte@example.com","telefono":"809-555-1000"};datos.update(extra);return crear_prospecto(context=OperationContext(empresa=self.e,usuario=self.u),datos=datos)
    def oportunidad(self,p=None,**extra):
        p=p or self.prospecto();datos={"prospecto":p,"titulo":"Contrato anual","monto_estimado":Decimal("10000"),"probabilidad":Decimal("30"),"fecha_apertura":date.today()};datos.update(extra);return crear_oportunidad(context=OperationContext(empresa=self.e,usuario=self.u),datos=datos)
    def actividad(self,p=None,**extra):
        p=p or self.prospecto();datos={"prospecto":p,"tipo":"LLAMADA","asunto":"Seguimiento","responsable":self.u,"fecha_inicio":timezone.now()+timedelta(hours=1)};datos.update(extra);return crear_actividad(context=OperationContext(empresa=self.e,usuario=self.u),datos=datos)
    def test_prospecto_uses_sequence_and_normalizes(self):
        p=self.prospecto();self.assertTrue(p.numero.startswith("PROS-"));self.assertEqual(p.identificacion_fiscal,"101123456");self.assertTrue(HistorialEstadoProspecto.objects.filter(prospecto=p).exists())
    def test_active_duplicate_is_rejected(self):
        self.prospecto();self.assertRaises(ValidationError,self.prospecto,nombre="Duplicado")
    def test_conversion_is_qualified_and_idempotent(self):
        p=self.prospecto();calificar_prospecto(context=self.c,pk=p.pk);cliente=convertir_prospecto_a_cliente(context=self.c,pk=p.pk);mismo=convertir_prospecto_a_cliente(context=self.c,pk=p.pk);self.assertEqual(cliente.pk,mismo.pk);self.assertEqual(Cliente.objects.filter(empresa=self.e).count(),1)
    def test_conversion_rejects_new(self):self.assertRaises(ValidationError,convertir_prospecto_a_cliente,context=self.c,pk=self.prospecto().pk)
    def test_opportunity_weight_and_transition(self):
        o=self.oportunidad();self.assertEqual(o.monto_ponderado,Decimal("3000"));cambiar_etapa_oportunidad(context=self.c,pk=o.pk,etapa="CALIFICADA");self.assertEqual(HistorialEtapaOportunidad.objects.filter(oportunidad=o).count(),2)
    def test_invalid_transition_and_terminal(self):
        o=self.oportunidad();self.assertRaises(ValidationError,cambiar_etapa_oportunidad,context=self.c,pk=o.pk,etapa="GANADA")
    def test_activity_complete_requires_result(self):
        a=self.actividad();self.assertRaises(ValidationError,completar_actividad,context=self.c,pk=a.pk,resultado="");completar_actividad(context=self.c,pk=a.pk,resultado="Contactado");a.refresh_from_db();self.assertEqual(a.estado,"COMPLETADA")
    def test_activity_cross_tenant_rejected(self):
        p=self.prospecto();a=ActividadComercial(empresa=self.otro,prospecto=p,tipo="LLAMADA",asunto="Ajena",responsable=self.otro_u,fecha_inicio=timezone.now());self.assertRaises(ValidationError,a.full_clean)
    def test_mark_overdue(self):
        a=self.actividad(fecha_inicio=timezone.now()-timedelta(days=1));ids=marcar_actividades_vencidas(context=self.c);a.refresh_from_db();self.assertIn(a.pk,ids);self.assertEqual(a.estado,"VENCIDA")
    def test_api_returns_plain_contracts(self):
        self.oportunidad();self.assertIsInstance(obtener_pipeline(empresa=self.e),tuple);self.assertIsInstance(obtener_resumen_crm(empresa=self.e),dict)
    def test_dashboard_and_empty_states_render(self):
        self.client.force_login(self.u);self.assertEqual(self.client.get(reverse("comercial:crm_dashboard")).status_code,200);self.assertContains(self.client.get(reverse("comercial:prospectos_lista")),"No hay resultados")
    def test_cross_tenant_detail_is_404(self):
        p=crear_prospecto(context=OperationContext(empresa=self.otro,usuario=self.otro_u),datos={"nombre":"Ajeno"});self.client.force_login(self.u);self.assertEqual(self.client.get(reverse("comercial:prospecto_detalle",args=[p.pk])).status_code,404)
    def test_actions_require_post(self):
        p=self.prospecto();self.client.force_login(self.u);self.assertEqual(self.client.get(reverse("comercial:prospecto_accion",args=[p.pk,"calificar"])).status_code,405)
    def test_document_allowlist_is_tenant_safe(self):
        p=self.prospecto();self.assertEqual(resolver_objeto_permitido(empresa=self.e,app_label="comercial",model="prospecto",object_id=p.pk),p);self.assertRaises(ValidationError,resolver_objeto_permitido,empresa=self.otro,app_label="comercial",model="prospecto",object_id=p.pk)
    def test_commands_are_dry_run_and_idempotent(self):
        out=StringIO();call_command("crear_fuentes_prospecto_base",empresa=self.e.pk,dry_run=True,stdout=out);self.assertEqual(FuenteProspecto.objects.count(),0);call_command("crear_fuentes_prospecto_base",empresa=self.e.pk);call_command("crear_fuentes_prospecto_base",empresa=self.e.pk);self.assertEqual(FuenteProspecto.objects.filter(empresa=self.e).count(),9)
    def test_detail_pipeline_agenda_and_reports_render(self):
        p=self.prospecto();o=self.oportunidad(p);a=self.actividad(p);self.client.force_login(self.u)
        for name,args in (("prospecto_detalle",[p.pk]),("oportunidad_detalle",[o.pk]),("actividad_detalle",[a.pk]),("pipeline",[]),("agenda",[]),("crm_reportes",[])):self.assertEqual(self.client.get(reverse(f"comercial:{name}",args=args)).status_code,200)
    def test_exports_csv_xlsx_pdf_print(self):
        self.prospecto(nombre="=RIESGO");self.client.force_login(self.u)
        for fmt,ctype in (("csv","text/csv"),("xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),("pdf","application/pdf"),("print","text/html")):
            response=self.client.get(reverse("comercial:crm_exportar",args=["prospectos",fmt]));self.assertEqual(response.status_code,200);self.assertTrue(response["Content-Type"].startswith(ctype))
    def test_demo_command_dry_run_does_not_write(self):
        out=StringIO();call_command("generar_datos_demo_crm",empresa=self.e.pk,dry_run=True,stdout=out);self.assertIn("30 prospectos",out.getvalue());self.assertEqual(Prospecto.objects.count(),0)
    def test_dashboard_query_budget(self):
        self.client.force_login(self.u)
        with CaptureQueriesContext(connection) as queries:response=self.client.get(reverse("comercial:crm_dashboard"))
        self.assertEqual(response.status_code,200);self.assertLessEqual(len(queries),20)
