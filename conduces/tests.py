from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
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
            "ds-hero--executive",
            "ds-kpi-ribbon",
            "Centro de atención",
            "Ventas vs. cobros",
            "Compras vs. pagos",
            "Actividad reciente",
            "Acciones rápidas",
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
            "ds-kpi-ribbon",
            "ds-dashboard-grid--executive",
            "ds-attention-grid",
            "ds-quick-grid--executive",
        ):
            self.assertIn(marker, self.responsive)

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
        self.assertContains(response, "Resumen ejecutivo")

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
        for marker in ("Requiere tu atención", "Indicadores ejecutivos", "Actividad reciente", "Agenda operativa"):
            self.assertContains(response, marker)

    def test_kpis_links_and_empty_states_are_honest(self):
        response = self.client.get(reverse("inicio"))
        self.assertEqual(len(response.context["kpis"]), 8)
        self.assertContains(response, "Sin resumen disponible", count=4)
        for route in ("comercial:dashboard", "comercial:o2c_full_dashboard", "inventario:produccion_dashboard", "inventario:dashboard"):
            self.assertContains(response, reverse(route))

    def test_actions_follow_role_permissions(self):
        response = self.client.get(reverse("inicio"))
        self.assertNotContains(response, "Nuevo cliente")
        self.user.user_permissions.add(Permission.objects.get(codename="add_cliente"))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("inicio")), "Nuevo cliente")

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

    def test_responsive_order_and_compact_hero_contract(self):
        self.assertIn("max-height:220px", self.css)
        for marker in (".premium-attention{order:2}", ".premium-kpis{order:3}", ".premium-actions{order:4}", ".premium-charts{order:6}"):
            self.assertIn(marker, self.css)

    def test_secondary_charts_are_lazy_and_no_empty_canvas_is_rendered(self):
        self.assertIn('data-chart-panel="production" hidden', self.template)
        self.assertIn('data-chart-panel="aging" hidden', self.template)
        self.assertIn("if(!canvas||charts[name]||!window.Chart)return", self.javascript)
        self.assertIn("{% if has_financial_chart %}", self.template)
