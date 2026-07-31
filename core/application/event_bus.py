import logging
from collections import defaultdict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.models import EventoDominio
from core.domain.rules import validate_safe_payload

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._handlers = defaultdict(list)

    def subscribe(self, event_type, handler):
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def clear(self):
        self._handlers.clear()

    def publish(self, event):
        payload = event.serializable_payload()
        validate_safe_payload(payload)
        record, created = EventoDominio.objects.get_or_create(
            empresa_id=event.empresa_id, tipo_evento=event.tipo_evento,
            clave_idempotente=event.clave_idempotente,
            defaults={
                "agregado_tipo": event.agregado_tipo,
                "agregado_id": str(event.agregado_id),
                "referencia": event.referencia,
                "payload": payload,
                "creado_por_id": event.usuario_id,
                "requiere_consumidor": event.requiere_consumidor,
                "categoria": (
                    EventoDominio.Categoria.EJECUTABLE
                    if event.requiere_consumidor
                    else EventoDominio.Categoria.TRAZABILIDAD
                ),
            },
        )
        if created or record.estado == EventoDominio.Estado.ERROR:
            transaction.on_commit(lambda: self.process(record.pk))
        return record

    def process(self, event_id):
        with transaction.atomic():
            record = EventoDominio.objects.select_for_update().get(pk=event_id)
            if record.estado == EventoDominio.Estado.PROCESADO:
                return record
            if record.estado == EventoDominio.Estado.PROCESANDO:
                return record
            record.estado = EventoDominio.Estado.PROCESANDO
            record.intentos += 1
            record.fecha_ultimo_intento = timezone.now()
            record.save(update_fields=["estado", "intentos", "fecha_ultimo_intento"])
        try:
            handlers = self._handlers.get(record.tipo_evento, ())
            if record.requiere_consumidor and not handlers:
                raise RuntimeError("El evento ejecutable no tiene consumidor registrado.")
            for handler in handlers:
                handler(record.payload)
            record.estado = EventoDominio.Estado.PROCESADO
            record.fecha_procesamiento = timezone.now()
            record.ultimo_error = ""
        except Exception as exc:
            logger.exception("Fallo procesando evento de dominio %s", record.pk)
            record.estado = EventoDominio.Estado.ERROR
            record.ultimo_error = str(exc)[:500]
        record.save(update_fields=["estado", "fecha_procesamiento", "ultimo_error"])
        return record

    def retry(self, event_id):
        with transaction.atomic():
            record = EventoDominio.objects.select_for_update().get(pk=event_id)
            if record.estado != EventoDominio.Estado.ERROR:
                return record
            record.estado = EventoDominio.Estado.PENDIENTE
            record.save(update_fields=["estado"])
        return self.process(event_id)

    def process_pending(self, *, empresa=None, limit=None):
        limit = limit or settings.CORE_EVENT_BATCH_SIZE
        queryset = EventoDominio.objects.filter(
            estado__in=[EventoDominio.Estado.PENDIENTE, EventoDominio.Estado.ERROR]
        )
        if empresa is not None:
            queryset = queryset.filter(empresa=empresa)
        processed = []
        for event_id in queryset.order_by("fecha_creacion").values_list("pk", flat=True)[:limit]:
            record = EventoDominio.objects.get(pk=event_id)
            if record.intentos >= settings.CORE_EVENT_MAX_ATTEMPTS:
                record.estado = EventoDominio.Estado.AGOTADO
                record.save(update_fields=["estado"])
                continue
            processed.append(self.process(event_id))
        return processed

    @transaction.atomic
    def recover_stuck(self, *, empresa=None, limit=None):
        limit = limit or settings.CORE_EVENT_BATCH_SIZE
        cutoff = timezone.now() - timezone.timedelta(
            seconds=settings.CORE_EVENT_PROCESSING_TIMEOUT_SECONDS
        )
        queryset = EventoDominio.objects.select_for_update().filter(
            estado=EventoDominio.Estado.PROCESANDO,
            fecha_ultimo_intento__lt=cutoff,
        )
        if empresa is not None:
            queryset = queryset.filter(empresa=empresa)
        records = list(queryset.order_by("fecha_ultimo_intento")[:limit])
        for record in records:
            record.estado = (
                EventoDominio.Estado.AGOTADO
                if record.intentos >= settings.CORE_EVENT_MAX_ATTEMPTS
                else EventoDominio.Estado.ERROR
            )
            record.ultimo_error = "Evento bloqueado recuperado por timeout."
        if records:
            EventoDominio.objects.bulk_update(records, ["estado", "ultimo_error"])
            from auditoria.models import EventoAuditoria
            from auditoria.services import registrar_evento
            for record in records:
                registrar_evento(
                    empresa=record.empresa, modulo="core",
                    accion=EventoAuditoria.Accion.OTRO,
                    descripcion=f"Evento bloqueado {record.pk} recuperado.",
                    objeto=record,
                    datos_anteriores={"estado": EventoDominio.Estado.PROCESANDO},
                    datos_nuevos={
                        "estado": record.estado, "motivo": record.ultimo_error
                    },
                )
        return records


event_bus = EventBus()
