from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Case, DecimalField, F, Q, Sum, Value, When
from django.utils import timezone

from auditoria.models import EventoAuditoria
from core.application.idempotency import begin, complete, fail
from core.domain.exceptions import CrossCompanyViolation
from core.infrastructure.audit_adapter import (
    audit_create, audit_inventory_movement, audit_reversal, audit_update,
)
from core.models import ConciliacionInventario, RegistroIdempotencia
from core.application.event_bus import event_bus
from core.domain.events import (
    EjecucionInventarioRevertida, InventarioConsumido,
    ProductoTerminadoIngresado, ReservaInventarioCreada,
)

from .inventario_avanzado_services import (
    aplicar_movimiento, cerrar_ejecucion, consumir_detalle, liberar_reserva,
    preparar_ejecucion, registrar_devolucion, reservar_para_orden, revertir_ejecucion,
)
from .inventario_avanzado_services import ENTRADAS, SALIDAS
from .models import LoteInventario, MovimientoInventario, ProductoInventario


def _validate_company(context, *objects):
    for obj in objects:
        company_id = getattr(obj, "empresa_id", None)
        if company_id and company_id != context.empresa.pk:
            raise CrossCompanyViolation("El objeto pertenece a otra empresa.")


def _idempotent_result(*, context, operation, payload, model, callback, allow_retry=False):
    record, execute = begin(
        context=context, operation=operation, payload=payload, allow_retry=allow_retry
    )
    if not execute and record.estado == RegistroIdempotencia.Estado.COMPLETADA:
        return model.objects.get(pk=record.resultado_referencia)
    try:
        with transaction.atomic():
            result = callback()
            complete(record, result.pk)
        return result
    except Exception as exc:
        fail(record, exc)
        raise


