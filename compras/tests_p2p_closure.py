from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client,TestCase
from django.urls import reverse
from django.utils import timezone

from catalogos.models import Moneda,MonedaEmpresa
from conduces.models import Empresa
from contabilidad.models import (AplicacionAnticipoProveedor,AplicacionNotaProveedor,AnticipoProveedor,
 CuentaContable,CuentaPorPagarEnterprise,DiarioContable,FacturaProveedor,NotaCreditoProveedor,
 PeriodoContable,PlanCuenta,ReglaContabilizacion)
from core.application.operation_context import OperationContext
from compras.application.financial import (anular_anticipo,anular_nota,aplicar_anticipo,aplicar_nota,
 crear_anticipo_borrador,crear_nota_borrador,decidir_anticipo,decidir_nota,enviar_nota_aprobacion,
 revertir_aplicacion_anticipo,revertir_aplicacion_nota)
from compras.models import Proveedor


class P2PClosureMatrixTests(TestCase):
 def setUp(self):
  U=get_user_model();self.user=U.objects.create_user("p2p-closure",password="x");self.empresa=Empresa.objects.create(usuario=self.user,nombre="P2P closure",modulo_compras=True);self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label__in=["compras","contabilidad","tesoreria"]));self.ctx=OperationContext(empresa=self.empresa,usuario=self.user,clave_idempotente="closure")
  moneda=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$");self.moneda=MonedaEmpresa.objects.create(empresa=self.empresa,moneda=moneda,es_base=True);self.proveedor=Proveedor.objects.create(empresa=self.empresa,codigo="P-CLOSE",tipo_persona="JURIDICA",razon_social="Proveedor",estado="ACTIVO",creado_por=self.user)
  plan=PlanCuenta.objects.create(empresa=self.empresa,codigo="CLOSE",nombre="Plan",creado_por=self.user);debit=CuentaContable.objects.create(empresa=self.empresa,plan=plan,codigo="1101",nombre="Activo",tipo="ACTIVO",naturaleza="DEBITO",creado_por=self.user);credit=CuentaContable.objects.create(empresa=self.empresa,plan=plan,codigo="2101",nombre="Pasivo",tipo="PASIVO",naturaleza="CREDITO",creado_por=self.user);today=timezone.localdate();PeriodoContable.objects.create(empresa=self.empresa,anio=today.year,mes=today.month,fecha_inicio=today.replace(day=1),fecha_fin=(today.replace(day=28)+timedelta(days=4)).replace(day=1)-timedelta(days=1),creado_por=self.user);DiarioContable.objects.create(empresa=self.empresa,codigo="GENERAL",nombre="General",creado_por=self.user)
  for event in ["APLICACION_NOTA_CREDITO","APLICACION_NOTA_DEBITO","ANTICIPO_PROVEEDOR"]:ReglaContabilizacion.objects.create(empresa=self.empresa,evento=event,configuracion={"debito":debit.codigo,"credito":credit.codigo},creado_por=self.user)
 def account(self,total=200):
  today=timezone.localdate();invoice=FacturaProveedor.objects.create(empresa=self.empresa,proveedor=self.proveedor,numero=f"FAC-{FacturaProveedor.objects.count()+1}",fecha=today,vence_el=today+timedelta(days=30),moneda=self.moneda,subtotal=total,total=total,estado="VALIDADA",creado_por=self.user);return CuentaPorPagarEnterprise.objects.create(empresa=self.empresa,factura=invoice,proveedor=self.proveedor,moneda=self.moneda,monto_original=total,saldo=total,vence_el=invoice.vence_el,creado_por=self.user),invoice
 def test_matriz_notas_y_anticipos(self):
  account,invoice=self.account();other,_=self.account(100);credit=crear_nota_borrador(context=self.ctx,tipo="CREDITO",factura_id=invoice.pk,numero="NC-MAT",monto=100,motivo="Matriz");self.assertEqual(account.saldo,200);enviar_nota_aprobacion(context=self.ctx,tipo="CREDITO",nota_id=credit.pk);decidir_nota(context=self.ctx,tipo="CREDITO",nota_id=credit.pk,decision="APROBAR");app1=aplicar_nota(context=self.ctx,tipo="CREDITO",nota_id=credit.pk,cuenta_id=account.pk,monto=40,clave_idempotencia="nc-1",tasa_cambio="1");app2=aplicar_nota(context=self.ctx,tipo="CREDITO",nota_id=credit.pk,cuenta_id=other.pk,monto=60,clave_idempotencia="nc-2");revertir_aplicacion_nota(context=self.ctx,aplicacion_id=app2.pk,motivo="UAT");self.assertEqual(app1.diferencia_cambiaria,Decimal("0.00"))
  rejected=crear_nota_borrador(context=self.ctx,tipo="CREDITO",factura_id=invoice.pk,numero="NC-REJ",monto=5,motivo="Rechazo");enviar_nota_aprobacion(context=self.ctx,tipo="CREDITO",nota_id=rejected.pk);decidir_nota(context=self.ctx,tipo="CREDITO",nota_id=rejected.pk,decision="RECHAZAR",motivo="No procede");anular_nota(context=self.ctx,tipo="CREDITO",nota_id=rejected.pk,motivo="Cerrar")
  advance=crear_anticipo_borrador(context=self.ctx,proveedor=self.proveedor,moneda=self.moneda,monto=80,referencia="ANT-MAT");decidir_anticipo(context=self.ctx,anticipo_id=advance.pk,decision="APROBAR");aplicar_anticipo(context=self.ctx,anticipo_id=advance.pk,cuenta_id=account.pk,monto=30,clave_idempotencia="ant-1",tasa_cambio="1.20");aplicar_anticipo(context=self.ctx,anticipo_id=advance.pk,cuenta_id=other.pk,monto=50,clave_idempotencia="ant-2");revertir_aplicacion_anticipo(context=self.ctx,aplicacion_id=AplicacionAnticipoProveedor.objects.get(clave_idempotencia="ant-2").pk,motivo="UAT");rejected_advance=crear_anticipo_borrador(context=self.ctx,proveedor=self.proveedor,moneda=self.moneda,monto=10,referencia="ANT-REJ");decidir_anticipo(context=self.ctx,anticipo_id=rejected_advance.pk,decision="RECHAZAR",motivo="No");anular_anticipo(context=self.ctx,anticipo_id=rejected_advance.pk,motivo="Cerrar");self.assertTrue(AplicacionNotaProveedor.objects.filter(nota_credito=credit).exists())
 def test_http_csrf_get_idor_y_tenant(self):
  account,invoice=self.account(100);client=Client(enforce_csrf_checks=True);client.force_login(self.user);action=reverse("compras:p2p_finance_nota_accion",args=["credito",999,"enviar"]);self.assertEqual(client.get(action).status_code,405);self.assertEqual(client.post(action).status_code,403);response=client.get(reverse("compras:p2p_finance_nota_crear"));self.assertEqual(response.status_code,200);token=client.cookies["csrftoken"].value;response=client.post(reverse("compras:p2p_finance_nota_crear"),{"tipo":"CREDITO","factura":invoice.pk,"numero":"NC-WEB","monto":"10","motivo":"Web"},HTTP_X_CSRFTOKEN=token);self.assertEqual(response.status_code,302);note=NotaCreditoProveedor.objects.get(numero="NC-WEB");self.assertEqual(client.post(reverse("compras:p2p_finance_nota_accion",args=["credito",note.pk,"enviar"]),HTTP_X_CSRFTOKEN=token).status_code,302)
  other_user=get_user_model().objects.create_user("finance-other");other=Empresa.objects.create(usuario=other_user,nombre="Other",modulo_compras=True);foreign_provider=Proveedor.objects.create(empresa=other,codigo="OTHER",tipo_persona="JURIDICA",razon_social="Otro",creado_por=other_user);foreign=AnticipoProveedor.objects.create(empresa=other,proveedor=foreign_provider,moneda=self.moneda,monto=10,saldo=10);self.assertEqual(client.get(reverse("compras:p2p_finance_detail",args=["anticipos",foreign.pk])).status_code,404);self.assertFalse(AplicacionNotaProveedor.objects.filter(cuenta=account).exists())
 def test_http_security_matrix_all_mutating_endpoints(self):
  urls=[reverse("compras:p2p_finance_nota_accion",args=["credito",999,"enviar"]),reverse("compras:p2p_finance_anticipo_accion",args=[999,"aprobar"]),reverse("compras:p2p_finance_retencion_accion",args=[999,"aprobar"]),reverse("compras:p2p_compensacion_accion",args=[999,"aprobar"]),reverse("compras:p2p_finance_matching_accion",args=[999,"desconciliar"])]
  csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.user)
  for url in urls:
   self.assertEqual(csrf.get(url).status_code,405);self.assertEqual(csrf.post(url).status_code,403);csrf.cookies["csrftoken"]="a"*32;self.assertEqual(csrf.post(url,HTTP_X_CSRFTOKEN="b"*32).status_code,403)
  anonymous=Client(enforce_csrf_checks=True)
  for url in urls:self.assertEqual(anonymous.get(url).status_code,302)
  no_permission=get_user_model().objects.create_user("no-finance",password="x");Empresa.objects.create(usuario=no_permission,nombre="No permission",modulo_compras=True);limited=Client(enforce_csrf_checks=True);limited.force_login(no_permission);limited.cookies["csrftoken"]="a"*32
  for url in urls:self.assertEqual(limited.post(url,HTTP_X_CSRFTOKEN="a"*32).status_code,403)
 def test_ui_acciones_contextuales_por_estado(self):
  _,invoice=self.account(100);note=crear_nota_borrador(context=self.ctx,tipo="CREDITO",factura_id=invoice.pk,numero="NC-UI",monto=10,motivo="UI");self.client.force_login(self.user);url=reverse("compras:p2p_finance_detail",args=["notas-credito",note.pk]);response=self.client.get(url);self.assertContains(response,"Enviar");self.assertNotContains(response,">Aprobar<");enviar_nota_aprobacion(context=self.ctx,tipo="CREDITO",nota_id=note.pk);response=self.client.get(url);self.assertContains(response,">Aprobar<",html=False);self.assertContains(response,"Rechazar");self.assertNotContains(response,">Aplicar<")
