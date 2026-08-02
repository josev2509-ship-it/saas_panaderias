from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from catalogos.models import Moneda,MonedaEmpresa,Impuesto
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from inventario.models import ProductoInventario
from comercial.application.o2c import *
from comercial.application.crm import crear_prospecto,calificar_prospecto,convertir_prospecto_a_cliente
from comercial.models import *

class NucleoComercialO2CTest(TestCase):
    def setUp(self):
        self.u=User.objects.create_superuser("o2c","o2c@example.invalid","x");self.e=Empresa.objects.create(usuario=self.u,nombre="O2C Test")
        m=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$");self.me=MonedaEmpresa.objects.create(empresa=self.e,moneda=m,es_base=True)
        self.imp=Impuesto.objects.create(empresa=self.e,codigo="ITBIS18",nombre="ITBIS 18",tipo="ITBIS",tasa=18,uso_venta=True,vigente_desde=timezone.localdate(),creado_por=self.u)
        self.inv=ProductoInventario.objects.create(empresa=self.e,codigo="PAN-1",nombre="Pan",tipo="producto_terminado",clasificacion_operativa="producto_terminado",unidad_medida="unidad")
        self.cli=Cliente.objects.create(empresa=self.e,codigo="C1",tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,nombre_comercial="Cliente",rnc_cedula="101000001",condicion_pago=Cliente.CondicionPago.CREDITO,dias_credito=30,limite_credito=100000,descuento_maximo=10,moneda_comercial=self.me,estado=Cliente.Estado.ACTIVO,creado_por=self.u)
        self.ctx=OperationContext(empresa=self.e,usuario=self.u,origen="test")
        self.prod=crear_producto_comercial(context=self.ctx,datos={"producto_inventario":self.inv,"codigo":"PC1","nombre":"Pan venta","unidad_venta":"unidad","impuesto":self.imp,"precio_base":Decimal("50"),"moneda":self.me})

    def lista(self,prioridad=10,codigo="L1"):
        l=crear_lista_precio(context=self.ctx,datos={"codigo":codigo,"nombre":codigo,"moneda":self.me,"vigencia_desde":timezone.localdate(),"prioridad":prioridad})
        DetalleListaPrecio.objects.create(lista=l,producto=self.prod,precio=Decimal("40"));activar_lista_precio(context=self.ctx,pk=l.pk);return l

    def test_riesgo_es_determinista_y_explicable(self):
        a=calcular_riesgo_cliente(context=self.ctx,cliente_id=self.cli.pk,persistir=False);b=calcular_riesgo_cliente(context=self.ctx,cliente_id=self.cli.pk,persistir=False)
        self.assertEqual(a,b);self.assertTrue(0<=a.score<=100);self.assertEqual(a.formula_version,"1.0")

    def test_pricing_decimal_y_hash_reproducible(self):
        self.lista();a=resolver_precio_comercial(context=self.ctx,cliente=self.cli,producto=self.prod,cantidad=Decimal("2"));b=resolver_precio_comercial(context=self.ctx,cliente=self.cli,producto=self.prod,cantidad=Decimal("2"))
        self.assertEqual(a.precio_final,Decimal("40.0000"));self.assertEqual(a.hash_resolucion,b.hash_resolucion);self.assertFalse(a.blockers)

    def test_ambiguedad_bloquea_linea(self):
        self.lista(codigo="L1");self.lista(codigo="L2");r=resolver_precio_comercial(context=self.ctx,cliente=self.cli,producto=self.prod,cantidad=1)
        self.assertTrue(r.blockers)
        c=self.cotizacion()
        with self.assertRaises(ValidationError):agregar_linea_cotizacion(context=self.ctx,cotizacion_id=c.pk,producto=self.prod,cantidad=1,resolucion=r)

    def cotizacion(self):
        return crear_cotizacion(context=self.ctx,datos={"cliente":self.cli,"fecha":timezone.localdate(),"valida_hasta":timezone.localdate()+timedelta(days=15),"moneda":self.me,"condicion_pago":"Crédito","dias_credito":30})

    def test_tenant_estricto_en_producto(self):
        u=User.objects.create_user("otro");e=Empresa.objects.create(usuario=u,nombre="Otra")
        p=ProductoComercial(empresa=e,producto_inventario=self.inv,codigo="X",nombre="X",unidad_venta="u",moneda=self.me)
        with self.assertRaises(ValidationError):p.full_clean()

    def test_end_to_end_cotizacion_pedido_programacion(self):
        prospecto=crear_prospecto(context=self.ctx,datos={"nombre":"Prospecto E2E","nombre_comercial":"Cliente convertido E2E","identificacion_fiscal":"E2E001","correo":"e2e@example.invalid"});calificar_prospecto(context=self.ctx,pk=prospecto.pk);cliente=convertir_prospecto_a_cliente(context=self.ctx,pk=prospecto.pk);cliente.condicion_pago=Cliente.CondicionPago.CREDITO;cliente.dias_credito=30;cliente.limite_credito=100000;cliente.moneda_comercial=self.me;cliente.estado=Cliente.Estado.ACTIVO;cliente.save()
        self.lista();r=resolver_precio_comercial(context=self.ctx,cliente=cliente,producto=self.prod,cantidad=10);c=crear_cotizacion(context=self.ctx,datos={"cliente":cliente,"fecha":timezone.localdate(),"valida_hasta":timezone.localdate()+timedelta(days=15),"moneda":self.me,"condicion_pago":"Crédito","dias_credito":30});agregar_linea_cotizacion(context=self.ctx,cotizacion_id=c.pk,producto=self.prod,cantidad=10,resolucion=r)
        for a in ("revision","aprobar","enviar","aceptar"):c=transicionar_cotizacion(context=self.ctx,pk=c.pk,accion=a)
        p=convertir_cotizacion_a_pedido(context=self.ctx,pk=c.pk,fecha_entrega=timezone.localdate()+timedelta(days=3));p=transicionar_pedido(pedido=p,empresa=self.e,usuario=self.u,accion="enviar");p=aprobar_pedido_o2c(context=self.ctx,pk=p.pk);pr=programar_pedido(context=self.ctx,pk=p.pk,fecha=p.fecha_entrega)
        self.assertEqual(pr.estado,"PROGRAMADA");self.assertEqual(Pedido.objects.get(pk=p.pk).estado,Pedido.Estado.PROGRAMADO);self.assertGreaterEqual(c.historial.count(),5)

    def test_conversion_es_idempotente(self):
        self.lista();r=resolver_precio_comercial(context=self.ctx,cliente=self.cli,producto=self.prod,cantidad=1);c=self.cotizacion();agregar_linea_cotizacion(context=self.ctx,cotizacion_id=c.pk,producto=self.prod,cantidad=1,resolucion=r)
        for a in ("revision","aprobar","enviar","aceptar"):transicionar_cotizacion(context=self.ctx,pk=c.pk,accion=a)
        a=convertir_cotizacion_a_pedido(context=self.ctx,pk=c.pk,fecha_entrega=timezone.localdate()+timedelta(days=1));b=convertir_cotizacion_a_pedido(context=self.ctx,pk=c.pk,fecha_entrega=timezone.localdate()+timedelta(days=2));self.assertEqual(a.pk,b.pk)