class InventoryEngine:
    @staticmethod
    def commercial_availability(*, context, producto, cantidad=0):
        """Lectura ATP para Comercial; el ledger y los lotes siguen siendo canónicos."""
        _validate_company(context, producto)
        reservado=calcular_reservado(producto)
        # Las reservas comerciales viven en Comercial, pero solo esta fachada
        # puede incorporarlas al ATP del inventario.
        from comercial.models import DetalleReservaComercial,ReservaComercial
        comercial=DetalleReservaComercial.objects.filter(
            reserva__empresa=context.empresa,producto=producto,
            reserva__estado__in=["PENDIENTE","PARCIAL","COMPLETA"],
        ).aggregate(total=Sum(F("cantidad_reservada")-F("cantidad_consumida")))["total"] or 0
        disponible=Decimal(producto.stock_actual or 0)-Decimal(reservado)-Decimal(comercial)
        return {"producto_id":producto.pk,"existencia":Decimal(producto.stock_actual or 0),"reservado":Decimal(reservado)+Decimal(comercial),"disponible":max(Decimal(0),disponible),"suficiente":disponible>=Decimal(cantidad or 0)}

    @staticmethod
    @transaction.atomic
    def reserve_commercial(*, context, detalle):
        """Selecciona lotes FEFO/FIFO y registra la reserva comercial."""
        _validate_company(context,detalle.reserva,detalle.producto)
        if detalle.cantidad_reservada:return detalle
        restante=Decimal(detalle.cantidad_solicitada)
        lotes=LoteInventario.objects.select_for_update().filter(empresa=context.empresa,producto=detalle.producto,activo=True).exclude(fecha_vencimiento__lt=timezone.localdate()).order_by("fecha_vencimiento","fecha_ingreso","id")
        # El detalle comercial representa una selección única; si hay varios
        # lotes, se crean detalles adicionales sin duplicar stock.
        from comercial.models import DetalleReservaComercial
        primero=True
        for lote in lotes:
            libre=Decimal(lote.cantidad_disponible)-Decimal(lote.cantidad_reservada)
            tomar=min(max(Decimal(0),libre),restante)
            if tomar<=0:continue
            target=detalle if primero else DetalleReservaComercial.objects.create(reserva=detalle.reserva,detalle_pedido=detalle.detalle_pedido,producto=detalle.producto,lote=lote,cantidad_solicitada=detalle.cantidad_solicitada,cantidad_reservada=0)
            target.lote=lote;target.cantidad_reservada=tomar;target.save(update_fields=["lote","cantidad_reservada"]);lote.cantidad_reservada=F("cantidad_reservada")+tomar;lote.save(update_fields=["cantidad_reservada","actualizado_en"]);restante-=tomar;primero=False
            if restante<=0:break
        return detalle

    @staticmethod
    @transaction.atomic
    def release_commercial(*,context,reserva):
        _validate_company(context,reserva)
        for d in reserva.detalles.select_for_update().select_related("lote"):
            pendiente=Decimal(d.cantidad_reservada)-Decimal(d.cantidad_consumida)
            if d.lote_id and pendiente>0:LoteInventario.objects.filter(pk=d.lote_id).update(cantidad_reservada=F("cantidad_reservada")-pendiente)
        return reserva

    @staticmethod
    @transaction.atomic
    def confirm_commercial_outbound(*,context,reserva,referencia):
        _validate_company(context,reserva)
        movimientos=[]
        for d in reserva.detalles.select_for_update().select_related("lote","producto"):
            cantidad=Decimal(d.cantidad_reservada)-Decimal(d.cantidad_consumida)
            if cantidad<=0:continue
            if d.lote_id:LoteInventario.objects.filter(pk=d.lote_id).update(cantidad_reservada=F("cantidad_reservada")-cantidad)
            movimientos.append(InventoryEngine.apply_movement(context=context,producto=d.producto,lote=d.lote,tipo="salida",cantidad=cantidad,referencia=referencia));d.cantidad_consumida=F("cantidad_consumida")+cantidad;d.save(update_fields=["cantidad_consumida"])
        return movimientos
    @staticmethod
    def apply_movement(*, context, producto, tipo, cantidad, lote=None, referencia=""):
        _validate_company(context, producto, lote)
        record, execute = begin(
            context=context, operation="inventario.apply_movement",
            payload={
                "producto": producto.pk, "lote": getattr(lote, "pk", None),
                "tipo": tipo, "cantidad": str(cantidad), "referencia": referencia,
            },
        )
        if not execute and record.estado == RegistroIdempotencia.Estado.COMPLETADA:
            return MovimientoInventario.objects.get(pk=record.resultado_referencia)
        try:
            with transaction.atomic():
                movement = aplicar_movimiento(
                    empresa=context.empresa, producto=producto, lote=lote, tipo=tipo,
                    cantidad=cantidad, usuario=context.usuario, referencia=referencia,
                    clave_idempotencia=f"core:{record.pk}",
                )
                audit_inventory_movement(
                    context=context, module="inventario", obj=movement,
                    description=f"Movimiento {movement.tipo} aplicado.",
                    before={"saldo": str(movement.saldo_anterior)},
                    after={"saldo": str(movement.saldo_posterior), "cantidad": str(movement.cantidad)},
                )
                complete(record, movement.pk)
            return movement
        except Exception as exc:
            fail(record, exc)
            raise

    @staticmethod
    def reserve(*, context, orden):
        _validate_company(context, orden)
        from .models import ReservaInventario
        return _idempotent_result(
            context=context, operation="inventario.reserve",
            payload={"orden_id": orden.pk}, model=ReservaInventario,
            callback=lambda: InventoryEngine._reserve_once(context=context, orden=orden),
        )

    @staticmethod
    def _reserve_once(*, context, orden):
        reserva = reservar_para_orden(orden=orden, empresa=context.empresa, usuario=context.usuario)
        audit_create(
            context=context, module="inventario", obj=reserva,
            description=f"Reserva {reserva.numero} creada.",
            after={"estado": reserva.estado, "orden_id": orden.pk},
        )
        event_bus.publish(ReservaInventarioCreada(
            empresa_id=context.empresa.pk, usuario_id=getattr(context.usuario, "pk", None),
            agregado_tipo="inventario.ReservaInventario", agregado_id=str(reserva.pk),
            referencia=reserva.numero,
            clave_idempotente=f"reserva:{reserva.pk}:creada",
            payload={"orden_id": orden.pk, "estado": reserva.estado},
        ))
        return reserva

    @staticmethod
    def release_reservation(*, context, reserva):
        _validate_company(context, reserva)
        from .models import ReservaInventario
        return _idempotent_result(
            context=context, operation="inventario.release_reservation",
            payload={"reserva_id": reserva.pk}, model=ReservaInventario,
            callback=lambda: InventoryEngine._release_once(context=context, reserva=reserva),
        )

    @staticmethod
    def _release_once(*, context, reserva):
        before = reserva.estado
        result = liberar_reserva(reserva=reserva, empresa=context.empresa)
        audit_update(
            context=context, module="inventario", obj=result,
            description=f"Reserva {result.numero} liberada.",
            before={"estado": before}, after={"estado": result.estado},
        )
        return result

    @staticmethod
    def cancel_reservation(*, context, reserva):
        from .models import ReservaInventario
        _validate_company(context, reserva)
        return _idempotent_result(
            context=context, operation="inventario.cancel_reservation",
            payload={"reserva_id": reserva.pk}, model=ReservaInventario,
            callback=lambda: InventoryEngine._cancel_once(context=context, reserva=reserva),
        )

    @staticmethod
    def _cancel_once(*, context, reserva):
        result = liberar_reserva(reserva=reserva, empresa=context.empresa)
        result.estado = result.Estado.CANCELADA
        result.save(update_fields=["estado", "actualizado_en"])
        return result

    @staticmethod
    def prepare_execution(*, context, orden):
        from .models import EjecucionInventarioOrden
        _validate_company(context, orden)
        return _idempotent_result(
            context=context, operation="inventario.prepare_execution",
            payload={"orden_id": orden.pk}, model=EjecucionInventarioOrden,
            callback=lambda: preparar_ejecucion(
                orden=orden, empresa=context.empresa, usuario=context.usuario,
                clave_idempotencia=context.clave_idempotente,
            ),
        )

    @staticmethod
    def consume(*, context, ejecucion, detalle, cantidad):
        _validate_company(context, ejecucion)
        from .models import ConsumoProduccion
        return _idempotent_result(
            context=context, operation="inventario.consume",
            payload={"ejecucion_id": ejecucion.pk, "detalle_id": detalle.pk, "cantidad": str(cantidad)},
            model=ConsumoProduccion,
            callback=lambda: InventoryEngine._consume_once(
                context=context, ejecucion=ejecucion, detalle=detalle, cantidad=cantidad
            ),
        )

    @staticmethod
    def _consume_once(*, context, ejecucion, detalle, cantidad):
        consumo = consumir_detalle(
            ejecucion=ejecucion, detalle=detalle, cantidad=cantidad,
            usuario=context.usuario, clave_idempotencia=context.clave_idempotente,
        )
        audit_create(
            context=context, module="inventario", obj=consumo,
            description="Consumo de produccion registrado.",
            after={"cantidad": str(consumo.cantidad)},
        )
        event_bus.publish(InventarioConsumido(
            empresa_id=context.empresa.pk, usuario_id=getattr(context.usuario, "pk", None),
            agregado_tipo="inventario.ConsumoProduccion", agregado_id=str(consumo.pk),
            referencia=context.referencia,
            clave_idempotente=f"consumo:{consumo.pk}",
            payload={"cantidad": str(consumo.cantidad), "lote_id": consumo.detalle_reserva.lote_id},
        ))
        return consumo

    @staticmethod
    def return_material(*, context, ejecucion, lote, cantidad):
        _validate_company(context, ejecucion, lote)
        from .models import DevolucionProduccion
        return _idempotent_result(
            context=context, operation="inventario.return_material",
            payload={"ejecucion_id": ejecucion.pk, "lote_id": lote.pk, "cantidad": str(cantidad)},
            model=DevolucionProduccion,
            callback=lambda: InventoryEngine._return_once(
                context=context, ejecucion=ejecucion, lote=lote, cantidad=cantidad
            ),
        )

    @staticmethod
    def _return_once(*, context, ejecucion, lote, cantidad):
        result = registrar_devolucion(
            ejecucion=ejecucion, lote=lote, cantidad=cantidad,
            usuario=context.usuario, clave_idempotencia=context.clave_idempotente,
        )
        audit_create(
            context=context, module="inventario", obj=result,
            description="Devolucion de produccion registrada.",
            after={"cantidad": str(result.cantidad)},
        )
        return result

    @staticmethod
    def enter_finished_product(*, context, ejecucion, cantidad_neta, **kwargs):
        _validate_company(context, ejecucion)
        from .models import LoteProduccion
        payload = {"ejecucion_id": ejecucion.pk, "cantidad_neta": str(cantidad_neta), **{k: str(v) for k, v in kwargs.items()}}
        return _idempotent_result(
            context=context, operation="inventario.enter_finished_product",
            payload=payload, model=LoteProduccion,
            callback=lambda: InventoryEngine._enter_once(
                context=context, ejecucion=ejecucion, cantidad_neta=cantidad_neta, **kwargs
            ),
        )

    @staticmethod
    def _enter_once(*, context, ejecucion, cantidad_neta, **kwargs):
        result = cerrar_ejecucion(
            ejecucion=ejecucion, cantidad_neta=cantidad_neta,
            usuario=context.usuario, clave_idempotencia=context.clave_idempotente,
            **kwargs,
        )
        audit_create(
            context=context, module="inventario", obj=result,
            description="Producto terminado ingresado.",
            after={"cantidad_neta": str(result.cantidad_neta), "lote_id": result.lote_id},
        )
        event_bus.publish(ProductoTerminadoIngresado(
            empresa_id=context.empresa.pk, usuario_id=getattr(context.usuario, "pk", None),
            agregado_tipo="inventario.LoteProduccion", agregado_id=str(result.pk),
            referencia=context.referencia,
            clave_idempotente=f"producto-terminado:{result.pk}",
            payload={"cantidad_neta": str(result.cantidad_neta), "lote_id": result.lote_id},
        ))
        return result

    @staticmethod
    def reverse_operation(*, context, ejecucion, motivo):
        _validate_company(context, ejecucion)
        if not context.usuario or not context.usuario.has_perm("inventario.revertir_ejecucion_inventario"):
            raise PermissionDenied
        from .models import EjecucionInventarioOrden
        return _idempotent_result(
            context=context, operation="inventario.reverse_operation",
            payload={"ejecucion_id": ejecucion.pk, "motivo": motivo},
            model=EjecucionInventarioOrden,
            callback=lambda: InventoryEngine._reverse_once(
                context=context, ejecucion=ejecucion, motivo=motivo
            ),
        )

    @staticmethod
    def _reverse_once(*, context, ejecucion, motivo):
        result = revertir_ejecucion(
            ejecucion=ejecucion, usuario=context.usuario, motivo=motivo
        )
        audit_reversal(
            context=context, module="inventario", obj=result,
            description="Ejecucion de inventario revertida.",
            before={"estado": "CERRADA"}, after={"estado": result.estado, "motivo": motivo},
        )
        event_bus.publish(EjecucionInventarioRevertida(
            empresa_id=context.empresa.pk, usuario_id=getattr(context.usuario, "pk", None),
            agregado_tipo="inventario.EjecucionInventarioOrden",
            agregado_id=str(result.pk), referencia=context.referencia,
            clave_idempotente=f"reversion:{result.pk}",
            payload={"motivo": motivo},
        ))
        return result

    @staticmethod
    def record_waste(*, context, ejecucion, lote, cantidad, motivo, aprobado_por=None):
        from .inventario_avanzado_services import registrar_merma
        from .models import MermaProduccion
        _validate_company(context, ejecucion, lote)
        return _idempotent_result(
            context=context, operation="inventario.record_waste",
            payload={"ejecucion_id": ejecucion.pk, "lote_id": lote.pk, "cantidad": str(cantidad), "motivo": motivo},
            model=MermaProduccion,
            callback=lambda: registrar_merma(
                ejecucion=ejecucion, lote=lote, cantidad=cantidad, motivo=motivo,
                usuario=context.usuario, aprobado_por=aprobado_por,
                clave_idempotencia=context.clave_idempotente,
            ),
        )

    @staticmethod
    def validate_stock(producto, quantity):
        return Decimal(producto.stock_actual or 0) >= Decimal(quantity or 0)

    calculate_balance = staticmethod(lambda producto, hasta_fecha=None: calcular_saldo_desde_movimientos(producto, hasta_fecha))

    @staticmethod
    def apply_authorized_adjustment(
        *, context, producto, cantidad, entrada=True, lote=None, requiere_lote=None
    ):
        if not context.usuario or not context.usuario.has_perm("inventario.change_productoinventario"):
            raise PermissionDenied
        has_lots = producto.lotes.filter(activo=True).exists()
        lot_required = has_lots if requiere_lote is None else requiere_lote
        if lot_required and lote is None:
            raise ValueError("El producto requiere un lote para este ajuste.")
        return InventoryEngine.apply_movement(
            context=context, producto=producto, lote=lote,
            tipo="ajuste" if entrada else "salida", cantidad=cantidad,
            referencia=context.referencia,
        )

    @staticmethod
    def reconcile_product(*, context, producto):
        return diagnosticar_producto(context=context, producto=producto)

    @staticmethod
    def rebuild_cached_balance(*, context, producto, motivo):
        return reconstruir_stock_cacheado(context=context, producto=producto, motivo=motivo)


