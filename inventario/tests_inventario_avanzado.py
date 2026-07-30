from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from comercial.pedidos_services import siguiente_numero
from conduces.models import Empresa

from .inventario_avanzado_services import (
    aplicar_movimiento, cerrar_ejecucion, consumir_detalle, liberar_reserva,
    preparar_ejecucion, reservar_para_orden,
)
from .models import (
    ConsumoProduccion, DetalleRecetaProduccion, EjecucionInventarioOrden,
    LoteInventario, MovimientoInventario, OrdenProduccion, ProductoInventario,
    RecetaProduccion, ReservaInventario,
)
from .produccion_services import calcular_necesidades


class InventarioAvanzadoSprintTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user("almacen")
        self.empresa = Empresa.objects.create(usuario=self.usuario, nombre="Empresa A")
        self.otra = Empresa.objects.create(nombre="Empresa B")
        self.mp = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="MP", nombre="Harina",
            tipo="materia_prima", unidad_medida="kg", stock_actual=Decimal("20")
        )
        self.pt = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="PT", nombre="Pan",
            tipo="producto_terminado", unidad_medida="unidad"
        )
        self.receta = RecetaProduccion.objects.create(
            empresa=self.empresa, codigo="R", nombre="R", producto_terminado=self.pt,
            rendimiento_base=100, unidad_rendimiento="unidad",
            fecha_vigencia_desde=timezone.localdate(),
        )
        DetalleRecetaProduccion.objects.create(
            receta=self.receta, materia_prima=self.mp, cantidad=10, unidad_medida="kg"
        )
        self.orden = OrdenProduccion.objects.create(
            empresa=self.empresa, numero=siguiente_numero(self.empresa, tipo="OP"),
            producto_terminado=self.pt, receta=self.receta,
            fecha_programada=timezone.localdate(), cantidad_planificada=100,
            unidad_medida="unidad",
        )
        calcular_necesidades(
            cantidad=100, receta=self.receta, empresa=self.empresa, orden=self.orden
        )
        self.lote1 = LoteInventario.objects.create(
            empresa=self.empresa, producto=self.mp, lote="L1",
            fecha_ingreso=timezone.localdate(), fecha_vencimiento=timezone.localdate(),
            cantidad_inicial=10, cantidad_disponible=10,
        )
        self.lote2 = LoteInventario.objects.create(
            empresa=self.empresa, producto=self.mp, lote="L2",
            fecha_ingreso=timezone.localdate(), cantidad_inicial=10, cantidad_disponible=10,
        )

    def test_lote_es_unico_por_empresa_y_producto(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            LoteInventario.objects.create(
                empresa=self.empresa, producto=self.mp, lote="L1",
                fecha_ingreso=timezone.localdate(), cantidad_inicial=1, cantidad_disponible=1
            )

    def test_lote_permite_mismo_numero_en_otra_empresa(self):
        producto = ProductoInventario.objects.create(
            empresa=self.otra, codigo="MP", nombre="Otra", tipo="materia_prima"
        )
        lote = LoteInventario.objects.create(
            empresa=self.otra, producto=producto, lote="L1",
            fecha_ingreso=timezone.localdate(), cantidad_inicial=1, cantidad_disponible=1
        )
        self.assertEqual(lote.empresa, self.otra)

    def test_restricciones_impiden_cantidades_negativas(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            LoteInventario.objects.create(
                empresa=self.empresa, producto=self.mp, lote="NEG",
                fecha_ingreso=timezone.localdate(), cantidad_inicial=1, cantidad_disponible=-1
            )

    def test_reserva_no_modifica_stock_fisico(self):
        reserva = reservar_para_orden(orden=self.orden, empresa=self.empresa, usuario=self.usuario)
        self.mp.refresh_from_db()
        self.assertEqual(self.mp.stock_actual, Decimal("20"))
        self.assertEqual(MovimientoInventario.objects.count(), 0)
        self.assertEqual(reserva.estado, ReservaInventario.Estado.ACTIVA)

    def test_reserva_fefe_y_fifo(self):
        reserva = reservar_para_orden(orden=self.orden, empresa=self.empresa)
        self.assertEqual(reserva.detalles.first().lote, self.lote1)

    def test_reserva_es_idempotente(self):
        primera = reservar_para_orden(orden=self.orden, empresa=self.empresa)
        segunda = reservar_para_orden(orden=self.orden, empresa=self.empresa)
        self.assertEqual(primera.pk, segunda.pk)
        self.assertEqual(ReservaInventario.objects.count(), 1)

    def test_reserva_parcial_si_no_hay_stock_suficiente(self):
        self.orden.necesidades.update(cantidad_con_merma=30)
        reserva = reservar_para_orden(orden=self.orden, empresa=self.empresa)
        self.assertEqual(reserva.estado, ReservaInventario.Estado.PARCIAL)

    def test_liberar_reserva_es_idempotente(self):
        reserva = reservar_para_orden(orden=self.orden, empresa=self.empresa)
        liberar_reserva(reserva=reserva, empresa=self.empresa)
        liberar_reserva(reserva=reserva, empresa=self.empresa)
        self.lote1.refresh_from_db()
        self.assertEqual(self.lote1.cantidad_reservada, 0)

    def test_preparar_requiere_reserva_completa(self):
        self.orden.necesidades.update(cantidad_con_merma=30)
        with self.assertRaises(ValidationError):
            preparar_ejecucion(orden=self.orden, empresa=self.empresa)

    def test_preparar_ejecucion_es_idempotente(self):
        una = preparar_ejecucion(orden=self.orden, empresa=self.empresa)
        dos = preparar_ejecucion(orden=self.orden, empresa=self.empresa)
        self.assertEqual(una.pk, dos.pk)
        self.assertEqual(EjecucionInventarioOrden.objects.count(), 1)

    def test_consumo_reduce_lote_stock_y_reserva(self):
        ejecucion = preparar_ejecucion(orden=self.orden, empresa=self.empresa)
        detalle = ejecucion.reserva.detalles.first()
        consumir_detalle(
            ejecucion=ejecucion, detalle=detalle, cantidad=4,
            clave_idempotencia="consumo-1"
        )
        self.mp.refresh_from_db()
        self.lote1.refresh_from_db()
        self.assertEqual(self.mp.stock_actual, 16)
        self.assertEqual(self.lote1.cantidad_disponible, 6)
        self.assertEqual(self.lote1.cantidad_reservada, 6)

    def test_consumo_no_supera_reserva(self):
        ejecucion = preparar_ejecucion(orden=self.orden, empresa=self.empresa)
        with self.assertRaises(ValidationError):
            consumir_detalle(
                ejecucion=ejecucion, detalle=ejecucion.reserva.detalles.first(),
                cantidad=11, clave_idempotencia="exceso"
            )

    def test_consumo_repetido_no_duplica(self):
        ejecucion = preparar_ejecucion(orden=self.orden, empresa=self.empresa)
        detalle = ejecucion.reserva.detalles.first()
        uno = consumir_detalle(
            ejecucion=ejecucion, detalle=detalle, cantidad=2, clave_idempotencia="igual"
        )
        dos = consumir_detalle(
            ejecucion=ejecucion, detalle=detalle, cantidad=2, clave_idempotencia="igual"
        )
        self.assertEqual(uno.pk, dos.pk)
        self.assertEqual(ConsumoProduccion.objects.count(), 1)

    def test_movimiento_rechaza_stock_negativo(self):
        with self.assertRaises(ValidationError):
            aplicar_movimiento(
                empresa=self.empresa, producto=self.mp, lote=self.lote1,
                tipo="consumo_produccion", cantidad=21
            )
        self.mp.refresh_from_db()
        self.assertEqual(self.mp.stock_actual, 20)

    def test_movimiento_guarda_saldos(self):
        mov = aplicar_movimiento(
            empresa=self.empresa, producto=self.mp, lote=self.lote1,
            tipo="consumo_produccion", cantidad=2
        )
        self.assertEqual((mov.saldo_anterior, mov.saldo_posterior), (20, 18))

    def test_cierre_crea_lote_y_entrada_una_sola_vez(self):
        ejecucion = preparar_ejecucion(orden=self.orden, empresa=self.empresa)
        uno = cerrar_ejecucion(
            ejecucion=ejecucion, cantidad_neta=90, usuario=self.usuario,
            clave_idempotencia="cierre-1"
        )
        dos = cerrar_ejecucion(
            ejecucion=ejecucion, cantidad_neta=90, usuario=self.usuario,
            clave_idempotencia="cierre-1"
        )
        self.pt.refresh_from_db()
        self.assertEqual(uno.pk, dos.pk)
        self.assertEqual(self.pt.stock_actual, 90)
        self.assertEqual(uno.lote.orden_produccion_origen, self.orden)
