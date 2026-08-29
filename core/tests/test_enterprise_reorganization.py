from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from conduces.models import Empresa


class EnterpriseReorganizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("enterprise-admin", "enterprise@example.com", "secret")
        cls.empresa = Empresa.objects.create(usuario=cls.user, nombre="Enterprise Demo", modulo_compras=True, modulo_inventario=True, modulo_nomina=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_sidebar_contains_only_canonical_top_level_domains(self):
        response = self.client.get(reverse("inicio"))
        self.assertEqual(response.status_code, 200)
        for label in ("Panel principal", "Venta General", "INABIE", "Inventario y Producción", "Compras", "Gestión Humana", "Finanzas", "Contabilidad", "Administración"):
            self.assertContains(response, label)
        self.assertNotContains(response, "<summary>Comercial</summary>", html=True)
        self.assertNotContains(response, "<summary>Producción</summary>", html=True)
        self.assertContains(response, "Ventas del día")
        self.assertContains(response, "Módulos principales")
        self.assertContains(response, "Alertas importantes")

    def test_module_hubs_and_financial_screens_render(self):
        routes = [
            reverse("core:enterprise_module", args=["ventas"]), reverse("core:enterprise_module", args=["inabie"]),
            reverse("core:enterprise_module", args=["inventario"]), reverse("core:enterprise_module", args=["administracion"]),
            reverse("core:enterprise_finance"), reverse("core:enterprise_cxp"), reverse("core:enterprise_cxc"),
            reverse("core:enterprise_treasury"), reverse("core:enterprise_payment_schedule"),
            reverse("core:enterprise_payment_multiple"),
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Inicio")

    def test_unknown_module_returns_404(self):
        self.assertEqual(self.client.get(reverse("core:enterprise_module", args=["desconocido"])).status_code, 404)

    def test_financial_views_require_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("core:enterprise_cxp"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)
