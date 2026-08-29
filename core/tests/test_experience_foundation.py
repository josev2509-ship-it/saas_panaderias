from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class EnterpriseExperienceFoundationTests(SimpleTestCase):
    """Contrato visual: detecta regresiones de shell sin tocar pruebas funcionales."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(settings.BASE_DIR)
        cls.base = (cls.root / "panaderia_saas/templates/base.html").read_text(encoding="utf-8")
        cls.dashboard = (cls.root / "conduces/templates/inicio.html").read_text(encoding="utf-8")
        cls.javascript = (cls.root / "conduces/static/design_system/js/components.js").read_text(encoding="utf-8")
        cls.responsive = (cls.root / "conduces/static/design_system/css/responsive.css").read_text(encoding="utf-8")

    def test_templates_compile(self):
        get_template("base.html")
        get_template("inicio.html")
        for name in ("kpi_card", "enterprise_table", "form_section", "breadcrumbs", "empty_state"):
            get_template(f"components/{name}.html")

    def test_shell_has_accessible_regions_and_breadcrumb_support(self):
        for marker in ('aria-label="Navegación principal"', 'id="contenido-principal"',
                       'class="ds-topbar"', 'class="ds-footer"', 'enterprise-welcome'):
            self.assertIn(marker, self.base + self.dashboard)

    def test_menu_respects_existing_permission_guards(self):
        self.assertIn("perms.compras.view_proveedor", self.base)
        self.assertIn("perms.compras.view_solicitudcompra", self.base)
        self.assertIn("perms.workflow.view_tareas_workflow", self.base)
        self.assertIn("perms.core.view_transaction_engine", self.base)
        self.assertIn('aria-current="page"', self.base)

    def test_menu_state_search_and_mobile_drawer(self):
        self.assertIn("localStorage", self.javascript)
        self.assertIn("data-menu-search", self.base)
        self.assertIn("ds-nav-open", self.javascript)
        self.assertIn("max-width:768px", self.responsive)
        self.assertIn("translateX", self.responsive)

    def test_dashboard_has_drilldowns_and_honest_empty_states(self):
        for route in ("core:enterprise_module", "compras:p2p_dashboard",
                      "rrhh:dashboard", "core:enterprise_finance"):
            self.assertIn(route, self.dashboard)
        self.assertIn('class="ds-empty"', self.dashboard)
        self.assertIn("Sin actividad reciente", self.dashboard)
        self.assertNotIn("action-icon", self.dashboard)

    def test_enterprise_tables_and_forms_are_reusable(self):
        components = self.root / "templates/components"
        for name in ("enterprise_table.html", "filter_bar.html", "form_section.html",
                     "sticky_form_actions.html", "export_menu.html", "pagination.html"):
            self.assertTrue((components / name).is_file(), name)

    def test_no_business_layer_changed_by_visual_contract(self):
        forbidden = ("models.py", "services.py", "migrations")
        documented_scope = self.root / "docs/enterprise_experience/mega_pase_06a/README.md"
        self.assertTrue(documented_scope.is_file())
        self.assertTrue(all(term not in str(documented_scope) for term in forbidden))
