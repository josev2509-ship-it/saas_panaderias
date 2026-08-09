from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.test import TestCase
from django.urls import resolve, reverse

from conduces.models import Empresa, PerfilUsuario


class CanonicalPremiumDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "test-only-canonical"
        cls.user = get_user_model().objects.create_user(
            username="canonical-user",
            email="canonical@example.test",
            password=cls.password,
        )
        cls.empresa = Empresa.objects.create(
            usuario=cls.user,
            nombre="Empresa Canonical",
            modulo_conduces=True,
            modulo_inventario=True,
            modulo_compras=True,
            modulo_workflow=True,
        )
        PerfilUsuario.objects.create(
            user=cls.user,
            rol="admin_empresa",
            correo_validado=True,
            activo=True,
        )

    def test_root_is_the_only_canonical_premium_route(self):
        self.client.force_login(self.user)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.resolver_match.url_name, "inicio")
        self.assertTemplateUsed(response, "inicio.html")
        self.assertContains(response, 'data-dashboard-version="premium-v2"')
        self.assertContains(response, "data-premium-dashboard")
        self.assertNotContains(response, "dashboard-legacy")
        self.assertEqual(reverse("inicio"), "/")
        self.assertEqual(resolve("/").url_name, "inicio")

    def test_login_chain_redirects_to_canonical_premium_dashboard(self):
        response = self.client.post(
            reverse("login_usuario"),
            {"username": self.user.username, "password": self.password},
        )
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        dashboard = self.client.get(response["Location"])
        self.assertContains(dashboard, 'data-dashboard-version="premium-v2"')

    def test_logo_sidebar_and_workspace_converge_on_root(self):
        self.client.force_login(self.user)
        for route in ("inicio", "core:workspace_home"):
            response = self.client.get(reverse(route))
            self.assertContains(response, 'class="ds-brand-home" href="/"')
            self.assertContains(response, 'href="/" aria-current="page"' if route == "inicio" else 'href="/"')

    def test_dashboard_assets_are_single_and_canonical(self):
        self.client.force_login(self.user)
        html = self.client.get("/").content.decode("utf-8")
        for asset in (
            "design_system/css/dashboard_premium.css",
            "design_system/js/dashboard_premium.js",
            "design_system/css/demo_unified.css",
        ):
            self.assertEqual(html.count(static(asset)), 1)
        self.assertNotIn("?v=qa1", html)
