from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from contabilidad.domain_events import MovimientoTesoreriaRegistrado,MovimientoTesoreriaReversado
from core.application.event_bus import event_bus

from .models import CuentaBancariaEmpresa, Caja, FlujoCajaProyectado, MovimientoTesoreria


@dataclass(frozen=True)
class MovimientoTesoreriaDTO:
    id: int
    tipo: str
    fecha: str
    monto: str
    referencia: str
    cuenta_id: int | None
    caja_id: int | None
    conciliado: bool


def _dto(obj):
    return MovimientoTesoreriaDTO(obj.pk, obj.tipo, str(obj.fecha), str(obj.monto), obj.referencia, obj.cuenta_id, obj.caja_id, obj.conciliado)


@transaction.atomic
def registrar_ingreso(*, context, origen_tipo, origen_id, fecha, monto, referencia, cuenta_id=None, caja_id=None):
    monto = Decimal(str(monto))
    if monto <= 0 or bool(cuenta_id) == bool(caja_id):
        raise ValidationError("Indique un importe positivo y exactamente un destino de tesorería.")
    clave = f"{origen_tipo}:{origen_id}"
    existente = MovimientoTesoreria.objects.filter(empresa=context.empresa, tipo="INGRESO", referencia=clave).first()
    if existente: return _dto(existente)
    cuenta = CuentaBancariaEmpresa.objects.select_for_update().get(pk=cuenta_id, empresa=context.empresa, activa=True) if cuenta_id else None
    caja = Caja.objects.select_for_update().get(pk=caja_id, empresa=context.empresa) if caja_id else None
    destino = cuenta or caja
    movimiento = MovimientoTesoreria.objects.create(empresa=context.empresa, cuenta=cuenta, caja=caja, tipo="INGRESO", fecha=fecha, monto=monto, referencia=clave)
    destino.saldo += monto; destino.save(update_fields=["saldo"])
    registrar_evento(empresa=context.empresa, usuario=context.usuario, request=context.request, objeto=movimiento, modulo="tesoreria", accion=EventoAuditoria.Accion.CREAR, descripcion="Ingreso de tesorería registrado.", datos_nuevos={"referencia_externa": referencia, "origen": origen_tipo, "origen_id": str(origen_id), "monto": str(monto), "correlation_id": context.identificador_solicitud})
    event_bus.publish(MovimientoTesoreriaRegistrado(empresa_id=context.empresa.pk, usuario_id=getattr(context.usuario, "pk", None), agregado_tipo="tesoreria.movimientotesoreria", agregado_id=str(movimiento.pk), referencia=referencia, clave_idempotente=f"movimiento-tesoreria:{clave}", payload={"schema_version":1,"empresa_id":context.empresa.pk,"movimiento_id":movimiento.pk,"origen_tipo":origen_tipo,"origen_id":str(origen_id),"monto":str(monto)}))
    return _dto(movimiento)


def obtener_movimiento(*, empresa, movimiento_id):
    return _dto(MovimientoTesoreria.objects.get(pk=movimiento_id, empresa=empresa))

@transaction.atomic
def revertir_movimiento(*,context,origen_tipo,origen_id,motivo):
    if not motivo:raise ValidationError("El motivo es obligatorio.")
    original=MovimientoTesoreria.objects.select_for_update().get(empresa=context.empresa,tipo="INGRESO",referencia=f"{origen_tipo}:{origen_id}")
    clave=f"REVERSO:{origen_tipo}:{origen_id}"
    existente=MovimientoTesoreria.objects.filter(empresa=context.empresa,referencia=clave).first()
    if existente:return _dto(existente)
    destino=original.cuenta or original.caja
    if destino is None:raise ValidationError("El movimiento no tiene destino reversible.")
    destino.__class__.objects.select_for_update().get(pk=destino.pk,empresa=context.empresa)
    if destino.saldo<original.monto:raise ValidationError("Saldo insuficiente para revertir el movimiento.")
    reverso=MovimientoTesoreria.objects.create(empresa=context.empresa,cuenta=original.cuenta,caja=original.caja,tipo="EGRESO",fecha=original.fecha,monto=original.monto,referencia=clave)
    destino.saldo-=original.monto;destino.save(update_fields=["saldo"])
    if original.conciliado:raise ValidationError("Debe desconciliar el movimiento antes de revertirlo.")
    registrar_evento(empresa=context.empresa,usuario=context.usuario,request=context.request,objeto=reverso,modulo="tesoreria",accion=EventoAuditoria.Accion.OTRO,descripcion="Movimiento de ingreso revertido.",datos_nuevos={"original_id":original.pk,"motivo":motivo})
    event_bus.publish(MovimientoTesoreriaReversado(empresa_id=context.empresa.pk,usuario_id=getattr(context.usuario,"pk",None),agregado_tipo="tesoreria.movimientotesoreria",agregado_id=str(reverso.pk),referencia=clave,clave_idempotente=f"movimiento-reversado:{original.pk}",payload={"schema_version":1,"empresa_id":context.empresa.pk,"movimiento_original_id":original.pk,"movimiento_reverso_id":reverso.pk}))
    return _dto(reverso)


def posicion(*, empresa, fecha=None):
    bancos=[{"tipo":"BANCO","id":x.pk,"cuenta":x.numero_enmascarado,"moneda":x.moneda.moneda.codigo,"saldo":str(x.saldo)} for x in CuentaBancariaEmpresa.objects.filter(empresa=empresa,activa=True).select_related("moneda__moneda")]
    cajas=[{"tipo":"CAJA","id":x.pk,"cuenta":x.codigo,"moneda":x.moneda.moneda.codigo,"saldo":str(x.saldo)} for x in Caja.objects.filter(empresa=empresa).select_related("moneda__moneda")]
    return bancos+cajas


def flujo(*,empresa,desde,hasta):return [{"fecha":str(x.fecha),"tipo":x.tipo,"monto":str(x.monto)} for x in FlujoCajaProyectado.objects.filter(empresa=empresa,fecha__range=(desde,hasta))]
