from django.test import TestCase
from django.contrib.auth import get_user_model
from conduces.models import Empresa
from comercial.models import *
from comercial.api.configuracion import validar_empresa_lista_para_vender
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.core.management import call_command
from io import StringIO
from datetime import date
from core.application.operation_context import OperationContext
from comercial.application.configuracion_operativa import configurar_secuencia,versionar_politica,TIPOS_SECUENCIA
class ConfiguracionComercialTest(TestCase):
    def setUp(self):self.u=get_user_model().objects.create_user("cfg");self.e=Empresa.objects.create(usuario=self.u,nombre="E")
    def test_config_unique_and_not_deletable(self):
        c=ConfiguracionComercialEmpresa.objects.create(empresa=self.e);self.assertRaises(Exception,c.delete)
    def test_catalog_tenant_unique(self):CanalVenta.objects.create(empresa=self.e,codigo="WEB",nombre="Web");self.assertRaises(Exception,CanalVenta.objects.create,empresa=self.e,codigo="WEB",nombre="Otro")
    def test_route_rejects_foreign_zone(self):
        u=get_user_model().objects.create_user("x");e=Empresa.objects.create(usuario=u,nombre="X");z=ZonaComercial.objects.create(empresa=e,codigo="Z",nombre="Z");r=RutaComercial(empresa=self.e,codigo="R",nombre="R",zona=z);self.assertRaises(Exception,r.full_clean)
    def test_readiness_reports_blockers(self):self.assertFalse(validar_empresa_lista_para_vender(empresa=self.e).ready)
    def test_dashboard_is_tenant_safe(self):
        CanalVenta.objects.create(empresa=self.e,codigo="A",nombre="Visible")
        ux=get_user_model().objects.create_user("tenant-x");ex=Empresa.objects.create(usuario=ux,nombre="X");CanalVenta.objects.create(empresa=ex,codigo="X",nombre="Secreto")
        self.client.force_login(self.u);response=self.client.get(reverse("comercial:catalogo_lista",args=["canalventa"]));self.assertContains(response,"Visible");self.assertNotContains(response,"Secreto")
    def test_catalog_foreign_detail_is_404(self):
        ux=get_user_model().objects.create_user("tenant-y");ex=Empresa.objects.create(usuario=ux,nombre="Y");obj=CanalVenta.objects.create(empresa=ex,codigo="Y",nombre="Ajeno");self.client.force_login(self.u);self.assertEqual(self.client.get(reverse("comercial:catalogo_detalle",args=["canalventa",obj.pk])).status_code,404)
    def test_state_change_requires_post(self):
        obj=CanalVenta.objects.create(empresa=self.e,codigo="A",nombre="A");self.client.force_login(self.u);self.assertEqual(self.client.get(reverse("comercial:catalogo_estado",args=["canalventa",obj.pk])).status_code,405)
    def test_sequence_service_creates_all_types_idempotently(self):
        self.u.user_permissions.add(Permission.objects.get(codename="change_secuenciadocumento",content_type__app_label="comercial"));context=OperationContext(empresa=self.e,usuario=self.u)
        for tipo in TIPOS_SECUENCIA:configurar_secuencia(context=context,tipo=tipo)
        configurar_secuencia(context=context,tipo="COT");self.assertEqual(SecuenciaDocumento.objects.filter(empresa=self.e).count(),14)
    def test_policy_snapshot_is_immutable(self):
        self.u.user_permissions.add(Permission.objects.get(codename="versionar_politica_comercial"));p=PoliticaCredito.objects.create(empresa=self.e,codigo="C",nombre="Crédito",vigencia_desde=date.today(),creado_por=self.u);nuevo=versionar_politica(context=OperationContext(empresa=self.e,usuario=self.u),tipo="PoliticaCredito",pk=p.pk,datos={},motivo="Prueba");snap=VersionPoliticaComercial.objects.get();self.assertEqual(nuevo.version,2);self.assertEqual(len(snap.hash_contenido),64);self.assertRaises(Exception,snap.save)
    def test_export_requires_permission(self):
        self.client.force_login(self.u);self.assertEqual(self.client.get(reverse("comercial:configuracion_exportar",args=["csv"])).status_code,403)
    def test_role_command_dry_run_does_not_write(self):
        out=StringIO();call_command("configurar_roles_comerciales",dry_run=True,stdout=out);self.assertIn("Administrador Comercial",out.getvalue())
