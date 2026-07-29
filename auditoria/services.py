from django.contrib.contenttypes.models import ContentType

from .models import EventoAuditoria


def contexto_request(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]
    return ip or None, user_agent


def registrar_evento(*, empresa, accion, modulo, descripcion, usuario=None,
                     objeto=None, request=None, datos_anteriores=None, datos_nuevos=None):
    ip, user_agent = contexto_request(request) if request else (None, "")
    content_type = ContentType.objects.get_for_model(objeto) if objeto is not None else None
    return EventoAuditoria.objects.create(
        empresa=empresa, usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
        modulo=modulo, accion=accion, descripcion=descripcion,
        content_type=content_type, object_id=getattr(objeto, "pk", None),
        datos_anteriores=datos_anteriores, datos_nuevos=datos_nuevos,
        direccion_ip=ip, user_agent=user_agent,
    )
