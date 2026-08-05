from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from conduces.models import Empresa
from core.models import AlertaExperiencia, FavoritoNavegacion, NavegacionReciente


class WorkspaceSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("workspace", password="safe-test-password")
        self.other = User.objects.create_user("other", password="safe-test-password")
        self.empresa = Empresa.objects.create(nombre="Tenant A", usuario=self.user, modulo_compras=True)
        self.otra = Empresa.objects.create(nombre="Tenant B", usuario=self.other, modulo_compras=True)
        self.client.force_login(self.user)

    def test_home_is_role_aware_and_records_recent(self):
        response = self.client.get(reverse("core:workspace_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mi Workspace")
        self.assertTrue(NavegacionReciente.objects.filter(empresa=self.empresa, usuario=self.user).exists())

    def test_workspace_compras_requires_permission(self):
        self.assertRedirects(self.client.get(reverse("core:workspace", args=["compras"])), reverse("core:workspace_home"))
        self.user.user_permissions.add(Permission.objects.get(codename="view_proveedor", content_type__app_label="compras"))
        self.assertEqual(self.client.get(reverse("core:workspace", args=["compras"])).status_code, 200)

    def test_alert_center_is_tenant_safe(self):
        AlertaExperiencia.objects.create(empresa=self.empresa, titulo="Visible", categoria="Comercial")
        AlertaExperiencia.objects.create(empresa=self.otra, titulo="Secreta", categoria="Finanzas")
        response = self.client.get(reverse("core:alertas"))
        self.assertContains(response, "Visible")
        self.assertNotContains(response, "Secreta")

    def test_favorite_is_internal_and_tenant_bound(self):
        self.assertEqual(self.client.post(reverse("core:favorito_toggle"), {"url": "https://evil.test"}).status_code, 400)
        response = self.client.post(reverse("core:favorito_toggle"), {"url": "/comercial/clientes/", "etiqueta": "Clientes"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertJSONEqual(response.content, {"favorite": True})
        self.assertTrue(FavoritoNavegacion.objects.filter(empresa=self.empresa, usuario=self.user).exists())

    def test_unknown_workspace_is_rejected(self):
        self.assertEqual(self.client.get(reverse("core:workspace", args=["unknown"])).status_code, 400)