def calcular_saldo_desde_movimientos(producto, hasta_fecha=None):
    """Calculate the ledger independently; never trust cached posterior balances."""
    movements = MovimientoInventario.objects.filter(
        empresa=producto.empresa, producto=producto
    )
    if hasta_fecha:
        movements = movements.filter(fecha__lte=hasta_fecha)
    opening = movements.order_by("fecha", "id").values_list(
        "saldo_anterior", flat=True
    ).first()
    signed = movements.aggregate(total=Sum(Case(
        When(
            Q(naturaleza=MovimientoInventario.Naturaleza.ENTRADA)
            | Q(naturaleza="", tipo__in=ENTRADAS),
            then=F("cantidad"),
        ),
        When(
            Q(naturaleza=MovimientoInventario.Naturaleza.SALIDA)
            | Q(naturaleza="", tipo__in=SALIDAS),
            then=-F("cantidad"),
        ),
        default=Value(0),
        output_field=DecimalField(max_digits=18, decimal_places=4),
    )))["total"]
    return Decimal(opening or 0) + Decimal(signed or 0)


def verificar_consistencia_lotes(producto):
    return Decimal(
        LoteInventario.objects.filter(
            empresa=producto.empresa, producto=producto, activo=True
        ).aggregate(total=Sum("cantidad_disponible"))["total"] or 0
    )


