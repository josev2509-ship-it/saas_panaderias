"""Implementacion interna del inventario.

Los consumidores productivos deben usar ``inventario.engine.InventoryEngine``.
Estas funciones se conservan para compatibilidad y para la fachada; no forman
parte de la API publica del ERP.
"""

from decimal import Decimal

__all__ = ()

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, F, IntegerField, Value, When
from django.utils import timezone

from comercial.pedidos_services import siguiente_numero

from .models import (
    ConsumoProduccion, DetalleReservaInventario, DevolucionProduccion,
    EjecucionInventarioOrden, LoteInventario, LoteProduccion,
    MermaProduccion, MovimientoInventario, OrdenProduccion,
    ProductoInventario, ReservaInventario,
)

ENTRADAS = {"entrada", "entrada_compra", "ajuste", "prestamo_recibido",
            "devolucion_prestamo", "devolucion_produccion",
            "entrada_producto_terminado", "reversion_consumo"}
SALIDAS = {"salida", "produccion", "merma", "prestamo_entregado",
           "consumo_produccion", "merma_produccion", "reversion_entrada"}


def _q(valor):
    return Decimal(valor or 0).quantize(Decimal("0.0001"))


def _estado_lote(lote):
    if lote.fecha_vencimiento and lote.fecha_vencimiento < timezone.localdate():
        return LoteInventario.Estado.VENCIDO
    if lote.cantidad_disponible <= 0:
        return LoteInventario.Estado.AGOTADO
    return LoteInventario.Estado.DISPONIBLE


@transaction.atomic
def aplicar_movimiento(*, empresa, producto, tipo, cantidad, usuario=None, lote=None,
                       orden=None, ejecucion=None, clave_idempotencia=None,
                       referencia="", revertido_de=None):
    cantidad = _q(cantidad)
    if cantidad <= 0 or tipo not in ENTRADAS | SALIDAS:
        raise ValidationError("Tipo o cantidad de movimiento invalido.")
    if clave_idempotencia:
        previo = MovimientoInventario.objects.filter(clave_idempotencia=clave_idempotencia).first()
        if previo:
            return previo
    producto = ProductoInventario.objects.select_for_update().get(pk=producto.pk, empresa=empresa)
    lote_bloqueado = None
    if lote:
        lote_bloqueado = LoteInventario.objects.select_for_update().get(
            pk=lote.pk, empresa=empresa, producto=producto
        )
        if tipo in SALIDAS and (
            not lote_bloqueado.activo
            or lote_bloqueado.estado != LoteInventario.Estado.DISPONIBLE
            or (
                lote_bloqueado.fecha_vencimiento
                and lote_bloqueado.fecha_vencimiento < timezone.localdate()
            )
        ):
            raise ValidationError("El lote no esta disponible o esta vencido.")
    anterior = _q(producto.stock_actual)
    posterior = anterior + cantidad if tipo in ENTRADAS else anterior - cantidad
    if posterior < 0:
        raise ValidationError("El movimiento produciria stock negativo.")
    if tipo in SALIDAS:
        if lote_bloqueado and lote_bloqueado.cantidad_disponible < cantidad:
            raise ValidationError("El lote no posee existencia suficiente.")
        if lote_bloqueado:
            lote_bloqueado.cantidad_disponible = F("cantidad_disponible") - cantidad
    elif lote_bloqueado:
        lote_bloqueado.cantidad_disponible = F("cantidad_disponible") + cantidad
        lote_bloqueado.cantidad_inicial = F("cantidad_inicial") + cantidad
    producto.stock_actual = posterior
    producto.save(update_fields=["stock_actual"])
    if lote_bloqueado:
        lote_bloqueado.save(update_fields=["cantidad_disponible", "cantidad_inicial", "actualizado_en"])
        lote_bloqueado.refresh_from_db()
        lote_bloqueado.estado = _estado_lote(lote_bloqueado)
        lote_bloqueado.save(update_fields=["estado", "actualizado_en"])
    return MovimientoInventario.objects.create(
        empresa=empresa, producto=producto, lote=lote_bloqueado, tipo=tipo,
        cantidad=cantidad, usuario=usuario, orden_produccion=orden,
        ejecucion=ejecucion, referencia=referencia,
        saldo_anterior=anterior, saldo_posterior=posterior,
        clave_idempotencia=clave_idempotencia,
        aplicado_por_servicio=True, revertido_de=revertido_de,
        naturaleza=(
            MovimientoInventario.Naturaleza.ENTRADA
            if tipo in ENTRADAS else MovimientoInventario.Naturaleza.SALIDA
        ),
        operacion_origen="InventoryEngine",
        es_reversion=revertido_de is not None,
    )


