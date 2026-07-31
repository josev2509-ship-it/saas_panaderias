from django import template

register = template.Library()

STATUS_TONES = {
    "BORRADOR": "neutral", "INACTIVO": "neutral", "ARCHIVADO": "neutral",
    "PENDIENTE": "progress", "PENDIENTE_APROBACION": "progress",
    "EN_REVISION": "progress", "EN_PREPARACION": "progress",
    "PROCESANDO": "progress", "INICIADA": "progress", "ACTIVA": "info",
    "APROBADO": "success", "APROBADA": "success", "COMPLETADO": "success",
    "COMPLETADA": "success", "ENTREGADO": "success", "COBRADO": "success",
    "PROCESADO": "success", "CONSISTENTE": "success", "CORREGIDA": "success",
    "PARCIAL": "warning", "PROXIMO_A_VENCER": "warning",
    "CON_OBSERVACION": "warning", "RETRASADO": "warning",
    "DIFERENCIA": "warning", "REQUIERE_INTERVENCION": "warning",
    "RECHAZADO": "danger", "VENCIDO": "danger", "CANCELADO": "danger",
    "CANCELADA": "danger", "FALLIDO": "danger", "FALLIDA": "danger",
    "ERROR": "danger", "AGOTADO": "danger", "BLOQUEADO": "danger",
    "ANULADO": "danger",
}


@register.filter
def status_tone(value):
    normalized = str(value or "").strip().upper().replace(" ", "_")
    return STATUS_TONES.get(normalized, "neutral")


@register.filter
def initials(value):
    parts = [part for part in str(value or "").strip().split() if part]
    return "".join(part[0] for part in parts[:2]).upper() or "US"