def calcular_reservado(producto):
    from .models import DetalleReservaInventario, ReservaInventario
    return Decimal(
        DetalleReservaInventario.objects.filter(
            lote__empresa=producto.empresa,
            lote__producto=producto,
            reserva__estado__in=[
                ReservaInventario.Estado.ACTIVA,
                ReservaInventario.Estado.PARCIAL,
            ],
        ).aggregate(total=Sum(
            F("cantidad_reservada") - F("cantidad_consumida") - F("cantidad_liberada")
        ))["total"] or 0
    )


def vista_previa_reconstruccion(*, context, producto):
    _validate_company(context, producto)
    historical = calcular_saldo_desde_movimientos(producto)
    cached = Decimal(producto.stock_actual or 0)
    lots = verificar_consistencia_lotes(producto)
    reserved = calcular_reservado(producto)
    has_lots = producto.lotes.filter(activo=True).exists()
    return {
        "saldo_calculado": historical,
        "saldo_cacheado": cached,
        "saldo_lotes": lots,
        "saldo_reservado": reserved,
        "saldo_disponible": historical - reserved,
        "diferencia": historical - cached,
        "lotes_consistentes": not has_lots or lots == historical,
        "requiere_intervencion": has_lots and lots != historical,
    }


@transaction.atomic
def diagnosticar_producto(*, context, producto):
    _validate_company(context, producto)
    producto = ProductoInventario.objects.select_for_update().get(
        pk=producto.pk, empresa=context.empresa
    )
    preview = vista_previa_reconstruccion(context=context, producto=producto)
    movements = preview["saldo_calculado"]
    cached = preview["saldo_cacheado"]
    lots = preview["saldo_lotes"]
    reserved = preview["saldo_reservado"]
    state = (
        ConciliacionInventario.Estado.CONSISTENTE
        if movements == cached and lots == cached
        else ConciliacionInventario.Estado.DIFERENCIA
    )
    return ConciliacionInventario.objects.create(
        empresa=context.empresa, producto=producto, saldo_movimientos=movements,
        saldo_cacheado=cached, saldo_lotes=lots, saldo_reservado=reserved,
        saldo_disponible=preview["saldo_disponible"],
        diferencia_movimientos_cache=movements - cached,
        diferencia_lotes_cache=lots - cached, estado=state,
        severidad=(
            ConciliacionInventario.Severidad.NINGUNA
            if state == ConciliacionInventario.Estado.CONSISTENTE
            else ConciliacionInventario.Severidad.ALTA
        ),
        modo=ConciliacionInventario.Modo.DIAGNOSTICO,
        ejecutado_por=context.usuario if getattr(context.usuario, "is_authenticated", False) else None,
        referencia=context.referencia,
        metadata={"request_id": context.identificador_solicitud},
    )


