from datetime import date
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from catalogos.models import Moneda, MonedaEmpresa
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from .models import CuentaBancariaEmpresa, ImportacionExtractoBancario, LineaExtractoBancario, MovimientoTesoreria
from .services import sugerir_coincidencias


class TreasuryQueryBudgetsTest(TestCase):
    # Dos SELECT de datos y cuatro sentencias de control transaccional de TestCase/atomic.
    MATCHING_MAX = 6

    def setUp(self):
        user=User.objects.create_user("query-treasury");self.empresa=Empresa.objects.create(usuario=user,nombre="Query Treasury");currency=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$");me=MonedaEmpresa.objects.create(empresa=self.empresa,moneda=currency,es_base=True);self.cuenta=CuentaBancariaEmpresa.objects.create(empresa=self.empresa,banco="Banco",numero_enmascarado="***1",moneda=me);self.importacion=ImportacionExtractoBancario.objects.create(empresa=self.empresa,cuenta=self.cuenta,nombre_archivo="x.csv",formato="CSV",huella="a"*64);self.ctx=OperationContext(empresa=self.empresa,usuario=user)
        MovimientoTesoreria.objects.bulk_create([MovimientoTesoreria(empresa=self.empresa,cuenta=self.cuenta,tipo="INGRESO",fecha=date(2026,8,2),monto=i+1,referencia=f"R{i}") for i in range(30)])
        LineaExtractoBancario.objects.bulk_create([LineaExtractoBancario(importacion=self.importacion,numero=i+1,fecha=date(2026,8,2),descripcion="Ingreso",referencia=f"R{i}",monto=i+1,huella=f"{i:064d}") for i in range(30)])

    def test_matching_budget_is_constant_for_thirty_rows(self):
        with CaptureQueriesContext(connection) as captured: result=sugerir_coincidencias(context=self.ctx,importacion=self.importacion)
        self.assertEqual(len(result),30);self.assertLessEqual(len(captured),self.MATCHING_MAX)