@transaction.atomic
def reservar_para_orden(*, orden, empresa, usuario=None):
    orden = OrdenProduccion.objects.select_for_update().get(pk=orden.pk, empresa=empresa)
    existente = orden.reservas_inventario.filter(
        estado__in=[ReservaInventario.Estado.ACTIVA, ReservaInventario.Estado.PARCIAL]
    ).first()
    if existente:
        return existente
    reserva = ReservaInventario.objects.create(
        empresa=empresa, numero=siguiente_numero(empresa, timezone.localdate(), "RES"),
        orden=orden, creado_por=usuario,
    )
    completa = True
    for necesidad in orden.necesidades.select_related("materia_prima"):
        restante = _q(necesidad.cantidad_con_merma)
        lotes = LoteInventario.objects.select_for_update().filter(
            empresa=empresa, producto=necesidad.materia_prima, activo=True,
            estado=LoteInventario.Estado.DISPONIBLE,
        ).exclude(
            fecha_vencimiento__lt=timezone.localdate()
        ).annotate(
            sin_vencimiento=Case(
                When(fecha_vencimiento__isnull=True, then=Value(1)),
                default=Value(0), output_field=IntegerField(),
            )
        ).order_by("sin_vencimiento", "fecha_vencimiento", "fecha_ingreso", "id")
        for lote in lotes:
            libre = _q(lote.cantidad_disponible - lote.cantidad_reservada)
            tomar = min(libre, restante)
            if tomar <= 0:
                continue
            DetalleReservaInventario.objects.create(
                reserva=reserva, necesidad=necesidad, lote=lote, cantidad_reservada=tomar
            )
            lote.cantidad_reservada = F("cantidad_reservada") + tomar
            lote.save(update_fields=["cantidad_reservada", "actualizado_en"])
            restante -= tomar
            if restante <= 0:
                break
        if restante > 0:
            completa = False
    reserva.estado = ReservaInventario.Estado.ACTIVA if completa else ReservaInventario.Estado.PARCIAL
    reserva.save(update_fields=["estado", "actualizado_en"])
    return reserva


@transaction.atomic
def liberar_reserva(*, reserva, empresa):
    reserva = ReservaInventario.objects.select_for_update().get(pk=reserva.pk, empresa=empresa)
    if reserva.estado in {ReservaInventario.Estado.LIBERADA, ReservaInventario.Estado.CONSUMIDA}:
        return reserva
    for detalle in reserva.detalles.select_for_update().select_related("lote"):
        pendiente = detalle.cantidad_pendiente
        if pendiente > 0:
            LoteInventario.objects.filter(pk=detalle.lote_id).update(
                cantidad_reservada=F("cantidad_reservada") - pendiente
            )
            detalle.cantidad_liberada = F("cantidad_liberada") + pendiente
            detalle.save(update_fields=["cantidad_liberada"])
    reserva.estado = ReservaInventario.Estado.LIBERADA
    reserva.save(update_fields=["estado", "actualizado_en"])
    return reserva


@transaction.atomic
def preparar_ejecucion(*, orden, empresa, usuario=None, clave_idempotencia=None):
    previo = EjecucionInventarioOrden.objects.filter(orden=orden, empresa=empresa).first()
    if previo:
        return previo
    reserva = reservar_para_orden(orden=orden, empresa=empresa, usuario=usuario)
    if reserva.estado != ReservaInventario.Estado.ACTIVA:
        raise ValidationError("La orden no tiene reserva completa.")
    return EjecucionInventarioOrden.objects.create(
        empresa=empresa, orden=orden, reserva=reserva, iniciado_por=usuario,
        clave_idempotencia=clave_idempotencia or f"ejecucion:{empresa.pk}:{orden.pk}",
    )


