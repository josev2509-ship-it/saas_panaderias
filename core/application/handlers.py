from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from conduces.models import Empresa
from django.contrib.auth import get_user_model

from .event_bus import event_bus


def registrar_seguimiento_tecnico(payload):
    """Consumer productivo: deja seguimiento auditable de acciones ejecutables."""
    empresa = Empresa.objects.get(pk=payload["empresa_id"])
    usuario = get_user_model().objects.filter(pk=payload.get("usuario_id")).first()
    registrar_evento(
        empresa=empresa,
        usuario=usuario,
        modulo="core",
        accion=EventoAuditoria.Accion.OTRO,
        descripcion=f"Evento tecnico procesado: {payload.get('agregado_tipo')}.",
        datos_nuevos={
            "agregado_id": payload.get("agregado_id"),
            "referencia": payload.get("referencia"),
        },
    )


def register_handlers():
    event_bus.subscribe("SaldoReconstruido", registrar_seguimiento_tecnico)
