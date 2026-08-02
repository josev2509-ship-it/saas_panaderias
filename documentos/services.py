from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.models import (
    Cliente, Pedido, ConfiguracionComercialEmpresa, VendedorComercial, RutaComercial,
    PoliticaCredito, PoliticaDescuento, PoliticaEntrega, PoliticaFacturacion,
    PoliticaDevolucion, PoliticaComision,
    Prospecto, OportunidadComercial, ActividadComercial,
    ProductoComercial, ListaPrecio, CotizacionVenta,
    ReservaComercial, PreparacionPedido, TareaPicking, PackingPedido,
    DespachoComercial, ConduceComercial, EntregaComercial, FacturaVenta,
    CuentaPorCobrar, ReciboCobro, CesionFactoring,
)
from inventario.models import OrdenProduccion, PlanProduccion, RecetaProduccion
from compras.models import CategoriaProveedor, CuentaBancariaProveedor, Proveedor, SolicitudCompra, ExpedienteCompra, ProcesoRFQ, InvitacionProveedorRFQ

from .models import Documento, extension_por_contenido

MODELOS_PERMITIDOS = {
    ("comercial", "cliente"): Cliente,
    ("comercial", "pedido"): Pedido,
    ("comercial", "configuracioncomercialempresa"): ConfiguracionComercialEmpresa,
    ("comercial", "vendedorcomercial"): VendedorComercial,
    ("comercial", "rutacomercial"): RutaComercial,
    ("comercial", "politicacredito"): PoliticaCredito,
    ("comercial", "politicadescuento"): PoliticaDescuento,
    ("comercial", "politicaentrega"): PoliticaEntrega,
    ("comercial", "politicafacturacion"): PoliticaFacturacion,
    ("comercial", "politicadevolucion"): PoliticaDevolucion,
    ("comercial", "politicacomision"): PoliticaComision,
    ("comercial", "prospecto"): Prospecto,
    ("comercial", "oportunidadcomercial"): OportunidadComercial,
    ("comercial", "actividadcomercial"): ActividadComercial,
    ("comercial", "productocomercial"): ProductoComercial,
    ("comercial", "listaprecio"): ListaPrecio,
    ("comercial", "cotizacionventa"): CotizacionVenta,
    ("comercial", "reservacomercial"): ReservaComercial,
    ("comercial", "preparacionpedido"): PreparacionPedido,
    ("comercial", "tareapicking"): TareaPicking,
    ("comercial", "packingpedido"): PackingPedido,
    ("comercial", "despachocomercial"): DespachoComercial,
    ("comercial", "conducecomercial"): ConduceComercial,
    ("comercial", "entregacomercial"): EntregaComercial,
    ("comercial", "facturaventa"): FacturaVenta,
    ("comercial", "cuentaporcobrar"): CuentaPorCobrar,
    ("comercial", "recibocobro"): ReciboCobro,
    ("comercial", "cesionfactoring"): CesionFactoring,
    ("inventario", "recetaproduccion"): RecetaProduccion,
    ("inventario", "planproduccion"): PlanProduccion,
    ("inventario", "ordenproduccion"): OrdenProduccion,
    ("compras", "proveedor"): Proveedor,
    ("compras", "categoriaproveedor"): CategoriaProveedor,
    ("compras", "cuentabancariaproveedor"): CuentaBancariaProveedor,
    ("compras", "solicitudcompra"): SolicitudCompra,
    ("compras", "expedientecompra"): ExpedienteCompra,
    ("compras", "procesorfq"): ProcesoRFQ,
    ("compras", "invitacionproveedorrfq"): InvitacionProveedorRFQ,
}

def _emitir_documento_crm(documento,accion,usuario):
    if documento.content_type.app_label!="comercial" or documento.content_type.model not in {"prospecto","oportunidadcomercial","actividadcomercial"}:return
    from comercial.domain.crm_events import DocumentoCRMActualizado
    from core.application.event_bus import event_bus
    event_bus.publish(DocumentoCRMActualizado(empresa_id=documento.empresa_id,usuario_id=getattr(usuario,"pk",None),agregado_tipo=f"comercial.{documento.content_type.model}",agregado_id=str(documento.object_id),referencia=str(documento.pk),clave_idempotente=f"crm-documento:{accion}:{documento.pk}:v{documento.version}",payload={"schema_version":1,"empresa_id":documento.empresa_id,"documento_id":documento.pk,"accion":accion,"version":documento.version}))


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
    from compras.application.expedientes_rfq import registrar_operacion_documental_p2p
    registrar_operacion_documental_p2p(documento=documento,accion="CARGA",usuario=usuario,request=request)
    _emitir_documento_crm(documento,"CARGA",usuario)
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
    from compras.application.expedientes_rfq import registrar_operacion_documental_p2p
    registrar_operacion_documental_p2p(documento=nuevo,accion="REEMPLAZO_VERSION",usuario=usuario,request=request)
    _emitir_documento_crm(nuevo,"REEMPLAZO_VERSION",usuario)
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
    from compras.application.expedientes_rfq import registrar_operacion_documental_p2p
    registrar_operacion_documental_p2p(documento=documento,accion="ANULACION",usuario=usuario,request=request)
    _emitir_documento_crm(documento,"ANULACION",usuario)
    return documento
