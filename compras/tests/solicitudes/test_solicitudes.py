from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied,ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from catalogos.models import CentroCosto,Moneda,MonedaEmpresa,TipoCompra,UnidadMedida
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from compras.application.solicitudes.services import agregar_linea_solicitud,calcular_linea_solicitud,crear_solicitud_compra,enviar_solicitud_a_aprobacion,exportar_solicitudes_csv,marcar_solicitud_lista
from compras.models import SolicitudCompra
from compras.selectors import solicitudes_empresa
from workflow.application.services import aprobar
from workflow.models import AsignadorNivel,NivelAprobacion,ReglaAprobacion

class SolicitudBase(TestCase):
    def setUp(self):
        U=get_user_model();self.user=U.objects.create_user("solicitante",password="x");self.other_user=U.objects.create_user("otro",password="x")
        self.empresa=Empresa.objects.create(usuario=self.user,nombre="Empresa",modulo_compras=True,modulo_workflow=True);self.other=Empresa.objects.create(usuario=self.other_user,nombre="Otra",modulo_compras=True)
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label__in=["compras","workflow"]));self.other_user.user_permissions.add(*Permission.objects.filter(content_type__app_label="compras"))
        self.centro=CentroCosto.objects.create(empresa=self.empresa,codigo="CC",nombre="Operaciones");self.tipo=TipoCompra.objects.create(empresa=self.empresa,codigo="SUM",nombre="Suministro",naturaleza="BIEN")
        moneda=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="RD$");self.moneda=MonedaEmpresa.objects.create(empresa=self.empresa,moneda=moneda,activa=True,es_base=True)
        self.unidad=UnidadMedida.objects.create(empresa=self.empresa,codigo="UND",nombre="Unidad",simbolo="u",magnitud="UNIDAD")
        self.ctx=OperationContext(empresa=self.empresa,usuario=self.user,clave_idempotente="create-1")
    def data(self,**extra):
        data={"titulo":"Material operativo","centro_costo":self.centro,"tipo_compra":self.tipo,"naturaleza":"BIEN","fecha_solicitud":timezone.localdate(),"fecha_necesaria":timezone.localdate()+timedelta(days=7),"moneda":self.moneda,"justificacion":"Reposición necesaria","impacto_no_compra":"Detención operativa"};data.update(extra);return data
    def create(self):return crear_solicitud_compra(context=self.ctx,datos=self.data())
    def add_line(self,obj):return agregar_linea_solicitud(context=self.ctx,solicitud_id=obj.pk,datos={"tipo_linea":"LIBRE","descripcion":"Tornillos","cantidad":2,"unidad_medida":self.unidad,"precio_unitario_estimado":100})
    def workflow_rule(self):
        r=ReglaAprobacion.objects.create(empresa=self.empresa,codigo="SC-BASE",nombre="Solicitud de compra",dominio="COMPRAS",tipo_documento="SOLICITUD_COMPRA",version=1,estado="ACTIVA",es_predeterminada=True,permite_autoaprobacion=True,creado_por=self.user,actualizado_por=self.user)
        n=NivelAprobacion.objects.create(empresa=self.empresa,regla=r,numero=1,nombre="Gerencia",estrategia_decision="CUALQUIERA")
        AsignadorNivel.objects.create(empresa=self.empresa,nivel=n,tipo="USUARIO",usuario=self.user);return r

class ModelsAndCalculationsTest(SolicitudBase):
    def test_number_and_company_are_assigned(self):
        obj=self.create();self.assertRegex(obj.numero,r"^SC-\d{4}-\d{6}$");self.assertEqual(obj.empresa,self.empresa);self.assertEqual(obj.estado,"BORRADOR")
    def test_invalid_date_and_cross_tenant_are_rejected(self):
        with self.assertRaises(ValidationError):crear_solicitud_compra(context=self.ctx,datos=self.data(fecha_necesaria=timezone.localdate()-timedelta(days=1)))
        foreign=CentroCosto.objects.create(empresa=self.other,codigo="X",nombre="Ajeno")
        with self.assertRaises(ValidationError):crear_solicitud_compra(context=OperationContext(empresa=self.empresa,usuario=self.user,clave_idempotente="create-2"),datos=self.data(centro_costo=foreign))
    def test_decimal_calculation_and_invalid_discount(self):
        result=calcular_linea_solicitud(cantidad="2",precio_unitario_estimado="100",descuento_porcentaje="10",impuesto_porcentaje="18");self.assertEqual(result["total"],Decimal("212.40"))
        with self.assertRaises(ValidationError):calcular_linea_solicitud(cantidad=1,precio_unitario_estimado=10,descuento_monto=11)
    def test_line_recalculation_and_completion(self):
        obj=self.create();self.add_line(obj);obj.refresh_from_db();self.assertEqual(obj.total_estimado,Decimal("200"));marcar_solicitud_lista(context=self.ctx,solicitud_id=obj.pk);obj.refresh_from_db();self.assertEqual(obj.estado,"LISTA_PARA_ENVIO")
    def test_without_lines_is_blocked(self):
        with self.assertRaises(ValidationError):marcar_solicitud_lista(context=self.ctx,solicitud_id=self.create().pk)
    def test_workflow_start_and_approval_callback_do_not_create_inventory(self):
        obj=self.create();self.add_line(obj);self.workflow_rule();marcar_solicitud_lista(context=self.ctx,solicitud_id=obj.pk);enviar_solicitud_a_aprobacion(context=self.ctx,solicitud_id=obj.pk,idempotency_key="send-1");obj.refresh_from_db();self.assertEqual(obj.estado,"EN_APROBACION");self.assertIsNotNone(obj.workflow_instancia_id)
        aprobar(context=self.ctx,instancia_id=obj.workflow_instancia_id,comentario="Conforme",idempotency_key="approve-1");obj.refresh_from_db();self.assertEqual(obj.estado,"APROBADA")
    def test_creation_idempotency_reuses_document(self):
        first=self.create();again=crear_solicitud_compra(context=self.ctx,datos=self.data());self.assertEqual(first.pk,again.pk)

class SecurityAndUITest(SolicitudBase):
    def test_selector_and_detail_are_tenant_safe(self):
        obj=self.create();self.assertEqual(solicitudes_empresa(empresa=self.other,usuario=self.other_user).count(),0);self.client.force_login(self.other_user);self.assertEqual(self.client.get(reverse("compras:solicitud_detalle",args=[obj.pk])).status_code,404)
    def test_actions_reject_get(self):
        obj=self.create();self.client.force_login(self.user);self.assertEqual(self.client.get(reverse("compras:solicitud_accion",args=[obj.pk,"cancelar"])).status_code,403)
    def test_list_and_detail_use_enterprise_ui(self):
        obj=self.create();self.client.force_login(self.user);self.assertContains(self.client.get(reverse("compras:solicitudes_lista")),"Solicitudes de compra");self.assertContains(self.client.get(reverse("compras:solicitud_detalle",args=[obj.pk])),obj.numero)
    def test_csv_injection_is_neutralized(self):
        obj=self.create();obj.titulo="=HYPERLINK(\"bad\")";obj.save(update_fields=["titulo"]);csv=exportar_solicitudes_csv(context=self.ctx,queryset=SolicitudCompra.objects.all());self.assertIn("'=HYPERLINK",csv)
