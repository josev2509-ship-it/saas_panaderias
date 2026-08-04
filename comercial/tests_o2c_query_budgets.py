from django.contrib.auth.models import User
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection

from conduces.models import Empresa
from catalogos.models import Moneda,MonedaEmpresa
from comercial.models import Cliente,FacturaVenta,CuentaPorCobrar,ReciboCobro
from comercial.api.finanzas import dashboard, estados, facturas, cobros, cuentas_cobrar
from comercial.application.financial_exports import exportar
from core.application.operation_context import OperationContext
from datetime import date


class O2CQueryBudgetsTest(TestCase):
    """Budgets are upper bounds and must remain independent from row count."""
    DASHBOARD_MAX = 18
    FINANCIAL_REPORTS_MAX = 6
    LIST_MAX = 4
    EXPORT_MAX = 10

    def setUp(self):
        self.user=User.objects.create_superuser("query-o2c","query@example.invalid","x");self.empresa=Empresa.objects.create(usuario=self.user,nombre="Query O2C");currency=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$");self.moneda=MonedaEmpresa.objects.create(empresa=self.empresa,moneda=currency,es_base=True);self.cliente=Cliente.objects.create(empresa=self.empresa,codigo="C1",tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,nombre_comercial="Cliente",condicion_pago=Cliente.CondicionPago.CREDITO,moneda_comercial=self.moneda,creado_por=self.user);self.context=OperationContext(empresa=self.empresa,usuario=self.user)
        invoices=[FacturaVenta(empresa=self.empresa,numero=f"F{i}",cliente=self.cliente,moneda=self.moneda,fecha=date(2026,8,1),vence_el=date(2026,9,1),estado="EMITIDA",total=100,creado_por=self.user) for i in range(30)];FacturaVenta.objects.bulk_create(invoices)
        CuentaPorCobrar.objects.bulk_create([CuentaPorCobrar(empresa=self.empresa,factura=f,cliente=self.cliente,moneda=self.moneda,fecha_emision=f.fecha,fecha_vencimiento=f.vence_el,monto_original=100,saldo=100,creado_por=self.user) for f in FacturaVenta.objects.all()]);ReciboCobro.objects.bulk_create([ReciboCobro(empresa=self.empresa,numero=f"R{i}",cliente=self.cliente,moneda=self.moneda,fecha=date(2026,8,1),metodo="TRANSFERENCIA",monto=100,creado_por=self.user) for i in range(30)])

    def test_dashboard_initial_budget(self):
        with CaptureQueriesContext(connection) as captured: dashboard(empresa=self.empresa)
        self.assertLessEqual(len(captured), self.DASHBOARD_MAX)

    def test_accounting_reports_budget(self):
        with CaptureQueriesContext(connection) as captured: estados(empresa=self.empresa)
        self.assertLessEqual(len(captured), self.FINANCIAL_REPORTS_MAX)

    def test_facturas_list_filter_notes_budget(self):
        with CaptureQueriesContext(connection) as captured: rows=facturas(empresa=self.empresa,moneda=self.moneda,cliente=self.cliente)
        self.assertEqual(len(rows),30);self.assertLessEqual(len(captured),self.LIST_MAX)

    def test_cobros_list_detail_applications_budget(self):
        with CaptureQueriesContext(connection) as captured: rows=cobros(empresa=self.empresa,moneda=self.moneda,cliente=self.cliente)
        self.assertEqual(len(rows),30);self.assertLessEqual(len(captured),self.LIST_MAX)

    def test_cxc_aging_exposure_currency_budget(self):
        with CaptureQueriesContext(connection) as captured: rows=cuentas_cobrar(empresa=self.empresa,moneda=self.moneda,cliente=self.cliente,estado="PENDIENTE")
        self.assertEqual(len(rows),30);self.assertLessEqual(len(captured),self.LIST_MAX)

    def test_dashboard_currency_and_drilldown_budgets(self):
        with CaptureQueriesContext(connection) as captured:dashboard(empresa=self.empresa,moneda=self.moneda)
        self.assertLessEqual(len(captured),20)
        with CaptureQueriesContext(connection) as captured:dashboard(empresa=self.empresa,moneda=self.moneda,centro=999999)
        self.assertLessEqual(len(captured),21)

    def test_export_csv_xlsx_pdf_budgets(self):
        for formato in ("csv","xlsx","pdf"):
            with CaptureQueriesContext(connection) as captured:result=exportar(context=self.context,tipo="facturas",formato=formato)
            self.assertTrue(result.contenido);self.assertLessEqual(len(captured),self.EXPORT_MAX,formato)
