from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.templatetags.static import static
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from conduces.models import Empresa


ROOT = Path(__file__).resolve().parents[2]


class DemoUnificadoContractTests(SimpleTestCase):
    def test_shell_loads_demo_convergence_once(self):
        source = (ROOT / "panaderia_saas/templates/base.html").read_text(encoding="utf-8")
        self.assertEqual(source.count("demo_unified.css"), 1)
        self.assertEqual(source.count("demo_unified.js"), 1)

    def test_visual_layer_covers_legacy_primitives_and_responsive(self):
        css = (ROOT / "conduces/static/design_system/css/demo_unified.css").read_text(encoding="utf-8")
        for marker in (".ds-demo-breadcrumbs", ".ds-demo-title", ".card", "table", "form label", "@media(max-width:768px)"):
            self.assertIn(marker, css)

    def test_progressive_layer_adds_breadcrumbs_forms_and_empty_states(self):
        script = (ROOT / "conduces/static/design_system/js/demo_unified.js").read_text(encoding="utf-8")
        for marker in ("ds-demo-breadcrumbs", "demoForm", "ds-demo-form-actions", "ds-demo-empty"):
            self.assertIn(marker, script)

    def test_login_uses_enterprise_brand_without_permanent_emoji(self):
        source = (ROOT / "conduces/templates/login.html").read_text(encoding="utf-8")
        self.assertIn("SASTRE ERP Enterprise", source)
        for emoji in ("🥖", "✔", "👁", "🔐", "📊", "📄"):
            self.assertNotIn(emoji, source)

    def test_navigation_keeps_recommended_domain_order(self):
        source = (ROOT / "panaderia_saas/templates/base.html").read_text(encoding="utf-8")
        positions = [source.index(f'data-group="{name}"') for name in (
            "inicio", "comercial", "operaciones", "compras", "inventario",
            "produccion", "finanzas", "reportes", "administracion",
        )]
        self.assertEqual(positions, sorted(positions))

    def test_demo_pipeline_bootstraps_currency_and_p2p_list_uses_real_date(self):
        pipeline = (ROOT / "conduces/management/commands/generar_demo_ready.py").read_text(encoding="utf-8")
        p2p_list = (ROOT / "compras/templates/compras/p2p/recurso_lista.html").read_text(encoding="utf-8")
        self.assertIn("MonedaEmpresa.objects.get_or_create", pipeline)
        self.assertIn('item.fecha|date:"Y-m-d"', p2p_list)
        self.assertNotIn("item.creado_en", p2p_list)


class DemoUnificadoRouteSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("demo-d1", "demo-d1@example.test", "test-only")
        Empresa.objects.create(
            usuario=cls.user,
            nombre="Empresa Demo D1",
            modulo_conduces=True,
            modulo_facturacion=True,
            modulo_inventario=True,
            modulo_compras=True,
            modulo_catalogos=True,
            modulo_workflow=True,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_representative_demo_routes_render_without_server_errors(self):
        routes = (
            reverse("inicio"), reverse("core:workspace_home"), reverse("core:alertas"),
            reverse("core:actividad"), reverse("comercial:dashboard"),
            reverse("comercial:crm_dashboard"), reverse("comercial:clientes_lista"),
            reverse("comercial:pedidos_lista"), reverse("compras:dashboard"),
            reverse("compras:lista"), reverse("compras:solicitudes_lista"),
            reverse("compras:p2p_recurso_lista", args=["ordenes"]),
            reverse("compras:p2p_recurso_lista", args=["recepciones"]),
            reverse("inventario:dashboard"), reverse("inventario:productos"),
            reverse("inventario:produccion_dashboard"), reverse("contabilidad:dashboard_enterprise"),
            reverse("contabilidad:reportes_financieros"), reverse("buscar_conduces"),
            reverse("facturacion"), reverse("calendario_escolar"),
        )
        for url in routes:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertLess(response.status_code, 500)
                self.assertIn(response.status_code, (200, 302, 403))

    def test_demo_pages_load_unified_assets(self):
        response = self.client.get(reverse("comercial:clientes_lista"))
        self.assertContains(response, static("design_system/css/demo_unified.css"))
        self.assertContains(response, static("design_system/js/demo_unified.js"))

    def test_login_remains_anonymous_and_functional(self):
        self.client.logout()
        response = self.client.get(reverse("login_usuario"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_demo_generator_is_complete_and_idempotent(self):
        from comercial.models import CuentaPorCobrar, EntregaComercial, FacturaVenta, Pedido, ReciboCobro
        from contabilidad.models import AsientoContable
        from conduces.models import CentroEducativo, Conduce, Factura, MenuDiario
        from inventario.models import MovimientoInventario, OrdenProduccion, PlanProduccion, RecetaProduccion

        empresa = Empresa.objects.get(usuario=self.user)
        call_command("generar_demo_ready", empresa=empresa.pk, verbosity=0)
        first = (
            Pedido.objects.filter(empresa=empresa).count(),
            EntregaComercial.objects.filter(empresa=empresa).count(),
            FacturaVenta.objects.filter(empresa=empresa).count(),
            CuentaPorCobrar.objects.filter(empresa=empresa).count(),
            ReciboCobro.objects.filter(empresa=empresa).count(),
            AsientoContable.objects.filter(empresa=empresa).count(),
            CentroEducativo.objects.filter(empresa=empresa).count(),
            MenuDiario.objects.filter(empresa=empresa).count(),
            Conduce.objects.filter(empresa=empresa).count(),
            Factura.objects.filter(empresa=empresa).count(),
            RecetaProduccion.objects.filter(empresa=empresa).count(),
            PlanProduccion.objects.filter(empresa=empresa).count(),
            OrdenProduccion.objects.filter(empresa=empresa).count(),
            MovimientoInventario.objects.filter(empresa=empresa).count(),
        )
        call_command("generar_demo_ready", empresa=empresa.pk, verbosity=0)
        self.assertEqual(first, (
            Pedido.objects.filter(empresa=empresa).count(),
            EntregaComercial.objects.filter(empresa=empresa).count(),
            FacturaVenta.objects.filter(empresa=empresa).count(),
            CuentaPorCobrar.objects.filter(empresa=empresa).count(),
            ReciboCobro.objects.filter(empresa=empresa).count(),
            AsientoContable.objects.filter(empresa=empresa).count(),
            CentroEducativo.objects.filter(empresa=empresa).count(),
            MenuDiario.objects.filter(empresa=empresa).count(),
            Conduce.objects.filter(empresa=empresa).count(),
            Factura.objects.filter(empresa=empresa).count(),
            RecetaProduccion.objects.filter(empresa=empresa).count(),
            PlanProduccion.objects.filter(empresa=empresa).count(),
            OrdenProduccion.objects.filter(empresa=empresa).count(),
            MovimientoInventario.objects.filter(empresa=empresa).count(),
        ))
        self.assertTrue(all(value > 0 for value in first))
