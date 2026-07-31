from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from catalogos.models import Moneda, MonedaEmpresa
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from core.domain.document_states import state_contract
from compras.application.proveedores import bloquear_proveedor, crear_proveedor
from compras.domain.identity import normalizar_identificacion
from compras.models import CuentaBancariaProveedor, Proveedor


class ComprasBase(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user("compras",password="x")
        self.empresa=Empresa.objects.create(usuario=self.user,nombre="Empresa",modulo_compras=True)
        self.other_user=get_user_model().objects.create_user("otra",password="x")
        self.other=Empresa.objects.create(usuario=self.other_user,nombre="Otra",modulo_compras=True)
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label="compras"))
        self.ctx=OperationContext(empresa=self.empresa,usuario=self.user)

    def data(self,**extra):
        data={"codigo":"P-1","tipo_persona":"JURIDICA","razon_social":"Proveedor Uno","rnc_identificacion":"1-01 12345-6"}
        data.update(extra); return data


class IdentityAndModelsTest(ComprasBase):
    def test_normalization_variants(self):
        self.assertEqual(normalizar_identificacion(" 1-01 12345-6 "),"101123456")
        self.assertEqual(normalizar_identificacion("ab-12 x"),"AB12X")
        self.assertEqual(normalizar_identificacion(""),"")

    def test_shared_state_contract(self):
        self.assertTrue(state_contract("APROBADO").final)
        self.assertEqual(state_contract("PERSONALIZADO").category,"custom")

    def test_rnc_unique_per_company(self):
        crear_proveedor(context=self.ctx,datos=self.data())
        with self.assertRaises(ValidationError):
            crear_proveedor(context=self.ctx,datos=self.data(codigo="P-2",rnc_identificacion="101123456"))
        other_ctx=OperationContext(empresa=self.other,usuario=self.other_user)
        self.other_user.user_permissions.add(*Permission.objects.filter(content_type__app_label="compras"))
        self.assertTrue(crear_proveedor(context=other_ctx,datos=self.data()).pk)

    def test_cross_company_catalog_rejected(self):
        moneda=Moneda.objects.create(codigo="USD",nombre="Dólar",simbolo="$")
        me=MonedaEmpresa.objects.create(empresa=self.other,moneda=moneda)
        with self.assertRaises(ValidationError):
            crear_proveedor(context=self.ctx,datos=self.data(moneda_habitual=me))

    def test_block_requires_reason_and_service(self):
        p=crear_proveedor(context=self.ctx,datos=self.data())
        with self.assertRaises(ValidationError): bloquear_proveedor(context=self.ctx,proveedor_id=p.pk,motivo="")


class SecurityAndUITest(ComprasBase):
    def setUp(self):
        super().setUp()
        self.proveedor=crear_proveedor(context=self.ctx,datos=self.data())
        moneda=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$")
        self.me=MonedaEmpresa.objects.create(empresa=self.empresa,moneda=moneda)
        self.cuenta=CuentaBancariaProveedor(empresa=self.empresa,proveedor=self.proveedor,banco="Banco",tipo_cuenta="Corriente",moneda=self.me,titular="Proveedor",identificacion_titular="101")
        self.cuenta.set_numero("1234-5678-9012"); self.cuenta.full_clean(); self.cuenta.save()

    def test_mask_and_export_do_not_expose_account(self):
        self.assertEqual(self.cuenta.numero_enmascarado,"•••• 9012")
        self.client.force_login(self.user)
        response=self.client.get(reverse("compras:exportar"))
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response,"1234-5678-9012")

    def test_full_account_permission_and_audit(self):
        self.client.force_login(self.user)
        response=self.client.get(reverse("compras:ver_cuenta",args=[self.cuenta.pk]))
        self.assertJSONEqual(response.content,{"numero_cuenta":"1234-5678-9012"})
        from auditoria.models import EventoAuditoria
        self.assertTrue(EventoAuditoria.objects.filter(object_id=self.cuenta.pk,modulo="compras").exists())

    def test_other_company_returns_404(self):
        self.client.force_login(self.other_user)
        self.other_user.user_permissions.add(Permission.objects.get(codename="view_proveedor",content_type__app_label="compras"))
        self.assertEqual(self.client.get(reverse("compras:detalle",args=[self.proveedor.pk])).status_code,404)

    def test_navigation_and_tabs(self):
        self.client.force_login(self.user)
        response=self.client.get(reverse("compras:detalle",args=[self.proveedor.pk]))
        self.assertContains(response,"Cuentas bancarias")
        self.assertContains(response,"Correspondencia legado")
