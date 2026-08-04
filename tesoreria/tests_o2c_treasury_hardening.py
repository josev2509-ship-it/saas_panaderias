from datetime import date
from decimal import Decimal
from io import BytesIO
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from openpyxl import Workbook
from catalogos.models import Moneda,MonedaEmpresa
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from core.models import EventoDominio
from auditoria.models import EventoAuditoria
from .api import registrar_ingreso,revertir_movimiento,posicion
from .models import CuentaBancariaEmpresa,Caja,MovimientoTesoreria,ImportacionExtractoBancario,LineaExtractoBancario,ConciliacionBancaria
from .services import importar_extracto,sugerir_coincidencias,conciliar_linea,desconciliar_linea,completar_conciliacion

class TreasuryHardeningTest(TestCase):
 def setUp(self):
  self.u=User.objects.create_superuser("tre-hard","t@example.invalid","x");self.e=Empresa.objects.create(usuario=self.u,nombre="Treasury Hardening");m=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$");self.me=MonedaEmpresa.objects.create(empresa=self.e,moneda=m,es_base=True);self.ctx=OperationContext(empresa=self.e,usuario=self.u,clave_idempotente="tre-hard");self.bank=CuentaBancariaEmpresa.objects.create(empresa=self.e,banco="Banco",numero_enmascarado="****1234",moneda=self.me);self.cash=Caja.objects.create(empresa=self.e,codigo="C1",nombre="Caja",moneda=self.me)
 def ingreso(self,oid="1",monto=100,**kw):return registrar_ingreso(context=self.ctx,origen_tipo="COBRO_O2C",origen_id=oid,fecha=date(2026,8,3),monto=monto,referencia=f"R-{oid}",cuenta_id=kw.get("cuenta_id",self.bank.pk),caja_id=kw.get("caja_id"))
 def csv(self,ref="R-1",amount="100"):return f"fecha,descripcion,referencia,debito,credito,saldo\n2026-08-03,Cobro,{ref},0,{amount},{amount}\n"
 def imported(self,ref="R-1",amount="100"):return importar_extracto(context=self.ctx,cuenta=self.bank,contenido=self.csv(ref,amount),nombre_archivo=f"{ref}.csv",confirmar=True)
 def test_01_movimiento_ingreso_valido(self):r=self.ingreso();self.assertEqual((r.tipo,r.monto),("INGRESO","100"))
 def test_02_movimiento_duplicado_idempotente(self):self.assertEqual(self.ingreso().id,self.ingreso().id);self.assertEqual(MovimientoTesoreria.objects.count(),1)
 def test_03_movimiento_cross_tenant(self):
  o=Empresa.objects.create(usuario=User.objects.create_user("tre-other"),nombre="Otra");b=CuentaBancariaEmpresa.objects.create(empresa=o,banco="X",numero_enmascarado="****9",moneda=MonedaEmpresa.objects.create(empresa=o,moneda=self.me.moneda,es_base=True))
  with self.assertRaises(CuentaBancariaEmpresa.DoesNotExist):self.ingreso(cuenta_id=b.pk)
 def test_04_caja_inexistente(self):
  with self.assertRaises(Caja.DoesNotExist):self.ingreso(cuenta_id=None,caja_id=99999)
 def test_05_banco_inexistente(self):
  with self.assertRaises(CuentaBancariaEmpresa.DoesNotExist):self.ingreso(cuenta_id=99999)
 def test_06_banco_inactivo(self):
  self.bank.activa=False;self.bank.save()
  with self.assertRaises(CuentaBancariaEmpresa.DoesNotExist):self.ingreso()
 def test_07_cobro_efectivo_en_caja(self):r=self.ingreso(cuenta_id=None,caja_id=self.cash.pk);self.cash.refresh_from_db();self.assertEqual((r.caja_id,self.cash.saldo),(self.cash.pk,100))
 def test_08_transferencia_incrementa_banco(self):self.ingreso();self.bank.refresh_from_db();self.assertEqual(self.bank.saldo,100)
 def test_09_destino_doble_rechazado(self):
  with self.assertRaises(ValidationError):self.ingreso(caja_id=self.cash.pk)
 def test_10_monto_no_positivo_rechazado(self):
  with self.assertRaises(ValidationError):self.ingreso(monto=0)
 def test_11_reversion_no_conciliada(self):self.ingreso();r=revertir_movimiento(context=self.ctx,origen_tipo="COBRO_O2C",origen_id="1",motivo="Error");self.assertEqual(r.tipo,"EGRESO")
 def test_12_reversion_duplicada_idempotente(self):self.ingreso();a=revertir_movimiento(context=self.ctx,origen_tipo="COBRO_O2C",origen_id="1",motivo="Error");b=revertir_movimiento(context=self.ctx,origen_tipo="COBRO_O2C",origen_id="1",motivo="Error");self.assertEqual(a.id,b.id)
 def test_13_importacion_csv_valida(self):self.assertEqual(self.imported().lineas.count(),1)
 def test_14_importacion_xlsx_valida(self):
  wb=Workbook();ws=wb.active;ws.append(["fecha","descripcion","referencia","debito","credito","saldo"]);ws.append([date(2026,8,3),"Cobro","X-1",0,125,125]);out=BytesIO();wb.save(out);imp=importar_extracto(context=self.ctx,cuenta=self.bank,contenido=out.getvalue(),nombre_archivo="x.xlsx",confirmar=True);self.assertEqual(imp.lineas.get().monto,125)
 def test_15_archivo_duplicado_idempotente(self):a=self.imported();b=self.imported();self.assertEqual(a.pk,b.pk);self.assertEqual(ImportacionExtractoBancario.objects.count(),1)
 def test_16_fila_duplicada_rechazada(self):
  data=self.csv()+self.csv().split("\n",1)[1]
  with self.assertRaises(IntegrityError):importar_extracto(context=self.ctx,cuenta=self.bank,contenido=data,nombre_archivo="dup.csv",confirmar=True)
 def test_17_matching_por_referencia(self):self.ingreso();s=sugerir_coincidencias(context=self.ctx,importacion=self.imported(ref="COBRO_O2C:1"))[0];self.assertEqual(s["tipo"],"REFERENCIA")
 def test_18_matching_por_monto_fecha(self):self.ingreso();s=sugerir_coincidencias(context=self.ctx,importacion=self.imported(ref="OTRA"))[0];self.assertEqual(s["movimiento_id"],self.ingreso().id)
 def test_19_conciliar_y_desconciliar(self):
  mov=self.ingreso();imp=self.imported();line=imp.lineas.get();con=ConciliacionBancaria.objects.create(empresa=self.e,cuenta=self.bank,desde=date(2026,8,1),hasta=date(2026,8,31),saldo_banco=100,saldo_libros=100);conciliar_linea(context=self.ctx,conciliacion=con,linea_id=line.pk,movimiento_id=mov.id);desconciliar_linea(context=self.ctx,linea_id=line.pk,motivo="Revisión");line.refresh_from_db();self.assertEqual(line.estado,"PENDIENTE")
 def test_20_cierre_evento_y_auditoria(self):
  con=ConciliacionBancaria.objects.create(empresa=self.e,cuenta=self.bank,desde=date(2026,8,1),hasta=date(2026,8,31),saldo_banco=0,saldo_libros=0);completar_conciliacion(context=self.ctx,conciliacion=con);self.assertTrue(EventoDominio.objects.filter(tipo_evento="ConciliacionCompletada").exists());self.assertTrue(EventoAuditoria.objects.filter(object_id=con.pk).exists());self.assertEqual(posicion(empresa=self.e)[0]["cuenta"],"****1234")
