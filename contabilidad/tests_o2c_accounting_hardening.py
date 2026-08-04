from datetime import date
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from catalogos.models import Moneda,MonedaEmpresa
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from core.models import EventoDominio
from auditoria.models import EventoAuditoria
from .api import contabilizar,contabilizar_factura_venta,ResultadoContabilizacion
from .models import PlanCuenta,CuentaContable,PeriodoContable,DiarioContable,ReglaContabilizacion,AsientoContable
from .services import cerrar_periodo,reabrir_periodo,revertir_asiento

class AccountingHardeningTest(TestCase):
 def setUp(self):
  self.u=User.objects.create_superuser("acct-hard","a@example.invalid","x");self.e=Empresa.objects.create(usuario=self.u,nombre="Accounting Hardening");m=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$");self.me=MonedaEmpresa.objects.create(empresa=self.e,moneda=m,es_base=True);self.ctx=OperationContext(empresa=self.e,usuario=self.u,clave_idempotente="acct-hard");self.p=PlanCuenta.objects.create(empresa=self.e,codigo="P",nombre="Plan",creado_por=self.u);self.d=CuentaContable.objects.create(empresa=self.e,plan=self.p,codigo="1101",nombre="Débito",tipo="ACTIVO",naturaleza="DEBITO",creado_por=self.u);self.c=CuentaContable.objects.create(empresa=self.e,plan=self.p,codigo="4101",nombre="Crédito",tipo="INGRESO",naturaleza="CREDITO",creado_por=self.u);self.per=PeriodoContable.objects.create(empresa=self.e,anio=2026,mes=8,fecha_inicio=date(2026,8,1),fecha_fin=date(2026,8,31),creado_por=self.u);self.diario=DiarioContable.objects.create(empresa=self.e,codigo="GENERAL",nombre="General",creado_por=self.u)
 def lines(self,m=100):return [{"cuenta":self.d,"debito":m},{"cuenta":self.c,"credito":m}]
 def post(self,oid="1",concepto="Venta",lineas=None,**kw):return contabilizar(context=self.ctx,origen_tipo="TEST",origen_id=oid,concepto=concepto,lineas=lineas or self.lines(),fecha=date(2026,8,2),**kw)
 def test_01_asiento_balanceado_valido(self):self.assertEqual(self.post().total_debito,self.post().total_credito)
 def test_02_asiento_desbalanceado_rechazado(self):
  with self.assertRaises(ValidationError):self.post(lineas=[{"cuenta":self.d,"debito":10},{"cuenta":self.c,"credito":9}])
 def test_03_asiento_cero_rechazado(self):
  with self.assertRaises(ValidationError):self.post(lineas=[{"cuenta":self.d,"debito":0},{"cuenta":self.c,"credito":0}])
 def test_04_linea_doble_lado_rechazada(self):
  with self.assertRaises(ValidationError):self.post(lineas=[{"cuenta":self.d,"debito":10,"credito":10}])
 def test_05_doble_contabilizacion_impedida(self):self.assertEqual(self.post().pk,self.post().pk);self.assertEqual(AsientoContable.objects.count(),1)
 def test_06_reintento_mismo_payload_estable(self):self.assertEqual(self.post().numero,self.post().numero)
 def test_07_reintento_concepto_distinto_falla(self):
  self.post()
  with self.assertRaises(ValidationError):self.post(concepto="Distinto")
 def test_08_reintento_total_distinto_falla(self):
  self.post()
  with self.assertRaises(ValidationError):self.post(lineas=self.lines(101))
 def test_09_periodo_cerrado_bloquea(self):
  self.per.estado="CERRADO";self.per.save()
  with self.assertRaises(ValidationError):self.post()
 def test_10_periodo_inexistente_bloquea(self):
  self.per.delete()
  with self.assertRaises(ValidationError):self.post()
 def test_11_cuenta_faltante_bloquea(self):
  with self.assertRaises(CuentaContable.DoesNotExist):self.post(lineas=[{"cuenta":"9999","debito":10},{"cuenta":self.c,"credito":10}])
 def test_12_cuenta_inactiva_bloquea(self):
  self.d.activa=False;self.d.save()
  with self.assertRaises(ValidationError):self.post()
 def test_13_cuenta_control_bloquea(self):
  self.d.acepta_movimientos=False;self.d.save()
  with self.assertRaises(ValidationError):self.post()
 def test_14_diario_faltante_bloquea(self):
  self.diario.delete()
  with self.assertRaises(DiarioContable.DoesNotExist):self.post()
 def test_15_regla_faltante(self):
  class O:pk=1;empresa_id=None;numero="F";total=100
  O.empresa_id=self.e.pk
  with self.assertRaises(ValidationError):contabilizar_factura_venta(context=self.ctx,factura=O())
 def test_16_regla_ambigua(self):
  class O:pk=1;empresa_id=None;numero="F";total=100
  O.empresa_id=self.e.pk
  for _ in range(2):ReglaContabilizacion.objects.create(empresa=self.e,evento="FACTURA_VENTA",version=1,configuracion={"debito":"1101","credito":"4101"},creado_por=self.u)
  with self.assertRaises(ValidationError):contabilizar_factura_venta(context=self.ctx,factura=O())
 def test_17_origen_cross_tenant(self):
  other=Empresa.objects.create(usuario=User.objects.create_user("other-acct"),nombre="Otra")
  class O:pk=1;numero="F";total=100
  o=O();o.empresa_id=other.pk;ReglaContabilizacion.objects.create(empresa=self.e,evento="FACTURA_VENTA",configuracion={"debito":"1101","credito":"4101"},creado_por=self.u)
  with self.assertRaises(ValidationError):contabilizar_factura_venta(context=self.ctx,factura=o)
 def test_18_simulacion_sin_persistencia(self):self.assertIsInstance(self.post(simular=True),ResultadoContabilizacion);self.assertFalse(AsientoContable.objects.exists())
 def test_19_trazabilidad_origen(self):a=self.post(oid="DOC-9");self.assertEqual((a.origen_tipo,a.origen_id),("TEST","DOC-9"))
 def test_20_auditoria_creada(self):a=self.post();self.assertTrue(EventoAuditoria.objects.filter(empresa=self.e,object_id=a.pk).exists())
 def test_21_evento_normalizado(self):
  self.post();payload=EventoDominio.objects.filter(tipo_evento="AsientoContabilizado").get().payload
  for key in ("schema_version","empresa_id","aggregate_type","aggregate_id","actor_id","correlation_id","causation_id","timestamp"):self.assertIn(key,payload)
 def test_22_evento_unico(self):self.post();self.post();self.assertEqual(EventoDominio.objects.filter(tipo_evento="AsientoContabilizado").count(),1)
 def test_23_reversion_balanceada(self):r=revertir_asiento(context=self.ctx,asiento=self.post(),motivo="Error");self.assertEqual(r.total_debito,r.total_credito)
 def test_24_reversion_idempotente(self):a=self.post();self.assertEqual(revertir_asiento(context=self.ctx,asiento=a,motivo="Error").pk,revertir_asiento(context=self.ctx,asiento=a,motivo="Error").pk)
 def test_25_cierre_y_reapertura(self):a=self.post();cerrar_periodo(context=self.ctx,periodo=self.per,motivo="Mes");reabrir_periodo(context=self.ctx,periodo=self.per,motivo="Ajuste");self.per.refresh_from_db();self.assertEqual(self.per.estado,"ABIERTO")
