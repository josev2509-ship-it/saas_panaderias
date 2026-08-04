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
from comercial.application.financial_integration import contabilizar_factura_emitida,integrar_cobro,emitir_nota_credito_integrada,emitir_nota_debito_integrada,desembolsar_factoring,revertir_cobro_integral
from comercial.application.financial_exports import exportar
from contabilidad.models import PlanCuenta,CuentaContable,PeriodoContable,DiarioContable,ReglaContabilizacion,AsientoContable
from tesoreria.models import CuentaBancariaEmpresa,ConciliacionBancaria
from tesoreria.services import importar_extracto,sugerir_coincidencias,conciliar_linea,completar_conciliacion
from comercial.api.finanzas import dashboard,estados

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
        plan=PlanCuenta.objects.create(empresa=self.e,codigo="O2C",nombre="O2C",creado_por=self.u)
        for codigo,nombre,tipo,naturaleza in (("1102","Banco","ACTIVO","DEBITO"),("1201","CxC","ACTIVO","DEBITO"),("1301","Retención","ACTIVO","DEBITO"),("4101","Ingresos","INGRESO","CREDITO"),("6101","Gasto financiero","GASTO","DEBITO")):
            CuentaContable.objects.create(empresa=self.e,plan=plan,codigo=codigo,nombre=nombre,tipo=tipo,naturaleza=naturaleza,creado_por=self.u)
        hoy=timezone.localdate();PeriodoContable.objects.create(empresa=self.e,anio=hoy.year,mes=hoy.month,fecha_inicio=hoy.replace(day=1),fecha_fin=hoy+timedelta(days=31),creado_por=self.u)
        DiarioContable.objects.create(empresa=self.e,codigo="GENERAL",nombre="General",creado_por=self.u)
        ReglaContabilizacion.objects.create(empresa=self.e,evento="FACTURA_VENTA",configuracion={"debito":"1201","credito":"4101"},creado_por=self.u)
        ReglaContabilizacion.objects.create(empresa=self.e,evento="COBRO",configuracion={"debito":"1102","credito":"1201"},creado_por=self.u)
        ReglaContabilizacion.objects.create(empresa=self.e,evento="NOTA_CREDITO_VENTA",configuracion={"debito":"4101","credito":"1201"},creado_por=self.u)
        ReglaContabilizacion.objects.create(empresa=self.e,evento="NOTA_DEBITO_VENTA",configuracion={"debito":"1201","credito":"4101"},creado_por=self.u)
        ReglaContabilizacion.objects.create(empresa=self.e,evento="FACTORING",configuracion={"banco":"1102","gasto":"6101","retencion":"1301","cxc":"1201"},creado_por=self.u)
        self.banco=CuentaBancariaEmpresa.objects.create(empresa=self.e,banco="Banco O2C",numero_enmascarado="****0001",moneda=self.me)

    def test_ciclo_completo_reserva_a_cobro(self):
        self.assertTrue(consultar_disponibilidad(context=self.ctx,pedido=self.p)[0]["suficiente"])
        r=crear_reserva_desde_pedido(context=self.ctx,pedido_id=self.p.pk);r=reservar_inventario(context=self.ctx,reserva_id=r.pk);self.assertEqual(r.estado,"COMPLETA")
        prep=crear_preparacion(context=self.ctx,reserva_id=r.pk);iniciar_preparacion(context=self.ctx,pk=prep.pk);prep=validar_preparacion(context=self.ctx,pk=prep.pk)
        pick=generar_picking(context=self.ctx,preparacion_id=prep.pk);pick=completar_picking(context=self.ctx,pk=pick.pk)
        pack=crear_packing(context=self.ctx,picking_id=pick.pk);pack=sellar_packing(context=self.ctx,pk=pack.pk,peso=5)
        des=crear_despacho(context=self.ctx,packing_ids=[pack.pk]);des=autorizar_despacho(context=self.ctx,pk=des.pk)
        cond=emitir_conduce(context=self.ctx,despacho_id=des.pk);ent=confirmar_entrega(context=self.ctx,conduce_id=cond.pk,receptor="María")
        fac=crear_factura_desde_entrega(context=self.ctx,entrega_id=ent.pk,vence_el=timezone.localdate()+timedelta(days=30),ncf="B0100000001");fac=emitir_factura(context=self.ctx,pk=fac.pk);cxc=fac.cuenta_cobrar
        af=contabilizar_factura_emitida(context=self.ctx,factura_id=fac.pk);self.assertEqual(af.total,"1000.00")
        self.assertEqual(af.asiento_id,contabilizar_factura_emitida(context=self.ctx,factura_id=fac.pk).asiento_id)
        emitir_nota_credito_integrada(context=self.ctx,factura_id=fac.pk,monto=100,motivo="Descuento posterior")
        emitir_nota_debito_integrada(context=self.ctx,factura_id=fac.pk,monto=50,motivo="Recargo")
        rec1=registrar_cobro(context=self.ctx,cliente=self.c,moneda=self.me,monto=400,metodo="TRANSFERENCIA",referencia="TR-400");cxc=aplicar_cobro(context=self.ctx,recibo_id=rec1.pk,cuenta_id=cxc.pk,monto=400);integrar_cobro(context=self.ctx,recibo_id=rec1.pk,cuenta_bancaria_id=self.banco.pk);self.assertEqual(cxc.estado,"PARCIAL")
        rec2=registrar_cobro(context=self.ctx,cliente=self.c,moneda=self.me,monto=550,metodo="TRANSFERENCIA",referencia="TR-550");cxc=aplicar_cobro(context=self.ctx,recibo_id=rec2.pk,cuenta_id=cxc.pk,monto=550);integrar_cobro(context=self.ctx,recibo_id=rec2.pk,cuenta_bancaria_id=self.banco.pk)
        self.assertEqual(cxc.estado,"COBRADA");self.assertEqual(cxc.saldo,0);self.prod.refresh_from_db();self.assertEqual(self.prod.stock_actual,90);self.assertTrue(FacturaVenta.objects.filter(pk=fac.pk,estado="COBRADA").exists())
        csv=f"fecha,descripcion,referencia,debito,credito,saldo\n{timezone.localdate()},Cobro 1,TR-400,0,400,400\n{timezone.localdate()},Cobro 2,TR-550,0,550,950\n"
        imp=importar_extracto(context=self.ctx,cuenta=self.banco,contenido=csv,nombre_archivo="o2c.csv",confirmar=True);sugerencias=sugerir_coincidencias(context=self.ctx,importacion=imp)
        con=ConciliacionBancaria.objects.create(empresa=self.e,cuenta=self.banco,desde=timezone.localdate(),hasta=timezone.localdate(),saldo_banco=950,saldo_libros=950)
        for s in sugerencias:conciliar_linea(context=self.ctx,conciliacion=con,linea_id=s["linea_id"],movimiento_id=s["movimiento_id"],tipo=s["tipo"])
        completar_conciliacion(context=self.ctx,conciliacion=con);self.assertEqual(AsientoContable.objects.filter(empresa=self.e).count(),5)
        reportes=estados(empresa=self.e);self.assertEqual(len(reportes["diario"]),5);self.assertEqual(reportes["resultados"]["resultado"],"950")
        tablero=dashboard(empresa=self.e);self.assertEqual(tablero["pendiente"],"0");self.assertEqual(tablero["movimientos_sin_conciliar"],0)

    def test_reserva_idempotente_y_tenant(self):
        a=crear_reserva_desde_pedido(context=self.ctx,pedido_id=self.p.pk);b=crear_reserva_desde_pedido(context=self.ctx,pedido_id=self.p.pk);self.assertEqual(a.pk,b.pk)

    def test_aging_separa_vencido(self):
        f=FacturaVenta.objects.create(empresa=self.e,numero="F1",cliente=self.c,moneda=self.me,fecha=timezone.localdate()-timedelta(days=50),vence_el=timezone.localdate()-timedelta(days=40),estado="EMITIDA",total=100,creado_por=self.u)
        c=CuentaPorCobrar.objects.create(empresa=self.e,factura=f,cliente=self.c,moneda=self.me,fecha_emision=f.fecha,fecha_vencimiento=f.vence_el,monto_original=100,saldo=100,creado_por=self.u);c=actualizar_aging_cuenta(context=self.ctx,cuenta_id=c.pk);self.assertEqual(c.bucket_aging,"31_60");self.assertEqual(c.estado,"EN_MORA")

    def test_factoring_reversion_y_exportaciones_seguras(self):
        f=FacturaVenta.objects.create(empresa=self.e,numero="FF1",cliente=self.c,moneda=self.me,fecha=timezone.localdate(),vence_el=timezone.localdate()+timedelta(days=30),estado="EMITIDA",total=500,creado_por=self.u)
        c=CuentaPorCobrar.objects.create(empresa=self.e,factura=f,cliente=self.c,moneda=self.me,fecha_emision=f.fecha,fecha_vencimiento=f.vence_el,monto_original=500,saldo=500,creado_por=self.u)
        ces=solicitar_factoring(context=self.ctx,cuenta_id=c.pk,factor="Factor Demo",porcentaje=80);ces=avanzar_factoring(context=self.ctx,pk=ces.pk,estado="APROBADA");r=desembolsar_factoring(context=self.ctx,cesion_id=ces.pk,cuenta_bancaria_id=self.banco.pk,comision=10,costo_financiero=15,retencion=5,referencia="FAC-DEMO");self.assertEqual(r["neto"],"470.00")
        rec=registrar_cobro(context=self.ctx,cliente=self.c,moneda=self.me,monto=100,metodo="TRANSFERENCIA",referencia="REV-1");aplicar_cobro(context=self.ctx,recibo_id=rec.pk,cuenta_id=c.pk,monto=100);integrar_cobro(context=self.ctx,recibo_id=rec.pk,cuenta_bancaria_id=self.banco.pk);rev=revertir_cobro_integral(context=self.ctx,recibo_id=rec.pk,motivo="Prueba controlada");self.assertEqual(rev["estado"],"REVERTIDO")
        for formato in ("csv","xlsx","pdf"):self.assertTrue(exportar(context=self.ctx,tipo="facturas",formato=formato).contenido)
