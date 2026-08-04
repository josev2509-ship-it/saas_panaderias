from datetime import date,timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from catalogos.models import Moneda,MonedaEmpresa
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from contabilidad.models import PlanCuenta,CuentaContable,PeriodoContable,DiarioContable,ReglaContabilizacion,AsientoContable
from tesoreria.models import CuentaBancariaEmpresa,MovimientoTesoreria
from comercial.models import Cliente,FacturaVenta,CuentaPorCobrar,ReciboCobro,AplicacionCobro,NotaCreditoVenta,NotaDebitoVenta,CesionFactoring
from comercial.application.o2c_full import registrar_cobro,aplicar_cobro,solicitar_factoring,avanzar_factoring
from comercial.application.financial_integration import contabilizar_factura_emitida,integrar_cobro,emitir_nota_credito_integrada,emitir_nota_debito_integrada,revertir_cobro_integral,desembolsar_factoring

class O2CFinancialHardeningTest(TestCase):
 def setUp(self):
  self.u=User.objects.create_superuser("o2cf-hard","o@example.invalid","x");self.e=Empresa.objects.create(usuario=self.u,nombre="O2C Financial");m=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$");self.me=MonedaEmpresa.objects.create(empresa=self.e,moneda=m,es_base=True);self.ctx=OperationContext(empresa=self.e,usuario=self.u,clave_idempotente="o2cf-hard");self.client=Cliente.objects.create(empresa=self.e,codigo="C1",tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,nombre_comercial="Cliente",condicion_pago=Cliente.CondicionPago.CREDITO,dias_credito=30,limite_credito=10000,moneda_comercial=self.me,creado_por=self.u);p=PlanCuenta.objects.create(empresa=self.e,codigo="P",nombre="Plan",creado_por=self.u)
  for code,name,t,n in (("1102","Banco","ACTIVO","DEBITO"),("1201","CxC","ACTIVO","DEBITO"),("1301","Ret","ACTIVO","DEBITO"),("4101","Ingreso","INGRESO","CREDITO"),("6101","Gasto","GASTO","DEBITO")):CuentaContable.objects.create(empresa=self.e,plan=p,codigo=code,nombre=name,tipo=t,naturaleza=n,creado_por=self.u)
  PeriodoContable.objects.create(empresa=self.e,anio=2026,mes=8,fecha_inicio=date(2026,8,1),fecha_fin=date(2026,8,31),creado_por=self.u);DiarioContable.objects.create(empresa=self.e,codigo="GENERAL",nombre="General",creado_por=self.u)
  for ev,cfg in (("FACTURA_VENTA",{"debito":"1201","credito":"4101"}),("NOTA_CREDITO_VENTA",{"debito":"4101","credito":"1201"}),("NOTA_DEBITO_VENTA",{"debito":"1201","credito":"4101"}),("COBRO",{"debito":"1102","credito":"1201"}),("FACTORING",{"banco":"1102","gasto":"6101","retencion":"1301","cxc":"1201"})):ReglaContabilizacion.objects.create(empresa=self.e,evento=ev,configuracion=cfg,creado_por=self.u)
  self.bank=CuentaBancariaEmpresa.objects.create(empresa=self.e,banco="Banco",numero_enmascarado="****1111",moneda=self.me)
 def invoice(self,num="F1",total=1000,state="EMITIDA"):
  f=FacturaVenta.objects.create(empresa=self.e,numero=num,cliente=self.client,moneda=self.me,fecha=date(2026,8,3),vence_el=date(2026,9,3),estado=state,total=total,creado_por=self.u)
  if state!="BORRADOR":CuentaPorCobrar.objects.create(empresa=self.e,factura=f,cliente=self.client,moneda=self.me,fecha_emision=f.fecha,fecha_vencimiento=f.vence_el,monto_original=total,saldo=total,creado_por=self.u)
  return f
 def receipt(self,cuenta,monto=100,num="R"):
  r=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.me,monto=monto,metodo="TRANSFERENCIA",referencia=num);aplicar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_id=cuenta.pk,monto=monto);return r
 def test_01_factura_emitida_contabiliza(self):self.assertTrue(contabilizar_factura_emitida(context=self.ctx,factura_id=self.invoice().pk).asiento_id)
 def test_02_factura_reintento_asiento_unico(self):f=self.invoice();a=contabilizar_factura_emitida(context=self.ctx,factura_id=f.pk);b=contabilizar_factura_emitida(context=self.ctx,factura_id=f.pk);self.assertEqual(a.asiento_id,b.asiento_id)
 def test_03_factura_anulada_no_contabiliza(self):
  with self.assertRaises(ValidationError):contabilizar_factura_emitida(context=self.ctx,factura_id=self.invoice(state="ANULADA").pk)
 def test_04_factura_borrador_no_contabiliza(self):
  with self.assertRaises(ValidationError):contabilizar_factura_emitida(context=self.ctx,factura_id=self.invoice(state="BORRADOR").pk)
 def test_05_cxc_unica_por_factura(self):
  f=self.invoice()
  with self.assertRaises(IntegrityError):CuentaPorCobrar.objects.create(empresa=self.e,factura=f,cliente=self.client,moneda=self.me,fecha_emision=f.fecha,fecha_vencimiento=f.vence_el,monto_original=1,saldo=1,creado_por=self.u)
 def test_06_asiento_venta_unico(self):f=self.invoice();contabilizar_factura_emitida(context=self.ctx,factura_id=f.pk);contabilizar_factura_emitida(context=self.ctx,factura_id=f.pk);self.assertEqual(AsientoContable.objects.filter(origen_tipo="FACTURA_VENTA").count(),1)
 def test_07_nota_credito_parcial(self):f=self.invoice();contabilizar_factura_emitida(context=self.ctx,factura_id=f.pk);r=emitir_nota_credito_integrada(context=self.ctx,factura_id=f.pk,monto=100,motivo="NC");self.assertEqual(r["saldo"],"900.00")
 def test_08_nota_credito_total(self):f=self.invoice();contabilizar_factura_emitida(context=self.ctx,factura_id=f.pk);r=emitir_nota_credito_integrada(context=self.ctx,factura_id=f.pk,monto=1000,motivo="Total");self.assertEqual(r["saldo"],"0.00")
 def test_09_nota_credito_excesiva(self):
  f=self.invoice()
  with self.assertRaises(ValidationError):emitir_nota_credito_integrada(context=self.ctx,factura_id=f.pk,monto=1001,motivo="Exceso")
 def test_10_nota_credito_idempotente(self):f=self.invoice();contabilizar_factura_emitida(context=self.ctx,factura_id=f.pk);a=emitir_nota_credito_integrada(context=self.ctx,factura_id=f.pk,monto=100,motivo="Misma");b=emitir_nota_credito_integrada(context=self.ctx,factura_id=f.pk,monto=100,motivo="Misma");self.assertEqual(a["nota_id"],b["nota_id"]);self.assertEqual(NotaCreditoVenta.objects.count(),1)
 def test_11_nota_debito_valida(self):f=self.invoice();contabilizar_factura_emitida(context=self.ctx,factura_id=f.pk);self.assertEqual(emitir_nota_debito_integrada(context=self.ctx,factura_id=f.pk,monto=50,motivo="ND")["saldo"],"1050.00")
 def test_12_nota_debito_idempotente(self):f=self.invoice();contabilizar_factura_emitida(context=self.ctx,factura_id=f.pk);a=emitir_nota_debito_integrada(context=self.ctx,factura_id=f.pk,monto=50,motivo="ND");b=emitir_nota_debito_integrada(context=self.ctx,factura_id=f.pk,monto=50,motivo="ND");self.assertEqual(a["nota_id"],b["nota_id"]);self.assertEqual(NotaDebitoVenta.objects.count(),1)
 def test_13_cobro_parcial(self):f=self.invoice();r=self.receipt(f.cuenta_cobrar,100);f.cuenta_cobrar.refresh_from_db();self.assertEqual(f.cuenta_cobrar.estado,"PARCIAL")
 def test_14_cobro_total(self):f=self.invoice();self.receipt(f.cuenta_cobrar,1000);f.cuenta_cobrar.refresh_from_db();self.assertEqual(f.cuenta_cobrar.estado,"COBRADA")
 def test_15_cobro_multiples_facturas(self):f1=self.invoice("F1",500);f2=self.invoice("F2",500);r=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.me,monto=1000,metodo="TRANSFERENCIA");aplicar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_id=f1.cuenta_cobrar.pk,monto=500);aplicar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_id=f2.cuenta_cobrar.pk,monto=500);self.assertEqual(r.aplicaciones.count(),2)
 def test_16_sobreaplicacion_bloqueada(self):
  f=self.invoice();r=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.me,monto=100,metodo="TRANSFERENCIA")
  with self.assertRaises(ValidationError):aplicar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_id=f.cuenta_cobrar.pk,monto=101)
 def test_17_integracion_cobro_idempotente(self):f=self.invoice();r=self.receipt(f.cuenta_cobrar,100);a=integrar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_bancaria_id=self.bank.pk);b=integrar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_bancaria_id=self.bank.pk);self.assertEqual(a.movimiento_id,b.movimiento_id)
 def test_18_reversion_integral_idempotente(self):f=self.invoice();contabilizar_factura_emitida(context=self.ctx,factura_id=f.pk);r=self.receipt(f.cuenta_cobrar,100);integrar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_bancaria_id=self.bank.pk);a=revertir_cobro_integral(context=self.ctx,recibo_id=r.pk,motivo="Error");b=revertir_cobro_integral(context=self.ctx,recibo_id=r.pk,motivo="Error");self.assertEqual((a["estado"],b["estado"]),("REVERTIDO","REVERTIDO"))
 def test_19_factoring_valido(self):f=self.invoice();c=solicitar_factoring(context=self.ctx,cuenta_id=f.cuenta_cobrar.pk,factor="Factor",porcentaje=80);c=avanzar_factoring(context=self.ctx,pk=c.pk,estado="APROBADA");r=desembolsar_factoring(context=self.ctx,cesion_id=c.pk,cuenta_bancaria_id=self.bank.pk,comision=10,costo_financiero=10,referencia="FAC");self.assertEqual(r["neto"],"980.00")
 def test_20_factoring_duplicado_bloqueado(self):
  f=self.invoice();solicitar_factoring(context=self.ctx,cuenta_id=f.cuenta_cobrar.pk,factor="A",porcentaje=80)
  with self.assertRaises(IntegrityError):solicitar_factoring(context=self.ctx,cuenta_id=f.cuenta_cobrar.pk,factor="B",porcentaje=80)
