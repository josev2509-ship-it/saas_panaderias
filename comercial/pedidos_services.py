from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento

from .models import Cliente, DetallePedido, HistorialEstadoPedido, Pedido, SecuenciaDocumento

CENTAVO = Decimal("0.01")


def moneda(valor):
    return Decimal(valor or 0).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def calcular_linea(detalle):
    bruto = Decimal(detalle.cantidad) * Decimal(detalle.precio_unitario)
    detalle.monto_descuento = moneda(bruto * Decimal(detalle.porcentaje_descuento) / Decimal("100"))
    detalle.subtotal = moneda(bruto - detalle.monto_descuento)
    detalle.monto_impuesto = moneda(detalle.subtotal * Decimal(detalle.porcentaje_impuesto) / Decimal("100"))
    detalle.total = moneda(detalle.subtotal + detalle.monto_impuesto)
    return detalle


def recalcular_pedido(pedido):
    detalles = list(pedido.detalles.all())
    pedido.subtotal = moneda(sum((d.subtotal for d in detalles), Decimal("0")))
    pedido.descuento_total = moneda(sum((d.monto_descuento for d in detalles), Decimal("0")))
    pedido.impuesto_total = moneda(sum((d.monto_impuesto for d in detalles), Decimal("0")))
    pedido.total = moneda(sum((d.total for d in detalles), Decimal("0")))
    pedido.save(update_fields=["subtotal", "descuento_total", "impuesto_total", "total", "fecha_actualizacion"])
    return pedido


def siguiente_numero(empresa, fecha=None):
    fecha = fecha or timezone.localdate()
    with transaction.atomic():
        secuencia, _ = SecuenciaDocumento.objects.select_for_update().get_or_create(
            empresa=empresa, tipo="PED", periodo=fecha.year, defaults={"ultimo_numero": 0}
        )
        secuencia.ultimo_numero += 1
        secuencia.save(update_fields=["ultimo_numero"])
        return f"PED-{fecha.year}-{secuencia.ultimo_numero:06d}"


def validar_envio(pedido):
    errores = []
    if not pedido.detalles.exists():
        errores.append("El pedido debe tener al menos una línea.")
    if pedido.cliente.estado not in {Cliente.Estado.ACTIVO, Cliente.Estado.EN_EVALUACION}:
        errores.append("El estado del cliente no permite enviar el pedido a aprobación.")
    if pedido.detalles.filter(porcentaje_descuento__gt=pedido.cliente.descuento_maximo).exists():
        errores.append("Hay descuentos superiores al máximo permitido para el cliente.")
    if errores:
        raise ValidationError(errores)


TRANSICIONES = {
    "enviar": (Pedido.Estado.BORRADOR, Pedido.Estado.PENDIENTE_APROBACION, "comercial.change_pedido"),
    "aprobar": (Pedido.Estado.PENDIENTE_APROBACION, Pedido.Estado.APROBADO, "comercial.aprobar_pedido"),
    "rechazar": (Pedido.Estado.PENDIENTE_APROBACION, Pedido.Estado.RECHAZADO, "comercial.rechazar_pedido"),
    "reabrir": (Pedido.Estado.RECHAZADO, Pedido.Estado.BORRADOR, "comercial.change_pedido"),
    "cancelar_borrador": (Pedido.Estado.BORRADOR, Pedido.Estado.CANCELADO, "comercial.cancelar_pedido"),
    "cancelar_pendiente": (Pedido.Estado.PENDIENTE_APROBACION, Pedido.Estado.CANCELADO, "comercial.cancelar_pedido"),
}


@transaction.atomic
def transicionar_pedido(*, pedido, empresa, usuario, accion, comentario="", request=None):
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk, empresa=empresa)
    clave = accion
    if accion == "cancelar":
        clave = "cancelar_borrador" if pedido.estado == Pedido.Estado.BORRADOR else "cancelar_pendiente"
    if clave not in TRANSICIONES:
        raise ValidationError("Acción de estado no permitida.")
    origen, destino, permiso = TRANSICIONES[clave]
    if not usuario.has_perm(permiso):
        raise PermissionDenied
    if pedido.estado != origen:
        raise ValidationError("El pedido ya fue procesado o no admite esta transición.")
    if accion == "enviar":
        validar_envio(pedido)
    ahora = timezone.now()
    if accion == "aprobar":
        pedido.aprobado_por, pedido.fecha_aprobacion = usuario, ahora
    if accion == "rechazar":
        if not comentario.strip():
            raise ValidationError("Debes indicar el motivo del rechazo.")
        pedido.rechazado_por, pedido.fecha_rechazo, pedido.motivo_rechazo = usuario, ahora, comentario.strip()
    if accion == "reabrir":
        pedido.rechazado_por = None
        pedido.fecha_rechazo = None
        pedido.motivo_rechazo = ""
    pedido.estado = destino
    pedido.actualizado_por = usuario
    pedido.save()
    HistorialEstadoPedido.objects.create(
        empresa=empresa, pedido=pedido, estado_anterior=origen,
        estado_nuevo=destino, usuario=usuario, comentario=comentario,
    )
    registrar_evento(
        empresa=empresa, usuario=usuario, request=request, objeto=pedido, modulo="comercial",
        accion=EventoAuditoria.Accion.CAMBIAR_ESTADO,
        descripcion=f"Pedido {pedido.numero}: {pedido.get_estado_display()}.",
        datos_anteriores={"estado": origen}, datos_nuevos={"estado": destino},
    )
    return pedido


@transaction.atomic
def duplicar_pedido(*, origen, empresa, usuario, request=None):
    origen = Pedido.objects.prefetch_related("detalles").get(pk=origen.pk, empresa=empresa)
    hoy = timezone.localdate()
    diferencia = max(origen.fecha_entrega - origen.fecha_pedido, timedelta(days=0))
    nuevo = Pedido.objects.create(
        empresa=empresa, numero=siguiente_numero(empresa, hoy), cliente=origen.cliente,
        direccion_entrega=origen.direccion_entrega, contacto=origen.contacto,
        fecha_pedido=hoy, fecha_entrega=hoy + diferencia,
        hora_entrega_desde=origen.hora_entrega_desde, hora_entrega_hasta=origen.hora_entrega_hasta,
        prioridad=origen.prioridad, condicion_pago=origen.condicion_pago,
        dias_credito=origen.dias_credito, lista_precio=origen.lista_precio,
        moneda=origen.moneda, observaciones_cliente=origen.observaciones_cliente,
        observaciones_internas=origen.observaciones_internas, creado_por=usuario, actualizado_por=usuario,
    )
    for linea in origen.detalles.all():
        linea.pk = None
        linea.pedido = nuevo
        linea.save()
    recalcular_pedido(nuevo)
    registrar_evento(
        empresa=empresa, usuario=usuario, request=request, objeto=nuevo, modulo="comercial",
        accion=EventoAuditoria.Accion.CREAR,
        descripcion=f"Se duplicó el pedido {origen.numero} como {nuevo.numero}.",
        datos_nuevos={"pedido_origen": origen.pk, "numero": nuevo.numero},
    )
    return nuevo
