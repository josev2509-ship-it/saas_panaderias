from pathlib import Path

from django.template.loader import get_template
from django.contrib.auth.models import User
from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from conduces.models import Empresa


ROOT = Path(__file__).resolve().parents[2]


class EnterpriseListExperienceContractTests(SimpleTestCase):
    canonical_templates = (
        "comercial/clientes_lista.html",
        "comercial/pedidos_lista.html",
        "comercial/crm/lista.html",
        "comercial/o2c/lista.html",
        "comercial/o2c/programacion.html",
        "comercial/o2c_full/lista.html",
        "comercial/programacion.html",
        "compras/lista.html",
        "compras/solicitudes/lista.html",
        "compras/expedientes/lista.html",
        "compras/rfq/lista.html",
        "compras/p2p/recurso_lista.html",
        "compras/p2p/finance_list.html",
        "buscar_conduces.html",
        "inventario/productos.html",
        "inventario/movimientos.html",
        "inventario/planes_lista.html",
        "inventario/ordenes_lista.html",
        "inventario/necesidades.html",
    )

    def test_all_canonical_templates_compile(self):
        for name in self.canonical_templates:
            with self.subTest(template=name):
                self.assertIsNotNone(get_template(name))

    def test_every_migrated_template_has_explicit_contract(self):
        for name in self.canonical_templates:
            source = get_template(name).template.source
            with self.subTest(template=name):
                self.assertIn("data-enterprise-list", source)

    def test_shared_header_contract(self):
        source = (ROOT / "templates/components/enterprise_list_header.html").read_text(encoding="utf-8")
        for marker in ("data-enterprise-page-header", "el-breadcrumbs", "el-count", "Actualizado"):
            self.assertIn(marker, source)

    def test_command_bar_contract(self):
        source = (ROOT / "templates/components/enterprise_list_command_bar.html").read_text(encoding="utf-8")
        for marker in ("data-el-search", "data-el-filters", "data-el-columns", "data-el-density", "data-el-refresh"):
            self.assertIn(marker, source)

    def test_table_javascript_supports_search_columns_density_and_empty_results(self):
        source = (ROOT / "conduces/static/design_system/js/enterprise_list.js").read_text(encoding="utf-8")
        for marker in ("el-density-compact", "data-el-column-options", "No encontramos resultados", "sessionStorage"):
            self.assertIn(marker, source)

    def test_responsive_contract_has_no_global_horizontal_scroll(self):
        source = (ROOT / "conduces/static/design_system/css/enterprise_list.css").read_text(encoding="utf-8")
        self.assertIn("@media(max-width:768px)", source)
        self.assertIn("overflow:visible", source)

    def test_empty_states_are_distinct(self):
        sources = "\n".join(get_template(name).template.source for name in self.canonical_templates)
        self.assertIn("Todavía no existen registros", sources)
        self.assertIn("No encontramos resultados", sources)

    def test_business_actions_remain_in_domain_templates(self):
        o2c = get_template("comercial/o2c_full/lista.html").template.source
        for action in ("Preparar", "Validar", "Completar", "Despachar", "Emitir conduce", "Entregar", "Facturar", "Cobrar"):
            self.assertIn(action, o2c)

    def test_no_new_destructive_action_in_shared_components(self):
        shared = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "templates/components/enterprise_list_header.html",
                "templates/components/enterprise_list_command_bar.html",
            )
        )
        for action in ("Aprobar", "Rechazar", "Anular", "Revertir", "Pagar", "Cobrar", "Eliminar"):
            self.assertNotIn(action, shared)

    def test_base_loads_one_reusable_asset_pair(self):
        source = get_template("base.html").template.source
        self.assertEqual(source.count("enterprise_list.css"), 1)
        self.assertEqual(source.count("enterprise_list.js"), 1)


class EnterpriseListQueryBudgetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username="enterprise-list-budget",
            email="enterprise-list-budget@example.test",
            password="test-only",
        )
        Empresa.objects.create(
            usuario=cls.user,
            nombre="Tenant Enterprise List",
            modulo_inventario=True,
            modulo_compras=True,
            modulo_workflow=True,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_priority_list_query_budgets(self):
        routes = (
            ("clientes", reverse("comercial:clientes_lista"), 20),
            ("pedidos", reverse("comercial:pedidos_lista"), 24),
            ("ordenes_compra", reverse("compras:p2p_recurso_lista", args=["ordenes"]), 18),
            ("facturas", reverse("comercial:o2c_full_lista", args=["facturas"]), 18),
            ("cxc", reverse("comercial:o2c_full_lista", args=["cxc"]), 18),
            ("cxp", reverse("compras:p2p_recurso_lista", args=["cxp"]), 18),
            ("productos", reverse("inventario:productos"), 20),
            ("conciliaciones", reverse("compras:p2p_finance_list", args=["conciliaciones"]), 16),
        )
        for name, url, limit in routes:
            with self.subTest(list=name), CaptureQueriesContext(connection) as queries:
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertLessEqual(len(queries), limit)
