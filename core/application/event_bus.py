import logging
from collections import defaultdict

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
            record.save(update_fields=["estado", "intentos"])
        try:
            for handler in self._handlers.get(record.tipo_evento, ()):
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


event_bus = EventBus()
