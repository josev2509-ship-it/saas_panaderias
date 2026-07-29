from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from auditoria.models import EventoAuditoria
from conduces.models import Empresa
from inventario.models import ProductoInventario
from documentos.services import resolver_objeto_permitido

from .models import Cliente, ContactoCliente, DetallePedido, DireccionCliente, HistorialEstadoPedido, Pedido
from .pedidos_services import (
    calcular_linea, duplicar_pedido, recalcular_pedido, siguiente_numero, transicionar_pedido,
)


class PedidosTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user("ped-a", password="clave")
        self.user_b = User.objects.create_user("ped-b", password="clave")
        self.empresa_a = Empresa.objects.create(usuario=self.user_a, nombre="Empresa A")
        self.empresa_b = Empresa.objects.create(usuario=self.user_b, nombre="Empresa B")
        self.cliente_a = Cliente.objects.create(
            empresa=self.empresa_a, codigo="A1", nombre_comercial="Cliente A",
            tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO, descuento_maximo=Decimal("10"),
        )
        self.cliente_b = Cliente.objects.create(
            empresa=self.empresa_b, codigo="B1", nombre_comercial="Cliente B",
            tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,
        )
        self.direccion_a = DireccionCliente.objects.create(cliente=self.cliente_a, nombre="Entrega", tipo="ENTREGA", direccion="Calle 1")
        self.contacto_a = ContactoCliente.objects.create(cliente=self.cliente_a, nombre="Ana", activo=True)
        self.producto_a = ProductoInventario.objects.create(
            empresa=self.empresa_a, codigo="PT1", nombre="Pan", tipo="producto_terminado",
            unidad_medida="unidad", porcentaje_itbis=18,
        )
        self.producto_b = ProductoInventario.objects.create(
            empresa=self.empresa_b, codigo="PT1", nombre="Otro", tipo="producto_terminado",
        )
        self.dar_permisos(self.user_a)

    def dar_permisos(self, usuario):
        usuario.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="comercial",
            codename__in=["add_pedido", "change_pedido", "view_pedido", "aprobar_pedido", "rechazar_pedido", "cancelar_pedido"],
        ))

    def pedido(self, empresa=None, cliente=None, estado=Pedido.Estado.BORRADOR, moneda=Pedido.Moneda.DOP):
        empresa = empresa or self.empresa_a
        cliente = cliente or self.cliente_a
        hoy = timezone.localdate()
        return Pedido.objects.create(
            empresa=empresa, numero=siguiente_numero(empresa, hoy), cliente=cliente,
            fecha_pedido=hoy, fecha_entrega=hoy + timedelta(days=1),
            condicion_pago=Cliente.CondicionPago.CONTADO, estado=estado, moneda=moneda,
        )

    def linea(self, pedido=None, descuento=Decimal("10"), precio=Decimal("100"), cantidad=Decimal("2")):
        detalle = DetallePedido(
            pedido=pedido or self.pedido(), producto=self.producto_a, descripcion="Pan",
            cantidad=cantidad, unidad_medida="unidad", precio_unitario=precio,
            porcentaje_descuento=descuento, porcentaje_impuesto=Decimal("18"),
        )
        calcular_linea(detalle)
        detalle.save()
        recalcular_pedido(detalle.pedido)
        return detalle

    def test_aislamiento_lista_detalle_edicion(self):
        propio = self.pedido()
        ajeno = self.pedido(empresa=self.empresa_b, cliente=self.cliente_b)
        self.client.force_login(self.user_a)
        lista = self.client.get(reverse("comercial:pedidos_lista"))
        self.assertContains(lista, self.cliente_a.nombre_comercial)
        self.assertNotContains(lista, self.cliente_b.nombre_comercial)
        self.assertEqual(self.client.get(reverse("comercial:pedido_detalle", args=[ajeno.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("comercial:pedido_editar", args=[ajeno.pk])).status_code, 404)

    def test_relaciones_deben_corresponder(self):
        pedido = self.pedido()
        pedido.cliente = self.cliente_b
        with self.assertRaises(ValidationError): pedido.full_clean()
        pedido.cliente = self.cliente_a
        pedido.direccion_entrega = DireccionCliente.objects.create(cliente=self.cliente_b, nombre="B", tipo="ENTREGA", direccion="B")
        with self.assertRaises(ValidationError): pedido.full_clean()
        pedido.direccion_entrega = None
        pedido.contacto = ContactoCliente.objects.create(cliente=self.cliente_b, nombre="B")
        with self.assertRaises(ValidationError): pedido.full_clean()

    def test_numeracion_empresa(self):
        uno = siguiente_numero(self.empresa_a)
        dos = siguiente_numero(self.empresa_a)
        otro = siguiente_numero(self.empresa_b)
        self.assertNotEqual(uno, dos)
        self.assertEqual(uno, otro)

    def test_fecha_entrega_invalida(self):
        pedido = self.pedido()
        pedido.fecha_entrega = pedido.fecha_pedido - timedelta(days=1)
        with self.assertRaises(ValidationError): pedido.full_clean()

    def test_calculos_decimal_y_redondeo(self):
        detalle = self.linea(cantidad=Decimal("1.005"), precio=Decimal("10.00"), descuento=Decimal("0"))
        self.assertEqual(detalle.subtotal, Decimal("10.05"))
        self.assertEqual(detalle.monto_impuesto, Decimal("1.81"))
        self.assertEqual(detalle.total, Decimal("11.86"))
        detalle.pedido.refresh_from_db()
        self.assertEqual(detalle.pedido.total, Decimal("11.86"))

    def test_sin_lineas_no_envia(self):
        pedido = self.pedido()
        with self.assertRaises(ValidationError):
            transicionar_pedido(pedido=pedido, empresa=self.empresa_a, usuario=self.user_a, accion="enviar")

    def test_descuento_excesivo_y_cliente_bloqueado(self):
        pedido = self.pedido()
        self.linea(pedido, descuento=Decimal("11"))
        with self.assertRaises(ValidationError):
            transicionar_pedido(pedido=pedido, empresa=self.empresa_a, usuario=self.user_a, accion="enviar")
        pedido.detalles.update(porcentaje_descuento=0)
        self.cliente_a.estado = Cliente.Estado.BLOQUEADO_CREDITO
        self.cliente_a.save()
        with self.assertRaises(ValidationError):
            transicionar_pedido(pedido=pedido, empresa=self.empresa_a, usuario=self.user_a, accion="enviar")

    def test_transiciones_historial_auditoria_y_reapertura(self):
        pedido = self.pedido()
        self.linea(pedido, descuento=Decimal("0"))
        for accion, esperado in [
            ("enviar", Pedido.Estado.PENDIENTE_APROBACION),
            ("rechazar", Pedido.Estado.RECHAZADO),
            ("reabrir", Pedido.Estado.BORRADOR),
        ]:
            pedido = transicionar_pedido(
                pedido=pedido, empresa=self.empresa_a, usuario=self.user_a, accion=accion,
                comentario="Motivo" if accion == "rechazar" else "",
            )
            self.assertEqual(pedido.estado, esperado)
        self.assertEqual(HistorialEstadoPedido.objects.filter(pedido=pedido).count(), 3)
        self.assertEqual(EventoAuditoria.objects.filter(object_id=pedido.pk, modulo="comercial").count(), 3)

    def test_aprobar_rechazar_cancelar_requieren_permiso(self):
        usuario = User.objects.create_user("sin-permiso")
        for estado, accion in [
            (Pedido.Estado.PENDIENTE_APROBACION, "aprobar"),
            (Pedido.Estado.PENDIENTE_APROBACION, "rechazar"),
            (Pedido.Estado.BORRADOR, "cancelar"),
        ]:
            pedido = self.pedido(estado=estado)
            with self.assertRaises(PermissionDenied):
                transicionar_pedido(pedido=pedido, empresa=self.empresa_a, usuario=usuario, accion=accion, comentario="No")

    def test_acciones_rechazan_get_y_aprobado_no_edita(self):
        pedido = self.pedido(estado=Pedido.Estado.APROBADO)
        self.client.force_login(self.user_a)
        for nombre in ("pedido_enviar_aprobacion", "pedido_aprobar", "pedido_rechazar", "pedido_reabrir", "pedido_cancelar", "pedido_duplicar"):
            self.assertEqual(self.client.get(reverse(f"comercial:{nombre}", args=[pedido.pk])).status_code, 405)
        respuesta = self.client.get(reverse("comercial:pedido_editar", args=[pedido.pk]))
        self.assertRedirects(respuesta, reverse("comercial:pedido_detalle", args=[pedido.pk]))

    def test_duplicar_numero_nuevo_sin_aprobacion(self):
        pedido = self.pedido(estado=Pedido.Estado.APROBADO)
        pedido.aprobado_por = self.user_a
        pedido.fecha_aprobacion = timezone.now()
        pedido.save()
        self.linea(pedido)
        nuevo = duplicar_pedido(origen=pedido, empresa=self.empresa_a, usuario=self.user_a)
        self.assertNotEqual(nuevo.numero, pedido.numero)
        self.assertEqual(nuevo.estado, Pedido.Estado.BORRADOR)
        self.assertIsNone(nuevo.aprobado_por)
        self.assertEqual(nuevo.detalles.count(), 1)

    def test_programacion_no_incluye_cancelados_y_totales_separados(self):
        dop = self.pedido(moneda=Pedido.Moneda.DOP)
        usd = self.pedido(moneda=Pedido.Moneda.USD)
        cancelado = self.pedido(estado=Pedido.Estado.CANCELADO)
        dop.total, usd.total, cancelado.total = Decimal("100"), Decimal("20"), Decimal("999")
        dop.save(); usd.save(); cancelado.save()
        self.client.force_login(self.user_a)
        lista = self.client.get(reverse("comercial:pedidos_lista"))
        self.assertContains(lista, "DOP 100")
        self.assertContains(lista, "USD 20")
        diaria = self.client.get(reverse("comercial:programacion_diaria"), {"fecha": dop.fecha_entrega})
        self.assertContains(diaria, dop.numero)
        self.assertNotContains(diaria, cancelado.numero)

    def test_vistas_requieren_autenticacion(self):
        pedido = self.pedido()
        for url in [
            reverse("comercial:pedidos_dashboard"), reverse("comercial:pedidos_lista"),
            reverse("comercial:pedido_crear"), reverse("comercial:pedido_detalle", args=[pedido.pk]),
            reverse("comercial:programacion_diaria"), reverse("comercial:programacion_semanal"),
        ]:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code, 302)

    def test_documentos_pedido_respetan_empresa(self):
        pedido = self.pedido()
        self.assertEqual(
            resolver_objeto_permitido(
                empresa=self.empresa_a, app_label="comercial", model="pedido", object_id=pedido.pk
            ),
            pedido,
        )
        with self.assertRaises(ValidationError):
            resolver_objeto_permitido(
                empresa=self.empresa_b, app_label="comercial", model="pedido", object_id=pedido.pk
            )

    def test_flujo_manual_crear_editar_enviar_aprobar_y_programar(self):
        segundo = ProductoInventario.objects.create(
            empresa=self.empresa_a, codigo="PT2", nombre="Galleta",
            tipo="producto_terminado", unidad_medida="unidad",
        )
        hoy = timezone.localdate()
        self.client.force_login(self.user_a)
        datos = {
            "cliente": self.cliente_a.pk, "direccion_entrega": self.direccion_a.pk,
            "contacto": self.contacto_a.pk, "fecha_pedido": hoy.isoformat(),
            "fecha_entrega": (hoy + timedelta(days=2)).isoformat(),
            "prioridad": Pedido.Prioridad.ALTA, "condicion_pago": Cliente.CondicionPago.CONTADO,
            "dias_credito": 0, "lista_precio": "", "moneda": Pedido.Moneda.DOP,
            "observaciones_cliente": "Entregar temprano", "observaciones_internas": "",
            "detalles-TOTAL_FORMS": 2, "detalles-INITIAL_FORMS": 0,
            "detalles-MIN_NUM_FORMS": 0, "detalles-MAX_NUM_FORMS": 1000,
            "detalles-0-producto": self.producto_a.pk, "detalles-0-cantidad": "2",
            "detalles-0-precio_unitario": "100", "detalles-0-porcentaje_descuento": "5",
            "detalles-0-porcentaje_impuesto": "18", "detalles-0-observaciones": "", "detalles-0-orden": 1,
            "detalles-1-producto": segundo.pk, "detalles-1-cantidad": "3",
            "detalles-1-precio_unitario": "50", "detalles-1-porcentaje_descuento": "0",
            "detalles-1-porcentaje_impuesto": "0", "detalles-1-observaciones": "", "detalles-1-orden": 2,
        }
        creado = self.client.post(reverse("comercial:pedido_crear"), datos)
        self.assertEqual(creado.status_code, 302, creado.context and creado.context.get("form").errors)
        pedido = Pedido.objects.get(cliente=self.cliente_a)
        self.assertEqual(pedido.detalles.count(), 2)
        self.assertEqual(pedido.total, Decimal("374.20"))
        enviado = self.client.post(reverse("comercial:pedido_enviar_aprobacion", args=[pedido.pk]))
        self.assertEqual(enviado.status_code, 302)
        aprobado = self.client.post(reverse("comercial:pedido_aprobar", args=[pedido.pk]))
        self.assertEqual(aprobado.status_code, 302)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.APROBADO)
        diaria = self.client.get(reverse("comercial:programacion_diaria"), {"fecha": pedido.fecha_entrega})
        semanal = self.client.get(reverse("comercial:programacion_semanal"), {"fecha": hoy})
        self.assertContains(diaria, pedido.numero)
        self.assertContains(semanal, pedido.numero)
        self.assertContains(diaria, 'class="com-page"')
