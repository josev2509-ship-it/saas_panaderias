from datetime import date
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied,ValidationError
from django.test import TestCase
from catalogos.models import Moneda,MonedaEmpresa
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from core.domain.exceptions import BusinessRuleViolation,UnsafePayloadError
from core.domain.rules import normalize_idempotency_key,validate_safe_payload
from contabilidad.models import PlanCuenta,CuentaContable,PeriodoContable,DiarioContable,ReglaContabilizacion
from contabilidad.api import contabilizar
from tesoreria.models import CuentaBancariaEmpresa,ConciliacionBancaria
from tesoreria.api import registrar_ingreso,posicion
from tesoreria.services import completar_conciliacion
from documentos.services import resolver_objeto_permitido
from comercial.models import Cliente,FacturaVenta,CuentaPorCobrar,ReciboCobro
from comercial.application.financial_integration import contabilizar_factura_emitida,integrar_cobro,revertir_cobro_integral
from comercial.application.o2c_full import solicitar_factoring
from comercial.application.financial_exports import exportar

class O2CSecurityHardeningTest(TestCase):
 def setUp(self):
  self.owner=User.objects.create_superuser("sec-owner","s@example.invalid","x");self.limited=User.objects.create_user("sec-limited",password="x");self.other_user=User.objects.create_superuser("sec-other","x@example.invalid","x");self.e=Empresa.objects.create(usuario=self.owner,nombre="Secure");self.other=Empresa.objects.create(usuario=self.other_user,nombre="Other");m=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$");self.me=MonedaEmpresa.objects.create(empresa=self.e,moneda=m,es_base=True);self.ome=MonedaEmpresa.objects.create(empresa=self.other,moneda=m,es_base=True);self.ctx=OperationContext(empresa=self.e,usuario=self.owner,clave_idempotente="security");self.client=Cliente.objects.create(empresa=self.e,codigo="C1",tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,nombre_comercial="Cliente",condicion_pago=Cliente.CondicionPago.CREDITO,moneda_comercial=self.me,creado_por=self.owner);self.oclient=Cliente.objects.create(empresa=self.other,codigo="C2",tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,nombre_comercial="Otro",condicion_pago=Cliente.CondicionPago.CREDITO,moneda_comercial=self.ome,creado_por=self.other_user);self.bank=CuentaBancariaEmpresa.objects.create(empresa=self.e,banco="Banco",numero_enmascarado="****1234",moneda=self.me);self.obank=CuentaBancariaEmpresa.objects.create(empresa=self.other,banco="Otro",numero_enmascarado="****9999",moneda=self.ome);p=PlanCuenta.objects.create(empresa=self.e,codigo="P",nombre="P",creado_por=self.owner);self.d=CuentaContable.objects.create(empresa=self.e,plan=p,codigo="1101",nombre="D",tipo="ACTIVO",naturaleza="DEBITO",creado_por=self.owner);self.c=CuentaContable.objects.create(empresa=self.e,plan=p,codigo="4101",nombre="C",tipo="INGRESO",naturaleza="CREDITO",creado_por=self.owner);PeriodoContable.objects.create(empresa=self.e,anio=2026,mes=8,fecha_inicio=date(2026,8,1),fecha_fin=date(2026,8,31),creado_por=self.owner);DiarioContable.objects.create(empresa=self.e,codigo="GENERAL",nombre="G",creado_por=self.owner);ReglaContabilizacion.objects.create(empresa=self.e,evento="FACTURA_VENTA",configuracion={"debito":"1101","credito":"4101"},creado_por=self.owner)
 def factura(self,empresa=None,cliente=None,moneda=None,num="F"):
  empresa=empresa or self.e;cliente=cliente or self.client;moneda=moneda or self.me;f=FacturaVenta.objects.create(empresa=empresa,numero=num,cliente=cliente,moneda=moneda,fecha=date(2026,8,3),vence_el=date(2026,9,3),estado="EMITIDA",total=100,creado_por=empresa.usuario);CuentaPorCobrar.objects.create(empresa=empresa,factura=f,cliente=cliente,moneda=moneda,fecha_emision=f.fecha,fecha_vencimiento=f.vence_el,monto_original=100,saldo=100,creado_por=empresa.usuario);return f
 def test_01_cross_tenant_factura(self):
  with self.assertRaises(FacturaVenta.DoesNotExist):contabilizar_factura_emitida(context=self.ctx,factura_id=self.factura(self.other,self.oclient,self.ome,"OF").pk)
 def test_02_cross_tenant_cobro(self):
  r=ReciboCobro.objects.create(empresa=self.other,numero="OR",cliente=self.oclient,moneda=self.ome,fecha=date(2026,8,3),metodo="TRANSFERENCIA",monto=10,monto_aplicado=10,estado="APLICADO",creado_por=self.other_user)
  with self.assertRaises(ReciboCobro.DoesNotExist):integrar_cobro(context=self.ctx,recibo_id=r.pk,cuenta_bancaria_id=self.bank.pk)
 def test_03_cross_tenant_tesoreria(self):
  with self.assertRaises(CuentaBancariaEmpresa.DoesNotExist):registrar_ingreso(context=self.ctx,origen_tipo="X",origen_id=1,fecha=date(2026,8,3),monto=1,referencia="X",cuenta_id=self.obank.pk)
 def test_04_cross_tenant_conciliacion(self):
  con=ConciliacionBancaria.objects.create(empresa=self.other,cuenta=self.obank,desde=date(2026,8,1),hasta=date(2026,8,31),saldo_banco=0,saldo_libros=0)
  with self.assertRaises(ConciliacionBancaria.DoesNotExist):completar_conciliacion(context=self.ctx,conciliacion=con)
 def test_05_cross_tenant_factoring(self):
  with self.assertRaises(CuentaPorCobrar.DoesNotExist):solicitar_factoring(context=self.ctx,cuenta_id=self.factura(self.other,self.oclient,self.ome,"OF2").cuenta_cobrar.pk,factor="X",porcentaje=80)
 def test_06_idor_factura_inexistente(self):
  with self.assertRaises(FacturaVenta.DoesNotExist):contabilizar_factura_emitida(context=self.ctx,factura_id=999999)
 def test_07_idor_documento(self):
  f=self.factura(self.other,self.oclient,self.ome,"OF3")
  with self.assertRaises(ValidationError):resolver_objeto_permitido(empresa=self.e,app_label="comercial",model="facturaventa",object_id=f.pk)
 def test_08_exportacion_tenant_safe(self):self.factura();self.factura(self.other,self.oclient,self.ome,"OF4");data=exportar(context=self.ctx,tipo="facturas",formato="csv").contenido.decode("utf-8-sig");self.assertIn("F",data);self.assertNotIn("OF4",data)
 def test_09_contabilizar_sin_permiso(self):
  ctx=OperationContext(empresa=self.e,usuario=self.limited)
  with self.assertRaises(PermissionDenied):contabilizar(context=ctx,origen_tipo="X",origen_id=1,concepto="X",lineas=[{"cuenta":self.d,"debito":1},{"cuenta":self.c,"credito":1}],fecha=date(2026,8,3))
 def test_10_reversion_sin_permiso(self):
  r=ReciboCobro.objects.create(empresa=self.e,numero="R",cliente=self.client,moneda=self.me,fecha=date(2026,8,3),metodo="TRANSFERENCIA",monto=10,estado="APLICADO",creado_por=self.owner)
  with self.assertRaises(ValidationError):revertir_cobro_integral(context=OperationContext(empresa=self.e,usuario=self.limited),recibo_id=r.pk,motivo="X")
 def test_11_factoring_sin_permiso(self):
  with self.assertRaises(PermissionDenied):solicitar_factoring(context=OperationContext(empresa=self.e,usuario=self.limited),cuenta_id=self.factura().cuenta_cobrar.pk,factor="X",porcentaje=80)
 def test_12_exportacion_sin_permiso(self):
  with self.assertRaises(PermissionDenied):exportar(context=OperationContext(empresa=self.e,usuario=self.limited),tipo="facturas",formato="csv")
 def test_13_numero_bancario_enmascarado(self):self.assertEqual(posicion(empresa=self.e)[0]["cuenta"],"****1234");self.assertNotIn("123456789",str(posicion(empresa=self.e)))
 def test_14_payload_sensible_rechazado(self):
  for key in ("password","token","secret","authorization"):
   with self.assertRaises(UnsafePayloadError):validate_safe_payload({key:"x"})
 def test_15_idempotency_maliciosa_rechazada(self):
  for key in ("../escape","x\r\ninject","<script>"):
   with self.assertRaises(BusinessRuleViolation):normalize_idempotency_key(key)
