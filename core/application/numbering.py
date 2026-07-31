from django.db import transaction
from django.utils import timezone

from comercial.models import SecuenciaDocumento
from core.domain.rules import format_number
from core.domain.exceptions import InactiveSequenceError
from core.domain.rules import validate_document_length, validate_prefix
from core.application.idempotency import begin, complete, fail
from core.models import RegistroIdempotencia
from core.application.event_bus import event_bus
from core.domain.events import SecuenciaEmitida


def obtener_siguiente_numero(*, empresa, tipo_documento, fecha=None, prefijo=None, longitud=None, usuario=None, context=None):
    if context:
        payload = {
            "tipo_documento": tipo_documento,
            "fecha": str(fecha or timezone.localdate()),
            "prefijo": prefijo,
            "longitud": longitud,
        }
        record, execute = begin(
            context=context, operation="core.emit_document_number", payload=payload
        )
        if not execute and record.estado == RegistroIdempotencia.Estado.COMPLETADA:
            return record.resultado_referencia
        try:
            number = _emit_number(
                empresa=empresa, tipo_documento=tipo_documento, fecha=fecha,
                prefijo=prefijo, longitud=longitud, usuario=usuario,
            )
            complete(record, number)
            return number
        except Exception as exc:
            fail(record, exc)
            raise
    return _emit_number(
        empresa=empresa, tipo_documento=tipo_documento, fecha=fecha,
        prefijo=prefijo, longitud=longitud, usuario=usuario,
    )


@transaction.atomic
def _emit_number(*, empresa, tipo_documento, fecha=None, prefijo=None, longitud=None, usuario=None):
    fecha = fecha or timezone.localdate()
    sequence = SecuenciaDocumento.objects.select_for_update().filter(
        empresa=empresa, tipo=tipo_documento, reinicia_anualmente=False
    ).order_by("-periodo").first()
    if not sequence:
        sequence, _ = SecuenciaDocumento.objects.select_for_update().get_or_create(
            empresa=empresa, tipo=tipo_documento, periodo=fecha.year,
            defaults={"ultimo_numero": 0},
        )
    if not sequence.activo:
        raise InactiveSequenceError("La secuencia documental esta inactiva.")
    effective_prefix = prefijo or sequence.prefijo or tipo_documento
    effective_length = longitud or sequence.longitud
    validate_prefix(effective_prefix)
    validate_document_length(effective_length)
    sequence.ultimo_numero += 1
    sequence.prefijo = sequence.prefijo or effective_prefix
    sequence.fecha_ultima_emision = timezone.now()
    if usuario:
        sequence.actualizado_por = usuario
    sequence.save(update_fields=["ultimo_numero", "prefijo", "fecha_ultima_emision", "actualizado_por", "fecha_actualizacion"])
    emitted = format_number(effective_prefix, fecha.year, sequence.ultimo_numero, effective_length)
    event_bus.publish(SecuenciaEmitida(
        empresa_id=empresa.pk, usuario_id=getattr(usuario, "pk", None),
        agregado_tipo="comercial.SecuenciaDocumento",
        agregado_id=str(sequence.pk), referencia=emitted,
        clave_idempotente=f"secuencia:{sequence.pk}:{sequence.ultimo_numero}",
        payload={"tipo": tipo_documento, "periodo": fecha.year, "numero": emitted},
    ))
    return emitted


def vista_previa_numero(*, empresa, tipo_documento, fecha=None, prefijo=None, longitud=None):
    fecha = fecha or timezone.localdate()
    sequence = SecuenciaDocumento.objects.filter(
        empresa=empresa, tipo=tipo_documento, reinicia_anualmente=False
    ).order_by("-periodo").first() or SecuenciaDocumento.objects.filter(
        empresa=empresa, tipo=tipo_documento, periodo=fecha.year
    ).first()
    current = sequence.ultimo_numero if sequence else 0
    return format_number(
        prefijo or getattr(sequence, "prefijo", "") or tipo_documento,
        fecha.year, current + 1, longitud or getattr(sequence, "longitud", 6),
    )
