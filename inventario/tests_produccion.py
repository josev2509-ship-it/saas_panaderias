from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from auditoria.models import EventoAuditoria
from comercial.models import Cliente, DetallePedido, Pedido
from comercial.pedidos_services import calcular_linea, siguiente_numero
from conduces.models import Empresa
from documentos.services import resolver_objeto_permitido

from .models import (
    DetalleRecetaProduccion, HistorialEstadoOrdenProduccion, MovimientoInventario,
    OrdenProduccion, PlanProduccion, ProductoInventario, RecetaProduccion,
)
from .produccion_services import (
    calcular_necesidades, duplicar_receta, generar_ordenes_desde_plan,
    generar_plan_desde_pedidos, transicionar_orden,
)


class ProduccionSprintTest(TestCase):
    def setUp(self):
        self.user=User.objects.create_user("prod",password="x")
        self.other=User.objects.create_user("otra",password="x")
        self.empresa=Empresa.objects.create(usuario=self.user,nombre="A")
        self.empresa_b=Empresa.objects.create(usuario=self.other,nombre="B")
        self.terminado=ProductoInventario.objects.create(empresa=self.empresa,codigo="PT",nombre="Pan",tipo="producto_terminado",unidad_medida="unidad",activo=True)
        self.materia=ProductoInventario.objects.create(empresa=self.empresa,codigo="MP",nombre="Harina",tipo="materia_prima",unidad_medida="kg",stock_actual=Decimal("20"),activo=True)
        self.terminado_b=ProductoInventario.objects.create(empresa=self.empresa_b,codigo="PT",nombre="Otro",tipo="producto_terminado",activo=True)
        self.materia_b=ProductoInventario.objects.create(empresa=self.empresa_b,codigo="MP",nombre="Otra MP",tipo="materia_prima",activo=True)
        hoy=timezone.localdate()
        self.receta=RecetaProduccion.objects.create(empresa=self.empresa,codigo="REC",nombre="Pan",producto_terminado=self.terminado,version=1,rendimiento_base=Decimal("100"),unidad_rendimiento="unidad",activa=True,fecha_vigencia_desde=hoy)
        self.ing=DetalleRecetaProduccion.objects.create(receta=self.receta,materia_prima=self.materia,cantidad=Decimal("10"),unidad_medida="kg",porcentaje_merma=Decimal("5"))
        self.dar_permisos(self.user)

    def dar_permisos(self,user):
        user.user_permissions.add(*Permission.objects.filter(content_type__app_label="inventario",codename__in=[
            "add_recetaproduccion","change_recetaproduccion","view_recetaproduccion",
            "add_planproduccion","change_planproduccion","view_planproduccion","aprobar_planproduccion","cancelar_planproduccion",
            "add_ordenproduccion","change_ordenproduccion","view_ordenproduccion","programar_ordenproduccion","iniciar_ordenproduccion","completar_ordenproduccion","cancelar_ordenproduccion",
        ]))

    def orden(self,estado=OrdenProduccion.Estado.BORRADOR,empresa=None,receta=None,producto=None):
        empresa=empresa or self.empresa;producto=producto or self.terminado;receta=receta or self.receta
        return OrdenProduccion.objects.create(empresa=empresa,numero=siguiente_numero(empresa,tipo="OP"),producto_terminado=producto,receta=receta,fecha_programada=timezone.localdate(),cantidad_planificada=Decimal("100"),unidad_medida="unidad",estado=estado)

    def pedido_aprobado(self,producto=None):
        sufijo=Cliente.objects.filter(empresa=self.empresa).count()+1
        cliente=Cliente.objects.create(empresa=self.empresa,codigo=f"C{sufijo}",nombre_comercial=f"Cliente {sufijo}",tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO)
        hoy=timezone.localdate()
        pedido=Pedido.objects.create(empresa=self.empresa,numero=siguiente_numero(self.empresa),cliente=cliente,fecha_pedido=hoy,fecha_entrega=hoy+timedelta(days=1),condicion_pago=Cliente.CondicionPago.CONTADO,estado=Pedido.Estado.APROBADO)
        linea=DetallePedido(pedido=pedido,producto=producto or self.terminado,descripcion="Pan",cantidad=Decimal("200"),unidad_medida="unidad",precio_unitario=Decimal("1"),porcentaje_descuento=0,porcentaje_impuesto=0)
        calcular_linea(linea);linea.save();return pedido,linea

    def test_aislamiento_recetas(self):
        RecetaProduccion.objects.create(empresa=self.empresa_b,codigo="B",nombre="B",producto_terminado=self.terminado_b,rendimiento_base=1,unidad_rendimiento="unidad",fecha_vigencia_desde=timezone.localdate())
        self.client.force_login(self.user)
        respuesta=self.client.get(reverse("inventario:recetas_lista"))
        self.assertContains(respuesta,"REC");self.assertNotContains(respuesta,">B<")
        ajena=RecetaProduccion.objects.get(codigo="B")
        self.assertEqual(self.client.get(reverse("inventario:receta_detalle",args=[ajena.pk])).status_code,404)

    def test_productos_y_materia_misma_empresa(self):
        receta=RecetaProduccion(empresa=self.empresa,codigo="X",nombre="X",producto_terminado=self.terminado_b,rendimiento_base=1,unidad_rendimiento="u",fecha_vigencia_desde=timezone.localdate())
        with self.assertRaises(ValidationError):receta.full_clean()
        ingrediente=DetalleRecetaProduccion(receta=self.receta,materia_prima=self.materia_b,cantidad=1,unidad_medida="kg")
        with self.assertRaises(ValidationError):ingrediente.full_clean()

    def test_materia_no_es_producto_y_rendimiento_positivo(self):
        ingrediente=DetalleRecetaProduccion(receta=self.receta,materia_prima=self.terminado,cantidad=1,unidad_medida="u")
        with self.assertRaises(ValidationError):ingrediente.full_clean()
        self.receta.rendimiento_base=0
        with self.assertRaises(ValidationError):self.receta.full_clean()

    def test_receta_vencida_no_inicia(self):
        self.receta.fecha_vigencia_hasta=timezone.localdate()-timedelta(days=1);self.receta.save()
        orden=self.orden(OrdenProduccion.Estado.PROGRAMADA)
        with self.assertRaises(ValidationError):transicionar_orden(orden=orden,empresa=self.empresa,usuario=self.user,accion="iniciar")

    def test_duplicar_incrementa_y_copia_sin_documentos(self):
        nueva=duplicar_receta(receta=self.receta,usuario=self.user)
        self.assertEqual(nueva.version,2);self.assertFalse(nueva.activa);self.assertEqual(nueva.ingredientes.count(),1)
        self.assertEqual(resolver_objeto_permitido(empresa=self.empresa,app_label="inventario",model="recetaproduccion",object_id=nueva.pk),nueva)

    def test_necesidad_decimal_proporcional_merma_sin_movimientos(self):
        antes=MovimientoInventario.objects.count()
        necesidades=calcular_necesidades(cantidad=Decimal("250"),receta=self.receta,empresa=self.empresa)
        self.assertEqual(necesidades[0].cantidad_teorica,Decimal("25.0000"))
        self.assertEqual(necesidades[0].cantidad_con_merma,Decimal("26.2500"))
        self.assertEqual(MovimientoInventario.objects.count(),antes)

    def test_plan_solo_aprobados_referencia_y_no_duplica(self):
        pedido,linea=self.pedido_aprobado()
        plan=generar_plan_desde_pedidos(empresa=self.empresa,pedidos=[pedido],fecha_plan=timezone.localdate(),usuario=self.user)
        detalle=plan.detalles.get();self.assertEqual(detalle.detalle_pedido_origen,linea)
        with self.assertRaises(ValidationError):generar_plan_desde_pedidos(empresa=self.empresa,pedidos=[pedido],fecha_plan=timezone.localdate(),usuario=self.user)
        borrador=self.pedido_aprobado()[0];borrador.estado=Pedido.Estado.BORRADOR;borrador.save()
        with self.assertRaises(ValidationError):generar_plan_desde_pedidos(empresa=self.empresa,pedidos=[borrador],fecha_plan=timezone.localdate(),usuario=self.user)

    def test_producto_sin_receta_advierte(self):
        otro=ProductoInventario.objects.create(empresa=self.empresa,codigo="PT2",nombre="Galleta",tipo="producto_terminado",activo=True)
        pedido,_=self.pedido_aprobado(otro)
        plan=generar_plan_desde_pedidos(empresa=self.empresa,pedidos=[pedido],fecha_plan=timezone.localdate(),usuario=self.user)
        self.assertIsNone(plan.detalles.get().receta);self.assertIn("ADVERTENCIA",plan.detalles.get().observaciones)

    def test_ordenes_empresa_numeracion_y_generacion(self):
        pedido,_=self.pedido_aprobado();plan=generar_plan_desde_pedidos(empresa=self.empresa,pedidos=[pedido],fecha_plan=timezone.localdate(),usuario=self.user)
        plan.estado=PlanProduccion.Estado.APROBADO;plan.save()
        orden=generar_ordenes_desde_plan(plan=plan,empresa=self.empresa,usuario=self.user)[0]
        self.assertTrue(orden.numero.startswith("OP-"));self.assertEqual(orden.empresa,self.empresa)
        otra=self.orden(empresa=self.empresa_b,receta=RecetaProduccion.objects.create(empresa=self.empresa_b,codigo="RB",nombre="B",producto_terminado=self.terminado_b,rendimiento_base=1,unidad_rendimiento="u",activa=True,fecha_vigencia_desde=timezone.localdate()),producto=self.terminado_b)
        self.assertEqual(orden.numero,otra.numero)

    def test_transiciones_permisos_historial_auditoria_idempotencia(self):
        orden=self.orden()
        for accion,estado,kwargs in [
            ("programar",OrdenProduccion.Estado.PROGRAMADA,{}),
            ("iniciar",OrdenProduccion.Estado.EN_PROCESO,{"cantidad_iniciada":100}),
            ("completar",OrdenProduccion.Estado.COMPLETADA,{"cantidad_producida":95,"cantidad_rechazada":5}),
        ]:
            orden=transicionar_orden(orden=orden,empresa=self.empresa,usuario=self.user,accion=accion,**kwargs)
            self.assertEqual(orden.estado,estado)
        self.assertEqual(HistorialEstadoOrdenProduccion.objects.filter(orden=orden).count(),3)
        self.assertEqual(EventoAuditoria.objects.filter(modulo="produccion",object_id=orden.pk).count(),3)
        with self.assertRaises(ValidationError):transicionar_orden(orden=orden,empresa=self.empresa,usuario=self.user,accion="completar",cantidad_producida=95,cantidad_rechazada=5)
        self.assertEqual(HistorialEstadoOrdenProduccion.objects.filter(orden=orden).count(),3)

    def test_permisos_y_cantidades(self):
        sin=User.objects.create_user("sin")
        for estado,accion in [(OrdenProduccion.Estado.BORRADOR,"programar"),(OrdenProduccion.Estado.PROGRAMADA,"iniciar"),(OrdenProduccion.Estado.EN_PROCESO,"completar"),(OrdenProduccion.Estado.BORRADOR,"cancelar")]:
            with self.assertRaises(PermissionDenied):transicionar_orden(orden=self.orden(estado),empresa=self.empresa,usuario=sin,accion=accion)
        orden=self.orden(OrdenProduccion.Estado.EN_PROCESO);orden.cantidad_iniciada=100;orden.save()
        with self.assertRaises(ValidationError):transicionar_orden(orden=orden,empresa=self.empresa,usuario=self.user,accion="completar",cantidad_producida=100,cantidad_rechazada=1)

    def test_acciones_get_completada_no_edita_y_programacion_sin_cancelada(self):
        orden=self.orden(OrdenProduccion.Estado.COMPLETADA);cancelada=self.orden(OrdenProduccion.Estado.CANCELADA)
        self.client.force_login(self.user)
        for nombre in ("orden_programar","orden_iniciar","orden_completar","orden_cancelar"):
            self.assertEqual(self.client.get(reverse(f"inventario:{nombre}",args=[orden.pk])).status_code,405)
        self.assertRedirects(self.client.get(reverse("inventario:orden_editar",args=[orden.pk])),reverse("inventario:orden_detalle",args=[orden.pk]))
        diaria=self.client.get(reverse("inventario:produccion_programacion_diaria"),{"fecha":orden.fecha_programada})
        self.assertContains(diaria,orden.numero);self.assertNotContains(diaria,cancelada.numero)

    def test_documentos_y_vistas_autenticacion(self):
        orden=self.orden()
        self.assertEqual(resolver_objeto_permitido(empresa=self.empresa,app_label="inventario",model="ordenproduccion",object_id=orden.pk),orden)
        with self.assertRaises(ValidationError):resolver_objeto_permitido(empresa=self.empresa_b,app_label="inventario",model="ordenproduccion",object_id=orden.pk)
        for url in [reverse("inventario:produccion_dashboard"),reverse("inventario:recetas_lista"),reverse("inventario:planes_lista"),reverse("inventario:ordenes_lista"),reverse("inventario:orden_detalle",args=[orden.pk]),reverse("inventario:produccion_programacion_diaria")]:
            self.assertEqual(self.client.get(url).status_code,302)
