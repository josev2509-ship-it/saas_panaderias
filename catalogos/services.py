from django.core.exceptions import ValidationError
from django.db import transaction

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento


@transaction.atomic
def guardar_catalogo(*, instancia, empresa, usuario, datos, request=None):
    if instancia.pk:
        instancia = type(instancia).objects.select_for_update().get(pk=instancia.pk, empresa=empresa)
        accion = EventoAuditoria.Accion.EDITAR
    else:
        instancia.empresa = empresa
        instancia.creado_por = usuario
        accion = EventoAuditoria.Accion.CREAR
    for campo, valor in datos.items():
        setattr(instancia, campo, valor)
    if hasattr(instancia, "actualizado_por"):
        instancia.actualizado_por = usuario
    instancia.full_clean()
    instancia.save()
    registrar_evento(
        empresa=empresa, usuario=usuario, request=request, objeto=instancia,
        modulo="catalogos", accion=accion,
        descripcion=f"{instancia._meta.verbose_name.title()} {instancia} guardado.",
    )
    return instancia


@transaction.atomic
def cambiar_actividad(*, model, pk, empresa, usuario, activo, request=None):
    instancia = model.objects.select_for_update().get(pk=pk, empresa=empresa)
    if not hasattr(instancia, "activo"):
        raise ValidationError("Este catálogo no admite cambio de actividad.")
    anterior = instancia.activo
    instancia.activo = activo
    instancia.actualizado_por = usuario
    instancia.full_clean()
    instancia.save(update_fields=["activo", "actualizado_por", "actualizado_en"])
    registrar_evento(
        empresa=empresa, usuario=usuario, request=request, objeto=instancia,
        modulo="catalogos", accion=EventoAuditoria.Accion.CAMBIAR_ESTADO,
        descripcion=f"{instancia}: {'activado' if activo else 'inactivado'}.",
        datos_anteriores={"activo": anterior}, datos_nuevos={"activo": activo},
    )
    return instancia
