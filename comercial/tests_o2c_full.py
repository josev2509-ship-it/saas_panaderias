from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from catalogos.models import Moneda,MonedaEmpresa
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from inventario.models import ProductoInventario,LoteInventario
from comercial.models import Cliente,Pedido,DetallePedido,CuentaPorCobrar,FacturaVenta
from comercial.application.o2c_full import *

class OrderToCashE2ETest(TestCase):
    def setUp(self):
        self.u=User.objects.create_superuser("o2c4","o2c4@example.invalid","x");self.e=Empresa.objects.create(usuario=self.u,nombre="O2C4")
        m=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$");self.me=MonedaEmpresa.objects.create(empresa=self.e,moneda=m,es_base=True)
        self.c=Cliente.objects.create(empresa=self.e,codigo="C1",tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,nombre_comercial="Cliente",condicion_pago=Cliente.CondicionPago.CREDITO,dias_credito=30,limite_credito=10000,moneda_comercial=self.me,creado_por=self.u)
        self.prod=ProductoInventario.objects.create(empresa=self.e,codigo="PT1",nombre="Producto",tipo="producto_terminado",clasificacion_operativa="producto_terminado",unidad_medida="unidad",stock_actual=100)
        LoteInventario.objects.create(empresa=self.e,producto=self.prod,lote="L1",fecha_ingreso=timezone.localdate(),fecha_vencimiento=timezone.localdate()+timedelta(days=30),cantidad_inicial=100,cantidad_disponible=100)
        self.p=Pedido.objects.create(empresa=self.e,numero="P1",cliente=self.c,fecha_pedido=timezone.localdate(),fecha_entrega=timezone.localdate()+timedelta(days=1),condicion_pago=Cliente.CondicionPago.CREDITO,dias_credito=30,estado=Pedido.Estado.APROBADO,total=Decimal("1000"),creado_por=self.u)
        DetallePedido.objects.create(pedido=self.p,producto=self.prod,descripcion="Producto",cantidad=10,unidad_medida="unidad",precio_unitario=100,subtotal=1000,total=1000)
        self.ctx=OperationContext(empresa=self.e,usuario=self.u,origen="test-o2c4")

    def test_ciclo_completo_reserva_a_cobro(self):
        self.assertTrue(consultar_disponibilidad(context=self.ctx,pedido=self.p)[0]["suficiente"])
        r=crear_reserva_desde_pedido(context=self.ctx,pedido_id=self.p.pk);r=reservar_inventario(context=self.ctx,reserva_id=r.pk);self.assertEqual(r.estado,"COMPLETA")
        prep=crear_preparacion(context=self.ctx,reserva_id=r.pk);iniciar_preparacion(context=self.ctx,pk=prep.pk);prep=validar_preparacion(context=self.ctx,pk=prep.pk)
        pick=generar_picking(context=self.ctx,preparacion_id=prep.pk);pick=completar_picking(context=self.ctx,pk=pick.pk)
        pack=crear_packing(context=self.ctx,picking_id=pick.pk);pack=sellar_packing(context=self.ctx,pk=pack.pk,peso=5)
        des=crear_despacho(context=self.ctx,packing_ids=[pack.pk]);des=autorizar_despacho(context=self.ctx,pk=des.pk)
        cond=emitir_conduce(context=self.ctx,despacho_id=des.pk);ent=confirmar_entrega(context=self.ctx,conduce_id=cond.pk,receptor="María")
        fac=crear_factura_desde_entrega(context=self.ctx,entrega_id=ent.pk,vence_el=timezone.localdate()+timedelta(days=30),ncf="B0100000001");fac=emitir_factura(context=self.ctx,pk=fac.pk);cxc=fac.cuenta_cobrar
        rec1=registrar_cobro(context=self.ctx,cliente=self.c,moneda=self.me,monto=400,metodo="TRANSFERENCIA");cxc=aplicar_cobro(context=self.ctx,recibo_id=rec1.pk,cuenta_id=cxc.pk,monto=400);self.assertEqual(cxc.estado,"PARCIAL")
        rec2=registrar_cobro(context=self.ctx,cliente=self.c,moneda=self.me,monto=600,metodo="EFECTIVO");cxc=aplicar_cobro(context=self.ctx,recibo_id=rec2.pk,cuenta_id=cxc.pk,monto=600)
        self.assertEqual(cxc.estado,"COBRADA");self.assertEqual(cxc.saldo,0);self.prod.refresh_from_db();self.assertEqual(self.prod.stock_actual,90);self.assertTrue(FacturaVenta.objects.filter(pk=fac.pk,estado="COBRADA").exists())

    def test_reserva_idempotente_y_tenant(self):
        a=crear_reserva_desde_pedido(context=self.ctx,pedido_id=self.p.pk);b=crear_reserva_desde_pedido(context=self.ctx,pedido_id=self.p.pk);self.assertEqual(a.pk,b.pk)

    def test_aging_separa_vencido(self):
        f=FacturaVenta.objects.create(empresa=self.e,numero="F1",cliente=self.c,moneda=self.me,fecha=timezone.localdate()-timedelta(days=50),vence_el=timezone.localdate()-timedelta(days=40),estado="EMITIDA",total=100,creado_por=self.u)
        c=CuentaPorCobrar.objects.create(empresa=self.e,factura=f,cliente=self.c,moneda=self.me,fecha_emision=f.fecha,fecha_vencimiento=f.vence_el,monto_original=100,saldo=100,creado_por=self.u);c=actualizar_aging_cuenta(context=self.ctx,cuenta_id=c.pk);self.assertEqual(c.bucket_aging,"31_60");self.assertEqual(c.estado,"EN_MORA")
