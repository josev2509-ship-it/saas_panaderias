from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento

SENSITIVE_KEYS = {"password", "contraseña", "token", "secret", "authorization", "archivo"}


def _safe(value):
    if isinstance(value, dict):
        return {key: _safe(item) for key, item in value.items() if key.lower() not in SENSITIVE_KEYS}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    if hasattr(value, "_meta") or hasattr(value, "read"):
        return "[valor protegido]"
    return value


def audit(*, context, module, action, description, obj=None, before=None, after=None):
    return registrar_evento(
        empresa=context.empresa, usuario=context.usuario, request=context.request,
        objeto=obj, modulo=module, accion=action, descripcion=description,
        datos_anteriores=_safe(before), datos_nuevos=_safe(after),
    )


def audit_create(**kwargs):
    return audit(action=EventoAuditoria.Accion.CREAR, **kwargs)


def audit_update(**kwargs):
    return audit(action=EventoAuditoria.Accion.EDITAR, **kwargs)


def audit_transition(**kwargs):
    return audit(action=EventoAuditoria.Accion.CAMBIAR_ESTADO, **kwargs)


def audit_inventory_movement(**kwargs):
    return audit(action=EventoAuditoria.Accion.OTRO, **kwargs)


def audit_reversal(**kwargs):
    return audit(action=EventoAuditoria.Accion.OTRO, **kwargs)


def audit_security_event(**kwargs):
    return audit(action=EventoAuditoria.Accion.OTRO, **kwargs)


audit_reconciliation = audit_update
audit_idempotency_conflict = audit_security_event
audit_numbering = audit_update
audit_event_retry = audit_update