@transaction.atomic
def consumir_detalle(*, ejecucion, detalle, cantidad, usuario=None, clave_idempotencia):
    ejecucion = EjecucionInventarioOrden.objects.select_for_update().get(
        pk=ejecucion.pk, empresa=ejecucion.empresa
    )
    detalle = DetalleReservaInventario.objects.select_for_update().select_related(
        "lote", "necesidad__materia_prima"
    ).get(pk=detalle.pk, reserva=ejecucion.reserva)
    cantidad = _q(cantidad)
    if cantidad <= 0 or cantidad > detalle.cantidad_pendiente:
        raise ValidationError("El consumo supera la reserva disponible.")
    previo = MovimientoInventario.objects.filter(clave_idempotencia=clave_idempotencia).first()
    if previo:
        return previo.consumo
    # La reserva debe bajar antes que la existencia para mantener en todo
    # momento el constraint cantidad_reservada <= cantidad_disponible.
    LoteInventario.objects.filter(pk=detalle.lote_id).update(
        cantidad_reservada=F("cantidad_reservada") - cantidad
    )
    detalle.lote.refresh_from_db()
    movimiento = aplicar_movimiento(
        empresa=ejecucion.empresa, producto=detalle.necesidad.materia_prima,
        lote=detalle.lote, tipo="consumo_produccion", cantidad=cantidad,
        usuario=usuario, orden=ejecucion.orden, ejecucion=ejecucion,
        clave_idempotencia=clave_idempotencia,
    )
    detalle.cantidad_consumida = F("cantidad_consumida") + cantidad
    detalle.save(update_fields=["cantidad_consumida"])
    ejecucion.estado = EjecucionInventarioOrden.Estado.EN_PROCESO
    ejecucion.save(update_fields=["estado"])
    return ConsumoProduccion.objects.create(
        ejecucion=ejecucion, detalle_reserva=detalle, movimiento=movimiento,
        cantidad=cantidad, creado_por=usuario,
    )


@transaction.atomic
def cerrar_ejecucion(*, ejecucion, cantidad_neta, usuario=None, numero_lote=None,
                     fecha_vencimiento=None, clave_idempotencia=None):
    ejecucion = EjecucionInventarioOrden.objects.select_for_update().select_related(
        "orden__producto_terminado"
    ).get(pk=ejecucion.pk)
    if hasattr(ejecucion, "lote_produccion"):
        return ejecucion.lote_produccion
    cantidad_neta = _q(cantidad_neta)
    if cantidad_neta <= 0:
        raise ValidationError("La cantidad neta debe ser positiva.")
    producto = ejecucion.orden.producto_terminado
    lote = LoteInventario.objects.create(
        empresa=ejecucion.empresa, producto=producto,
        lote=numero_lote or siguiente_numero(ejecucion.empresa, timezone.localdate(), "LOT"),
        fecha_ingreso=timezone.localdate(), fecha_fabricacion=timezone.localdate(),
        fecha_vencimiento=fecha_vencimiento, cantidad_inicial=0, cantidad_disponible=0,
        unidad_medida=ejecucion.orden.unidad_medida,
        tipo_origen=LoteInventario.Origen.PRODUCCION,
        referencia_origen=ejecucion.orden.numero,
        orden_produccion_origen=ejecucion.orden, creado_por=usuario,
    )
    movimiento = aplicar_movimiento(
        empresa=ejecucion.empresa, producto=producto, lote=lote,
        tipo="entrada_producto_terminado", cantidad=cantidad_neta, usuario=usuario,
        orden=ejecucion.orden, ejecucion=ejecucion,
        clave_idempotencia=clave_idempotencia or f"cierre:{ejecucion.pk}",
    )
    registro = LoteProduccion.objects.create(
        ejecucion=ejecucion, lote=lote, movimiento_entrada=movimiento, cantidad_neta=cantidad_neta
    )
    liberar_reserva(reserva=ejecucion.reserva, empresa=ejecucion.empresa)
    ejecucion.estado = EjecucionInventarioOrden.Estado.CERRADA
    ejecucion.cerrado_por = usuario
    ejecucion.cerrado_en = timezone.now()
    ejecucion.save(update_fields=["estado", "cerrado_por", "cerrado_en"])
    return registro