def reconstruir_stock_cacheado(*, context, producto, motivo):
    return _idempotent_result(
        context=context, operation="inventario.rebuild_cached_balance",
        payload={"producto_id": producto.pk, "motivo": motivo},
        model=ConciliacionInventario,
        callback=lambda: _reconstruir_stock_cacheado_once(
            context=context, producto=producto, motivo=motivo
        ),
    )


@transaction.atomic
def _reconstruir_stock_cacheado_once(*, context, producto, motivo):
    if not context.usuario or not context.usuario.has_perm("core.rebuild_inventory_balance"):
        raise PermissionDenied
    if not motivo or not motivo.strip():
        raise ValueError("El motivo es obligatorio.")
    _validate_company(context, producto)
    producto = ProductoInventario.objects.select_for_update().get(
        pk=producto.pk, empresa=context.empresa
    )
    preview = vista_previa_reconstruccion(context=context, producto=producto)
    target = preview["saldo_calculado"]
    previous = preview["saldo_cacheado"]
    lots = preview["saldo_lotes"]
    producto.stock_actual = target
    producto.save(update_fields=["stock_actual"])
    reconciliation = ConciliacionInventario.objects.create(
        empresa=context.empresa, producto=producto, saldo_movimientos=target,
        saldo_cacheado=previous, saldo_lotes=lots,
        saldo_reservado=preview["saldo_reservado"],
        saldo_disponible=preview["saldo_disponible"],
        diferencia_movimientos_cache=target - previous,
        diferencia_lotes_cache=lots - previous,
        estado=(
            ConciliacionInventario.Estado.REQUIERE_INTERVENCION
            if preview["requiere_intervencion"]
            else ConciliacionInventario.Estado.CORREGIDA
        ),
        severidad=(
            ConciliacionInventario.Severidad.ALTA
            if preview["requiere_intervencion"]
            else ConciliacionInventario.Severidad.NINGUNA
        ),
        modo=ConciliacionInventario.Modo.CORRECCION, motivo=motivo.strip(),
        ejecutado_por=context.usuario,
        corregido_por=context.usuario,
        fecha_correccion=timezone.now(),
        referencia=context.referencia,
        observaciones=(
            "El saldo cacheado fue reconstruido; los lotes requieren intervencion."
            if preview["requiere_intervencion"] else "Reconstruccion completada."
        ),
        metadata={"request_id": context.identificador_solicitud, "operation": "rebuild"},
    )
    audit_update(
        context=context, module="inventario", obj=reconciliation,
        description=f"Se reconstruyo el saldo de {producto.codigo}.",
        before={"stock_actual": str(previous)}, after={"stock_actual": str(target)},
    )
    from core.domain.events import SaldoReconstruido
    event_bus.publish(SaldoReconstruido(
        empresa_id=context.empresa.pk, usuario_id=context.usuario.pk,
        agregado_tipo="core.ConciliacionInventario",
        agregado_id=str(reconciliation.pk), referencia=context.referencia,
        clave_idempotente=f"reconstruccion:{reconciliation.pk}",
        payload={"producto_id": producto.pk, "saldo_anterior": str(previous), "saldo_nuevo": str(target)},
        requiere_consumidor=True,
    ))
    return reconciliation
