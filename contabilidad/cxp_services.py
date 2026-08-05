from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from core.application.event_bus import event_bus
from tesoreria.models import MovimientoTesoreria
from tesoreria.api import registrar_egreso

from .api import contabilizar_factura_proveedor, contabilizar_pago_proveedor
from .domain_events import CuentaPorPagarCreada, FacturaProveedorRegistrada, PagoProveedorRegistrado
from .models import AplicacionPago, CuentaPorPagarEnterprise, MovimientoCxP


def _publicar(clase, obj, context, clave, payload=None):
    event_bus.publish(clase(empresa_id=context.empresa.pk, usuario_id=getattr(context.usuario, "pk", None), agregado_tipo=f"contabilidad.{obj._meta.model_name}", agregado_id=str(obj.pk), referencia=str(obj.pk), clave_idempotente=clave, payload={"schema_version": 1, "empresa_id": context.empresa.pk, **(payload or {})}))


@transaction.atomic
def registrar_factura(*, context, factura):
    factura = factura.__class__.objects.select_for_update().get(pk=factura.pk, empresa=context.empresa)
    cuenta, creada = CuentaPorPagarEnterprise.objects.get_or_create(empresa=context.empresa, factura=factura, defaults={"proveedor": factura.proveedor, "moneda": factura.moneda, "monto_original": factura.total, "saldo": factura.total, "vence_el": factura.vence_el, "creado_por": context.usuario})
    if creada:
        MovimientoCxP.objects.create(cuenta=cuenta, tipo="FACTURA", monto=factura.total, saldo_anterior=0, saldo_posterior=factura.total)
        contabilizar_factura_proveedor(context=context, factura=factura)
        _publicar(FacturaProveedorRegistrada, factura, context, f"factura-proveedor:{factura.pk}")
        _publicar(CuentaPorPagarCreada, cuenta, context, f"cxp-creada:{cuenta.pk}")
    return cuenta


@transaction.atomic
def aplicar_pago(*, context, orden, cuenta_bancaria=None, caja=None, monto=0, referencia=""):
    monto = Decimal(str(monto))
    orden = orden.__class__.objects.select_for_update().select_related("solicitud__cuenta").get(pk=orden.pk, empresa=context.empresa)
    cuenta = CuentaPorPagarEnterprise.objects.select_for_update().get(pk=orden.solicitud.cuenta_id, empresa=context.empresa)
    origen_id=f"{orden.pk}:{referencia}"
    existente = MovimientoTesoreria.objects.filter(empresa=context.empresa, referencia=f"PAGO_PROVEEDOR:{origen_id}", tipo="EGRESO").first()
    if existente:
        return existente
    if monto <= 0 or monto > cuenta.saldo or monto > orden.solicitud.monto:
        raise ValidationError("Monto de pago inválido.")
    anterior = cuenta.saldo
    movimiento_dto = registrar_egreso(context=context, origen_tipo="PAGO_PROVEEDOR", origen_id=origen_id, fecha=timezone.localdate(), monto=monto, referencia=referencia, cuenta_id=getattr(cuenta_bancaria,"pk",None),caja_id=getattr(caja,"pk",None))
    movimiento = MovimientoTesoreria.objects.get(pk=movimiento_dto.id, empresa=context.empresa)
    cuenta.saldo -= monto
    cuenta.estado = "PAGADA" if cuenta.saldo == 0 else "PARCIAL"
    cuenta.save(update_fields=["saldo", "estado"])
    AplicacionPago.objects.create(orden=orden, cuenta=cuenta, monto=monto)
    MovimientoCxP.objects.create(cuenta=cuenta, tipo="PAGO", monto=-monto, saldo_anterior=anterior, saldo_posterior=cuenta.saldo)
    orden.estado = "PAGADA" if cuenta.saldo == 0 else "PARCIAL"
    orden.save(update_fields=["estado"])
    contabilizar_pago_proveedor(context=context, pago=movimiento)
    registrar_evento(empresa=context.empresa, usuario=context.usuario, objeto=cuenta, modulo="cuentas_por_pagar", accion=EventoAuditoria.Accion.CAMBIAR_ESTADO, descripcion="Pago de proveedor aplicado.", datos_anteriores={"saldo": str(anterior)}, datos_nuevos={"saldo": str(cuenta.saldo), "referencia": referencia})
    _publicar(PagoProveedorRegistrado, movimiento, context, f"pago-proveedor:{referencia}", {"monto": str(monto)})
    return movimiento