@transaction.atomic
def registrar_merma(*, ejecucion, lote, cantidad, motivo, usuario=None,
                    aprobado_por=None, clave_idempotencia):
    cantidad = _q(cantidad)
    if cantidad <= 0 or not motivo:
        raise ValidationError("La merma y su motivo son obligatorios.")
    previo = MovimientoInventario.objects.filter(clave_idempotencia=clave_idempotencia).first()
    if previo:
        return previo.merma_produccion
    movimiento = aplicar_movimiento(
        empresa=ejecucion.empresa, producto=lote.producto, lote=lote,
        tipo="merma_produccion", cantidad=cantidad, usuario=usuario,
        orden=ejecucion.orden, ejecucion=ejecucion,
        clave_idempotencia=clave_idempotencia,
    )
    return MermaProduccion.objects.create(
        ejecucion=ejecucion, lote=lote, movimiento=movimiento, cantidad=cantidad,
        motivo=motivo, creado_por=usuario, aprobado_por=aprobado_por,
    )


@transaction.atomic
def registrar_devolucion(*, ejecucion, lote, cantidad, usuario=None, clave_idempotencia):
    cantidad = _q(cantidad)
    consumido = sum(
        (c.cantidad for c in ejecucion.consumos.filter(detalle_reserva__lote=lote)),
        Decimal("0"),
    )
    devuelto = sum(
        (d.cantidad for d in ejecucion.devoluciones.filter(lote=lote)),
        Decimal("0"),
    )
    if cantidad <= 0 or cantidad > consumido - devuelto:
        raise ValidationError("La devolucion supera el material consumido.")
    previo = MovimientoInventario.objects.filter(clave_idempotencia=clave_idempotencia).first()
    if previo:
        return previo.devolucion_produccion
    movimiento = aplicar_movimiento(
        empresa=ejecucion.empresa, producto=lote.producto, lote=lote,
        tipo="devolucion_produccion", cantidad=cantidad, usuario=usuario,
        orden=ejecucion.orden, ejecucion=ejecucion,
        clave_idempotencia=clave_idempotencia,
    )
    return DevolucionProduccion.objects.create(
        ejecucion=ejecucion, lote=lote, movimiento=movimiento,
        cantidad=cantidad, creado_por=usuario,
    )


@transaction.atomic
def revertir_ejecucion(*, ejecucion, usuario, motivo):
    ejecucion = EjecucionInventarioOrden.objects.select_for_update().select_related(
        "orden"
    ).get(pk=ejecucion.pk)
    if ejecucion.estado == EjecucionInventarioOrden.Estado.REVERSADA:
        return ejecucion
    if not motivo:
        raise ValidationError("El motivo de reversion es obligatorio.")
    if not hasattr(ejecucion, "lote_produccion"):
        raise ValidationError("La ejecucion no esta cerrada.")
    terminado = ejecucion.lote_produccion
    lote_pt = LoteInventario.objects.select_for_update().get(pk=terminado.lote_id)
    if lote_pt.cantidad_disponible != terminado.cantidad_neta:
        raise ValidationError("El lote terminado ya fue utilizado.")
    aplicar_movimiento(
        empresa=ejecucion.empresa, producto=lote_pt.producto, lote=lote_pt,
        tipo="reversion_entrada", cantidad=terminado.cantidad_neta, usuario=usuario,
        orden=ejecucion.orden, ejecucion=ejecucion,
        clave_idempotencia=f"reversion-entrada:{ejecucion.pk}",
        revertido_de=terminado.movimiento_entrada,
    )
    for consumo in ejecucion.consumos.select_related(
        "detalle_reserva__lote__producto", "movimiento"
    ):
        aplicar_movimiento(
            empresa=ejecucion.empresa, producto=consumo.detalle_reserva.lote.producto,
            lote=consumo.detalle_reserva.lote, tipo="reversion_consumo",
            cantidad=consumo.cantidad, usuario=usuario, orden=ejecucion.orden,
            ejecucion=ejecucion, clave_idempotencia=f"reversion-consumo:{consumo.pk}",
            revertido_de=consumo.movimiento,
        )
    ejecucion.estado = EjecucionInventarioOrden.Estado.REVERSADA
    ejecucion.reversado_por = usuario
    ejecucion.reversado_en = timezone.now()
    ejecucion.save(update_fields=["estado", "reversado_por", "reversado_en"])
    return ejecucion
