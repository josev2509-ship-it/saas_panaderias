from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from conduces.models import Empresa


class DemoReadyContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = Path(settings.BASE_DIR)
        cls.template = (root / "conduces/templates/inicio.html").read_text(encoding="utf-8")
        cls.components = "\n".join(
            (root / f"conduces/static/design_system/css/{name}").read_text(encoding="utf-8")
            for name in ("components.css", "demo_ready.css", "layout.css")
        )
        cls.responsive = (
            root / "conduces/static/design_system/css/responsive.css"
        ).read_text(encoding="utf-8")

    def test_dashboard_contains_executive_demo_sections(self):
        for marker in (
            "enterprise-welcome",
            "executive-kpis",
            "Módulos principales",
            "Actividad reciente",
            "Alertas importantes",
        ):
            self.assertIn(marker, self.template)

    def test_minimum_component_subset_exists(self):
        joined = self.template + self.components
        for marker in (
            "ds-page-header",
            "ds-breadcrumb",
            "ds-action-toolbar",
            "ds-tabs",
            "ds-kpi",
            "ds-alert-card",
            "ds-timeline",
            "ds-enterprise-table",
            "ds-pagination",
            "ds-table-toolbar",
            "ds-export-menu",
            "ds-form-section",
            "ds-inline-error",
            "ds-sticky-actions",
            "ds-empty",
            "ds-skeleton",
            "ds-spinner",
            "ds-toast",
            "ds-confirm-dialog",
            "ds-status",
            "ds-hero-header",
            "ds-widget-container",
            "ds-split-layout",
        ):
            self.assertIn(marker, joined)

    def test_responsive_demo_contract(self):
        for marker in (
            "executive-mobile-menu",
            "executive-kpis",
            "executive-modules",
            "executive-bottom",
        ):
            self.assertIn(marker, self.template + self.responsive)

    def test_demo_pipeline_uses_existing_generators(self):
        source = (
            Path(settings.BASE_DIR)
            / "conduces/management/commands/generar_demo_ready.py"
        ).read_text(encoding="utf-8")
        for command in (
            "generar_datos_demo_crm",
            "generar_datos_demo_o2c_completo",
            "generar_datos_demo_p2p",
            "generar_datos_demo_administrativos",
        ):
            self.assertIn(command, source)
        self.assertNotIn("stock_actual =", source)


class DemoReadyDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username="demo-viewer")
        self.empresa = Empresa.objects.create(
            usuario=self.user,
            nombre="Empresa Demo",
            modulo_compras=True,
        )
        self.client.force_login(self.user)

    def test_dashboard_is_authenticated_and_tenant_scoped(self):
        response = self.client.get(reverse("inicio"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Empresa Demo")
        self.assertContains(response, "Resumen general de tu empresa")

    def test_demo_command_dry_run_is_non_mutating(self):
        call_command("generar_demo_ready", empresa=self.empresa.pk, dry_run=True)
        self.assertEqual(Empresa.objects.count(), 1)


class PremiumExecutiveDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="premium-viewer")
        self.empresa = Empresa.objects.create(
            usuario=self.user,
            nombre="Empresa Premium",
            modulo_conduces=True,
            modulo_compras=True,
        )
        self.client.force_login(self.user)

    def test_authenticated_tenant_home_renders_premium_sections(self):
        Empresa.objects.create(nombre="Empresa Ajena")
        response = self.client.get(reverse("inicio"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Empresa Premium")
        self.assertNotContains(response, "Empresa Ajena")
        for marker in ("Ventas del día", "Módulos principales", "Actividad reciente", "Alertas importantes"):
            self.assertContains(response, marker)

    def test_kpis_links_and_empty_states_are_honest(self):
        response = self.client.get(reverse("inicio"))
        self.assertContains(response, 'class="executive-kpi ', count=5)
        self.assertContains(response, "Sin actividad reciente")
        for route in ("core:enterprise_module", "compras:dashboard", "rrhh:dashboard", "core:enterprise_finance"):
            if route == "core:enterprise_module":
                self.assertContains(response, reverse(route, args=["ventas"]))
                continue
            self.assertContains(response, reverse(route))

    def test_actions_follow_role_permissions(self):
        response = self.client.get(reverse("inicio"))
        self.assertContains(response, "Venta General")
        self.assertContains(response, "Compras")
        self.assertNotContains(response, 'data-group="rrhh"')
        self.assertNotContains(response, 'data-group="administracion"')
        self.assertContains(response, "Módulos principales")

    def test_dashboard_stays_within_query_budget(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("inicio"))
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 20, [query["sql"] for query in queries])


class PremiumDashboardContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = Path(settings.BASE_DIR)
        cls.template = (root / "conduces/templates/inicio.html").read_text(encoding="utf-8")
        cls.css = (root / "conduces/static/design_system/css/dashboard_premium.css").read_text(encoding="utf-8")
        cls.javascript = (root / "conduces/static/design_system/js/dashboard_premium.js").read_text(encoding="utf-8")

    def test_reference_layout_and_responsive_contract(self):
        self.assertIn(".executive-kpis{display:grid;grid-template-columns:repeat(5", self.css)
        for marker in (".executive-kpis{grid-template-columns:repeat(2", ".executive-bottom{grid-template-columns:1fr", ".executive-mobile-menu{display:inline-grid"):
            self.assertIn(marker, self.css)

    def test_approved_composition_replaces_legacy_blocks(self):
        for marker in ("enterprise-welcome", "executive-kpis", "executive-modules", "executive-bottom", "executive-mobile-menu"):
            self.assertIn(marker, self.template)
        self.assertNotIn("premium-hero", self.template)
        self.assertNotIn("premium-chart-tabs", self.template)
        self.assertIn("if(canvas&&values.length&&window.Chart)", self.javascript)
