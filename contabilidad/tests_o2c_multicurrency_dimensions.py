from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from catalogos.models import Moneda, MonedaEmpresa, TasaCambio
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from .api import contabilizar
from .reportes import diario, mayor, saldos, estado_resultados, balance_general
from .models import (AsientoContable, CuentaContable, DiarioContable, DimensionContable,
                     PeriodoContable, PlanCuenta, ValorDimensionContable)


class MulticurrencyDimensionsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("semantic", "semantic@example.invalid", "x")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Semántica O2C")
        dop = Moneda.objects.create(codigo="DOP", nombre="Peso", simbolo="$")
        usd = Moneda.objects.create(codigo="USD", nombre="Dólar", simbolo="US$")
        self.dop = MonedaEmpresa.objects.create(empresa=self.empresa, moneda=dop, es_base=True)
        self.usd = MonedaEmpresa.objects.create(empresa=self.empresa, moneda=usd)
        self.tasa = TasaCambio.objects.create(empresa=self.empresa, moneda=self.usd, tasa="60.250000", vigente_desde=date(2026, 8, 1), vigente_hasta=date(2026, 8, 31))
        self.ctx = OperationContext(empresa=self.empresa, usuario=self.user, clave_idempotente="semantic")
        plan = PlanCuenta.objects.create(empresa=self.empresa, codigo="P", nombre="Plan", creado_por=self.user)
        self.debito = CuentaContable.objects.create(empresa=self.empresa, plan=plan, codigo="1101", nombre="CxC", tipo="ACTIVO", naturaleza="DEBITO", creado_por=self.user)
        self.credito = CuentaContable.objects.create(empresa=self.empresa, plan=plan, codigo="4101", nombre="Ventas", tipo="INGRESO", naturaleza="CREDITO", creado_por=self.user)
        PeriodoContable.objects.create(empresa=self.empresa, anio=2026, mes=8, fecha_inicio=date(2026, 8, 1), fecha_fin=date(2026, 8, 31), creado_por=self.user)
        DiarioContable.objects.create(empresa=self.empresa, codigo="GENERAL", nombre="General", creado_por=self.user)
        self.centro_dim = DimensionContable.objects.create(empresa=self.empresa, codigo="CENTRO_COSTO", nombre="Centro", creado_por=self.user)
        self.proyecto_dim = DimensionContable.objects.create(empresa=self.empresa, codigo="PROYECTO", nombre="Proyecto", creado_por=self.user)
        self.centro = ValorDimensionContable.objects.create(empresa=self.empresa, dimension=self.centro_dim, codigo="CC1", nombre="Centro 1", creado_por=self.user)
        self.proyecto = ValorDimensionContable.objects.create(empresa=self.empresa, dimension=self.proyecto_dim, codigo="PR1", nombre="Proyecto 1", creado_por=self.user)

    def post(self, oid="1", moneda=None, tasa=None, dimensiones=None):
        dims = dimensiones or {}
        return contabilizar(context=self.ctx, origen_tipo="SEMANTIC", origen_id=oid, concepto="Venta", fecha=date(2026, 8, 2), moneda=moneda, tasa_cambio=tasa, lineas=[{"cuenta": self.debito, "debito": 100, "dimensiones": dims}, {"cuenta": self.credito, "credito": 100, "dimensiones": dims}])

    def test_01_moneda_base_fija_tasa_uno(self): self.assertEqual(self.post().tasa_cambio, Decimal("1"))
    def test_02_moneda_extranjera_vigente(self): self.assertEqual(self.post(moneda=self.usd, tasa=self.tasa.tasa).moneda, self.usd)
    def test_03_moneda_extranjera_sin_tasa(self):
        with self.assertRaises(ValidationError): self.post(moneda=self.usd)
    def test_04_tasa_cero(self):
        with self.assertRaises(ValidationError): self.post(moneda=self.usd, tasa=0)
    def test_05_tasa_negativa(self):
        with self.assertRaises(ValidationError): self.post(moneda=self.usd, tasa=-1)
    def test_06_tasa_expirada(self):
        self.tasa.vigente_hasta=date(2026, 8, 1); self.tasa.save()
        with self.assertRaises(ValidationError): self.post(moneda=self.usd, tasa=self.tasa.tasa)
    def test_07_moneda_cross_tenant(self):
        other_user=User.objects.create_user("other-semantic"); other=Empresa.objects.create(usuario=other_user,nombre="Otra")
        foreign=MonedaEmpresa.objects.create(empresa=other,moneda=self.usd.moneda)
        with self.assertRaises(ValidationError): self.post(moneda=foreign,tasa=self.tasa.tasa)
    def test_08_snapshot_idempotente(self):
        first=self.post(moneda=self.usd,tasa=self.tasa.tasa); self.tasa.tasa="61"; self.tasa.save()
        self.assertEqual(AsientoContable.objects.get(pk=first.pk).tasa_cambio,Decimal("60.250000"))
    def test_09_dimensiones_validas_propagadas(self):
        dims={"CENTRO_COSTO":self.centro.pk,"PROYECTO":self.proyecto.pk}; asiento=self.post(dimensiones=dims)
        self.assertTrue(all(linea.dimensiones==dims for linea in asiento.lineas.all()))
    def test_10_dimension_inactiva(self):
        self.centro.activo=False;self.centro.save()
        with self.assertRaises(ValidationError):self.post(dimensiones={"CENTRO_COSTO":self.centro.pk})
    def test_11_dimension_codigo_incorrecto(self):
        with self.assertRaises(ValidationError):self.post(dimensiones={"PROYECTO":self.centro.pk})
    def test_12_cuenta_exige_centro(self):
        self.debito.requiere_centro_costo=True;self.debito.save()
        with self.assertRaises(ValidationError):self.post()
    def test_13_cuenta_exige_proyecto(self):
        self.credito.requiere_proyecto=True;self.credito.save()
        with self.assertRaises(ValidationError):self.post(dimensiones={"CENTRO_COSTO":self.centro.pk})
    def test_14_fallo_dimension_no_persiste(self):
        with self.assertRaises(ValidationError):self.post(dimensiones={"CENTRO_COSTO":999999})
        self.assertFalse(AsientoContable.objects.exists())
    def test_15_diario_filtra_moneda_y_expone_base(self):
        self.post(moneda=self.usd,tasa=self.tasa.tasa,dimensiones={"CENTRO_COSTO":self.centro.pk});rows=diario(empresa=self.empresa,moneda=self.usd);self.assertEqual(len(rows),1);self.assertEqual(rows[0]["debito_base"],"6025.00000000")
    def test_16_mayor_filtra_centro(self):
        self.post(dimensiones={"CENTRO_COSTO":self.centro.pk});self.assertEqual(len(mayor(empresa=self.empresa,centro=self.centro.pk)),2);self.assertFalse(mayor(empresa=self.empresa,centro=999999))
    def test_17_mayor_filtra_proyecto(self):
        self.post(dimensiones={"PROYECTO":self.proyecto.pk});self.assertEqual(len(mayor(empresa=self.empresa,proyecto=self.proyecto.pk)),2)
    def test_18_balanza_transaccional_por_moneda(self):
        self.post(moneda=self.usd,tasa=self.tasa.tasa);rows=saldos(empresa=self.empresa,moneda=self.usd);self.assertEqual(sum(x["debito"] for x in rows),Decimal("100"))
    def test_19_resultados_por_proyecto(self):
        self.post(dimensiones={"PROYECTO":self.proyecto.pk});self.assertEqual(estado_resultados(empresa=self.empresa,proyecto=self.proyecto.pk)["ingresos"],"100")
    def test_20_balance_por_moneda(self):
        self.post(moneda=self.usd,tasa=self.tasa.tasa);self.assertEqual(balance_general(empresa=self.empresa,moneda=self.usd)["activo"],"100")
