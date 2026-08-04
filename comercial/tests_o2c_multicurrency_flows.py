from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from catalogos.models import Moneda, MonedaEmpresa, TasaCambio
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from contabilidad.models import PlanCuenta, CuentaContable, PeriodoContable, DiarioContable, ReglaContabilizacion, AsientoContable
from tesoreria.models import CuentaBancariaEmpresa
from comercial.models import Cliente, FacturaVenta, CuentaPorCobrar, AplicacionCobro, NotaCreditoVenta, NotaDebitoVenta
from comercial.application.o2c_full import registrar_cobro, aplicar_cobro, emitir_nota_credito, solicitar_factoring
from comercial.application.financial_integration import emitir_nota_debito_integrada, integrar_cobro, revertir_cobro_integral


class O2CMulticurrencyFlowsTest(TestCase):
    def setUp(self):
        self.user=User.objects.create_superuser("multi-flow","multi@example.invalid","x");self.empresa=Empresa.objects.create(usuario=self.user,nombre="Multi Flow")
        dop=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$");usd=Moneda.objects.create(codigo="USD",nombre="Dólar",simbolo="US$")
        self.dop=MonedaEmpresa.objects.create(empresa=self.empresa,moneda=dop,es_base=True);self.usd=MonedaEmpresa.objects.create(empresa=self.empresa,moneda=usd)
        for day,rate in enumerate(("59","60","61","62"),1):TasaCambio.objects.create(empresa=self.empresa,moneda=self.usd,tasa=rate,vigente_desde=date(2026,8,day))
        self.client=Cliente.objects.create(empresa=self.empresa,codigo="C1",tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,nombre_comercial="Cliente",condicion_pago=Cliente.CondicionPago.CREDITO,moneda_comercial=self.usd,creado_por=self.user);self.ctx=OperationContext(empresa=self.empresa,usuario=self.user,clave_idempotente="multi")
        plan=PlanCuenta.objects.create(empresa=self.empresa,codigo="P",nombre="Plan",creado_por=self.user)
        for code,name,t,n in (("1102","Banco","ACTIVO","DEBITO"),("1201","CxC","ACTIVO","DEBITO"),("4101","Ventas","INGRESO","CREDITO"),("4201","Ganancia cambio","INGRESO","CREDITO"),("6201","Pérdida cambio","GASTO","DEBITO")):
            CuentaContable.objects.create(empresa=self.empresa,plan=plan,codigo=code,nombre=name,tipo=t,naturaleza=n,creado_por=self.user)
        PeriodoContable.objects.create(empresa=self.empresa,anio=2026,mes=8,fecha_inicio=date(2026,8,1),fecha_fin=date(2026,8,31),creado_por=self.user);DiarioContable.objects.create(empresa=self.empresa,codigo="GENERAL",nombre="General",creado_por=self.user)
        ReglaContabilizacion.objects.create(empresa=self.empresa,evento="COBRO",configuracion={"debito":"1102","credito":"1201"},creado_por=self.user);ReglaContabilizacion.objects.create(empresa=self.empresa,evento="NOTA_DEBITO_VENTA",configuracion={"debito":"1201","credito":"4101"},creado_por=self.user);ReglaContabilizacion.objects.create(empresa=self.empresa,evento="DIFERENCIA_CAMBIARIA",configuracion={"contrapartida":"1201","ganancia":"4201","perdida":"6201"},creado_por=self.user)
        self.bank_dop=CuentaBancariaEmpresa.objects.create(empresa=self.empresa,banco="Banco",numero_enmascarado="***1",moneda=self.dop);self.bank_usd=CuentaBancariaEmpresa.objects.create(empresa=self.empresa,banco="Banco",numero_enmascarado="***2",moneda=self.usd)

    def invoice(self,num="F1",moneda=None,tasa="60",total="100",dims=None):
        moneda=moneda or self.usd;f=FacturaVenta.objects.create(empresa=self.empresa,numero=num,cliente=self.client,moneda=moneda,tasa_cambio=tasa,dimensiones=dims or {},fecha=date(2026,8,2),vence_el=date(2026,9,2),estado="EMITIDA",total=total,creado_por=self.user);CuentaPorCobrar.objects.create(empresa=self.empresa,factura=f,cliente=self.client,moneda=moneda,fecha_emision=f.fecha,fecha_vencimiento=f.vence_el,monto_original=total,saldo=total,creado_por=self.user);return f

    def test_01_factura_usd_cobrada_usd_preserva_tasas(self):
        f=self.invoice();r=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.usd,monto=40,metodo="TRANSFERENCIA",tasa_cambio=61);aplicar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_id=f.cuenta_cobrar.pk,monto=40,monto_cuenta=40);a=AplicacionCobro.objects.get();self.assertEqual((a.tasa_factura,a.tasa_cobro),(Decimal("60"),Decimal("61")))
    def test_02_factura_usd_cobrada_dop(self):
        f=self.invoice();r=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.dop,monto=6100,metodo="TRANSFERENCIA");aplicar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_id=f.cuenta_cobrar.pk,monto=6100,monto_cuenta=100);self.assertEqual(AplicacionCobro.objects.get().diferencia_cambiaria,Decimal("100.00"))
    def test_03_factura_dop_cobrada_usd(self):
        f=self.invoice(moneda=self.dop,tasa=1,total=6000);r=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.usd,monto=100,metodo="TRANSFERENCIA",tasa_cambio=59);aplicar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_id=f.cuenta_cobrar.pk,monto=100,monto_cuenta=6000);self.assertEqual(AplicacionCobro.objects.get().diferencia_cambiaria,Decimal("-100.00"))
    def test_04_cobro_parcial_y_segundo_con_tasa_distinta(self):
        f=self.invoice();r1=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.usd,monto=40,metodo="TRANSFERENCIA",tasa_cambio=59);aplicar_cobro(context=self.ctx,recibo_id=r1.pk,cuenta_id=f.cuenta_cobrar.pk,monto=40);r2=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.usd,monto=60,metodo="TRANSFERENCIA",tasa_cambio=62);aplicar_cobro(context=self.ctx,recibo_id=r2.pk,cuenta_id=f.cuenta_cobrar.pk,monto=60);self.assertEqual(list(AplicacionCobro.objects.order_by("pk").values_list("tasa_cobro",flat=True)),[Decimal("59"),Decimal("62")])
    def test_05_diferencia_positiva_contabilizada_balanceada(self):
        f=self.invoice();r=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.dop,monto=6100,metodo="TRANSFERENCIA");aplicar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_id=f.cuenta_cobrar.pk,monto=6100,monto_cuenta=100);integrar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_bancaria_id=self.bank_dop.pk);a=AsientoContable.objects.get(origen_tipo="DIFERENCIA_CAMBIARIA");self.assertEqual(a.total_debito,a.total_credito)
    def test_06_reversion_revierte_diferencia(self):
        f=self.invoice();r=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.dop,monto=6100,metodo="TRANSFERENCIA");aplicar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_id=f.cuenta_cobrar.pk,monto=6100,monto_cuenta=100);integrar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_bancaria_id=self.bank_dop.pk);revertir_cobro_integral(context=self.ctx,recibo_id=r.pk,motivo="Error");self.assertEqual(AsientoContable.objects.get(origen_tipo="DIFERENCIA_CAMBIARIA").estado,"REVERSADO")
    def test_07_nota_credito_hereda_snapshot(self):
        f=self.invoice(dims={"SUCURSAL":"SD"});n=emitir_nota_credito(context=self.ctx,factura_id=f.pk,monto=20,motivo="NC");self.assertEqual((n.moneda,n.tasa_cambio,n.dimensiones),(self.usd,Decimal("60"),f.dimensiones))
    def test_08_nota_debito_hereda_snapshot(self):
        f=self.invoice(dims={"SUCURSAL":"SD"});result=emitir_nota_debito_integrada(context=self.ctx,factura_id=f.pk,monto=10,motivo="ND");n=NotaDebitoVenta.objects.get(pk=result["nota_id"]);self.assertEqual((n.moneda,n.tasa_cambio,n.dimensiones),(self.usd,Decimal("60"),f.dimensiones))
    def test_09_factoring_hereda_moneda_tasa_dimensiones(self):
        f=self.invoice(dims={"SUCURSAL":"SD"});c=solicitar_factoring(context=self.ctx,cuenta_id=f.cuenta_cobrar.pk,factor="Factor",porcentaje=80);self.assertEqual((c.moneda,c.tasa_cambio,c.dimensiones),(self.usd,Decimal("60"),f.dimensiones))
    def test_10_cxc_permanece_en_moneda_original(self):
        f=self.invoice();r=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.dop,monto=3050,metodo="TRANSFERENCIA");aplicar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_id=f.cuenta_cobrar.pk,monto=3050,monto_cuenta=50);f.cuenta_cobrar.refresh_from_db();self.assertEqual((f.cuenta_cobrar.moneda,f.cuenta_cobrar.saldo),(self.usd,Decimal("50")))
