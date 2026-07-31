from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.domain.exceptions import IdempotencyConflict
from core.models import RegistroIdempotencia
from core.domain.rules import idempotency_hash


def request_hash(payload):
    return idempotency_hash(payload or {})


@transaction.atomic
def begin(*, context, operation, payload=None, allow_retry=False):
    if not context.clave_idempotente:
        raise IdempotencyConflict("La clave idempotente es obligatoria.")
    digest = request_hash(payload)
    try:
        record, created = RegistroIdempotencia.objects.select_for_update().get_or_create(
            empresa=context.empresa, operacion=operation, clave=context.clave_idempotente,
            defaults={
                "referencia": context.referencia, "hash_solicitud": digest,
                "creado_por": context.usuario if getattr(context.usuario, "is_authenticated", False) else None,
                "metadata": context.metadata,
            },
        )
    except IntegrityError:
        record = RegistroIdempotencia.objects.select_for_update().get(
            empresa=context.empresa, operacion=operation, clave=context.clave_idempotente
        )
        created = False
    if not created and record.hash_solicitud != digest:
        raise IdempotencyConflict("La clave ya fue usada con una solicitud diferente.")
    if not created and record.estado == RegistroIdempotencia.Estado.FALLIDA and allow_retry:
        if record.intentos >= settings.CORE_IDEMPOTENCY_MAX_RETRIES:
            raise IdempotencyConflict("La operacion alcanzo el maximo de reintentos.")
        record.estado = RegistroIdempotencia.Estado.INICIADA
        record.intentos += 1
        record.mensaje_error = ""
        record.fecha_finalizacion = None
        record.save(update_fields=["estado", "mensaje_error", "fecha_finalizacion", "intentos"])
        return record, True
    if not created and record.estado == RegistroIdempotencia.Estado.INICIADA:
        raise IdempotencyConflict("La operacion ya se encuentra en proceso.")
    return record, created


def complete(record, result_reference="", metadata=None):
    record.estado = RegistroIdempotencia.Estado.COMPLETADA
    record.resultado_referencia = str(result_reference or "")
    record.fecha_finalizacion = timezone.now()
    if metadata is not None:
        record.metadata = metadata
    record.save(update_fields=["estado", "resultado_referencia", "fecha_finalizacion", "metadata"])
    return record


def fail(record, error):
    record.estado = RegistroIdempotencia.Estado.FALLIDA
    record.mensaje_error = str(error)[:500]
    record.fecha_finalizacion = timezone.now()
    record.save(update_fields=["estado", "mensaje_error", "fecha_finalizacion"])
    return record


iniciar_operacion_idempotente = begin
completar_operacion_idempotente = complete
fallar_operacion_idempotente = fail


def obtener_resultado_idempotente(*, context, operation, payload=None):
    record, execute = begin(context=context, operation=operation, payload=payload)
    return record, execute


def reintentar_operacion_fallida(*, context, operation, payload=None):
    return begin(
        context=context, operation=operation, payload=payload, allow_retry=True
    )


@transaction.atomic
def recover_stale(*, empresa=None, usuario=None, limit=100):
    cutoff = timezone.now() - timezone.timedelta(
        seconds=settings.CORE_IDEMPOTENCY_STALE_SECONDS
    )
    queryset = RegistroIdempotencia.objects.select_for_update().filter(
        estado=RegistroIdempotencia.Estado.INICIADA,
        fecha_inicio__lt=cutoff,
    )
    if empresa is not None:
        queryset = queryset.filter(empresa=empresa)
    records = list(queryset.order_by("fecha_inicio")[:limit])
    now = timezone.now()
    for record in records:
        record.estado = RegistroIdempotencia.Estado.FALLIDA
        record.fecha_finalizacion = now
        record.mensaje_error = "Operacion abandonada recuperada por timeout."
    if records:
        RegistroIdempotencia.objects.bulk_update(
            records, ["estado", "fecha_finalizacion", "mensaje_error"]
        )
        from auditoria.models import EventoAuditoria
        from auditoria.services import registrar_evento
        for record in records:
            registrar_evento(
                empresa=record.empresa, usuario=usuario, modulo="core",
                accion=EventoAuditoria.Accion.OTRO,
                descripcion=f"Idempotencia abandonada {record.pk} recuperada.",
                objeto=record,
                datos_anteriores={"estado": RegistroIdempotencia.Estado.INICIADA},
                datos_nuevos={
                    "estado": record.estado,
                    "motivo": record.mensaje_error,
                },
            )
    return records
