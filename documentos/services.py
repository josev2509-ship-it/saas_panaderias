from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.models import Cliente, Pedido
from inventario.models import OrdenProduccion, PlanProduccion, RecetaProduccion

from .models import Documento, extension_por_contenido

MODELOS_PERMITIDOS = {
    ("comercial", "cliente"): Cliente,
    ("comercial", "pedido"): Pedido,
    ("inventario", "recetaproduccion"): RecetaProduccion,
    ("inventario", "planproduccion"): PlanProduccion,
    ("inventario", "ordenproduccion"): OrdenProduccion,
}


def resolver_objeto_permitido(*, empresa, app_label, model, object_id):
    clase = MODELOS_PERMITIDOS.get((app_label.lower(), model.lower()))
    if clase is None:
        raise ValidationError("El tipo de registro indicado no admite documentos.")
    try:
        return clase.objects.get(pk=object_id, empresa=empresa)
    except clase.DoesNotExist as exc:
        raise ValidationError("El registro indicado no existe o pertenece a otra empresa.") from exc


def validar_empresa_objeto(empresa, objeto):
    if not hasattr(objeto, "empresa_id") or objeto.empresa_id != empresa.pk:
        raise ValidationError("El registro relacionado pertenece a otra empresa.")


def obtener_documentos(objeto, empresa):
    validar_empresa_objeto(empresa, objeto)
    ct = ContentType.objects.get_for_model(objeto)
    return Documento.objects.filter(empresa=empresa, content_type=ct, object_id=objeto.pk)


@transaction.atomic
def crear_documento_asociado(*, empresa, objeto, archivo, usuario=None, request=None, **datos):
    validar_empresa_objeto(empresa, objeto)
    documento = Documento(
        empresa=empresa, content_object=objeto, archivo=archivo, creado_por=usuario,
        nombre_original=Path(archivo.name).name[:255],
        extension=extension_por_contenido(archivo) or "",
        tamano_bytes=archivo.size, **datos,
    )
    documento.full_clean()
    documento.save()
    registrar_evento(
        empresa=empresa, usuario=usuario, request=request, objeto=objeto, modulo="documentos",
        accion=EventoAuditoria.Accion.CARGAR_DOCUMENTO,
        descripcion=f"Se cargó el documento «{documento.titulo}» (v{documento.version}).",
        datos_nuevos={"documento_id": documento.pk, "titulo": documento.titulo, "version": documento.version},
    )
    return documento


@transaction.atomic
def reemplazar_documento(*, documento, archivo, usuario=None, request=None):
    anterior = Documento.objects.select_for_update().get(pk=documento.pk, empresa=documento.empresa)
    if anterior.estado in {Documento.Estado.ANULADO, Documento.Estado.REEMPLAZADO}:
        raise ValidationError("Este documento ya no puede reemplazarse.")
    nuevo = Documento(
        empresa=anterior.empresa, tipo_documento=anterior.tipo_documento,
        titulo=anterior.titulo, descripcion=anterior.descripcion, archivo=archivo,
        nombre_original=Path(archivo.name).name[:255], extension=extension_por_contenido(archivo) or "",
        tamano_bytes=archivo.size, fecha_documento=anterior.fecha_documento,
        fecha_vencimiento=anterior.fecha_vencimiento, confidencial=anterior.confidencial,
        version=anterior.version + 1, documento_anterior=anterior, creado_por=usuario,
        content_type=anterior.content_type, object_id=anterior.object_id,
    )
    nuevo.full_clean()
    nuevo.save()
    anterior.estado = Documento.Estado.REEMPLAZADO
    anterior.save(update_fields=["estado", "fecha_actualizacion"])
    registrar_evento(
        empresa=anterior.empresa, usuario=usuario, request=request, objeto=anterior.content_object,
        modulo="documentos", accion=EventoAuditoria.Accion.REEMPLAZAR_DOCUMENTO,
        descripcion=f"Se reemplazó «{anterior.titulo}»; nueva versión {nuevo.version}.",
        datos_anteriores={"documento_id": anterior.pk, "version": anterior.version},
        datos_nuevos={"documento_id": nuevo.pk, "version": nuevo.version},
    )
    return nuevo


@transaction.atomic
def anular_documento(*, documento, usuario=None, request=None):
    documento = Documento.objects.select_for_update().get(pk=documento.pk, empresa=documento.empresa)
    if documento.estado == Documento.Estado.ANULADO:
        raise ValidationError("El documento ya está anulado.")
    anterior = documento.estado
    documento.estado = Documento.Estado.ANULADO
    documento.save(update_fields=["estado", "fecha_actualizacion"])
    registrar_evento(
        empresa=documento.empresa, usuario=usuario, request=request, objeto=documento.content_object,
        modulo="documentos", accion=EventoAuditoria.Accion.ANULAR_DOCUMENTO,
        descripcion=f"Se anuló el documento «{documento.titulo}» (v{documento.version}).",
        datos_anteriores={"estado": anterior}, datos_nuevos={"estado": documento.estado},
    )
    return documento
