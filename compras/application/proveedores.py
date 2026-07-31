from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from core.application.event_bus import event_bus
from core.application.numbering import obtener_siguiente_numero
from compras.domain.events import (
    ContactoProveedorCreado, CorrespondenciaProveedorLegadoCreada,
    CuentaBancariaProveedorRegistrada, CuentaBancariaProveedorVerificada,
    DireccionProveedorCreada, ProductoProveedorVinculado, ProveedorActivado,
    ProveedorActualizado, ProveedorBloqueado, ProveedorCreado,
    ProveedorInactivado, ProveedorReactivado, ProveedorSuspendido,
)
from compras.domain.states import puede_transicionar
from compras.models import (
    ContactoProveedor, CuentaBancariaProveedor, DireccionProveedor,
    HistorialEstadoProveedor, ProductoProveedor, Proveedor, ProveedorLegadoMap,
    RequisitoDocumentoProveedor,
)


EVENTOS_ESTADO = {
    Proveedor.Estado.ACTIVO: ProveedorActivado,
    Proveedor.Estado.SUSPENDIDO: ProveedorSuspendido,
    Proveedor.Estado.BLOQUEADO: ProveedorBloqueado,
    Proveedor.Estado.INACTIVO: ProveedorInactivado,
}


def _perm(context, codename):
    user = context.usuario
    if not user or not user.has_perm(f"compras.{codename}"):
        raise PermissionDenied(f"Se requiere el permiso compras.{codename}.")


def _audit(context, objeto, accion, descripcion, antes=None, despues=None):
    registrar_evento(
        empresa=context.empresa, usuario=context.usuario, request=context.request,
        objeto=objeto, modulo="compras", accion=accion, descripcion=descripcion,
        datos_anteriores=antes, datos_nuevos=despues,
    )


def _event(context, cls, proveedor, suffix, payload=None):
    safe = {"empresa_id": context.empresa.pk, "proveedor_id": proveedor.pk,
            "codigo": proveedor.codigo, "schema_version": 1, **(payload or {})}
    event_bus.publish(cls(
        empresa_id=context.empresa.pk, usuario_id=getattr(context.usuario, "pk", None),
        agregado_tipo="compras.Proveedor", agregado_id=str(proveedor.pk),
        referencia=context.referencia, clave_idempotente=(
            context.clave_idempotente or f"compras:{suffix}:{proveedor.pk}:{timezone.now().timestamp()}"
        ), payload=safe,
    ))


@transaction.atomic
def crear_proveedor(*, context, datos):
    _perm(context, "add_proveedor")
    data = dict(datos)
    data.pop("estado", None)
    if not data.get("codigo"):
        data["codigo"] = obtener_siguiente_numero(
            empresa=context.empresa, tipo_documento="PROV", prefijo="PROV",
            usuario=context.usuario,
        )
    proveedor = Proveedor(empresa=context.empresa, creado_por=context.usuario,
                          actualizado_por=context.usuario, **data)
    proveedor.full_clean()
    proveedor.save()
    _audit(context, proveedor, EventoAuditoria.Accion.CREAR, "Proveedor canónico creado.",
           despues={"codigo": proveedor.codigo, "estado": proveedor.estado})
    _event(context, ProveedorCreado, proveedor, "crear")
    return proveedor


@transaction.atomic
def actualizar_proveedor(*, context, proveedor_id, datos):
    _perm(context, "change_proveedor")
    proveedor = Proveedor.objects.select_for_update().get(pk=proveedor_id, empresa=context.empresa)
    antes = {k: str(getattr(proveedor, k, "")) for k in datos if k != "estado"}
    for campo, valor in datos.items():
        if campo not in {"estado", "bloqueado", "fecha_bloqueo", "bloqueado_por"}:
            setattr(proveedor, campo, valor)
    proveedor.actualizado_por = context.usuario
    proveedor.full_clean()
    proveedor.save()
    _audit(context, proveedor, EventoAuditoria.Accion.EDITAR, "Proveedor actualizado.", antes,
           {k: str(getattr(proveedor, k, "")) for k in antes})
    _event(context, ProveedorActualizado, proveedor, "actualizar")
    return proveedor


@transaction.atomic
def _transicionar(*, context, proveedor_id, hacia, motivo, permiso):
    _perm(context, permiso)
    proveedor = Proveedor.objects.select_for_update().get(pk=proveedor_id, empresa=context.empresa)
    anterior = proveedor.estado
    if not puede_transicionar(anterior, hacia):
        raise ValidationError(f"No se permite la transición {anterior} → {hacia}.")
    if not motivo.strip():
        raise ValidationError("El motivo es obligatorio.")
    if hacia == Proveedor.Estado.ACTIVO and anterior == Proveedor.Estado.EN_EVALUACION:
        if not proveedor.direcciones.filter(tipo="FISCAL", activa=True).exists():
            raise ValidationError("Se requiere una dirección fiscal activa.")
        if not proveedor.documentacion_completa:
            raise ValidationError("La documentación obligatoria no está completa.")
    proveedor.estado = hacia
    if hacia == Proveedor.Estado.BLOQUEADO:
        proveedor.bloqueado=True; proveedor.motivo_bloqueo=motivo
        proveedor.fecha_bloqueo=timezone.now(); proveedor.bloqueado_por=context.usuario
    elif hacia == Proveedor.Estado.ACTIVO:
        proveedor.bloqueado=False; proveedor.motivo_bloqueo=""
        proveedor.fecha_bloqueo=None; proveedor.bloqueado_por=None
    if hacia == Proveedor.Estado.INACTIVO:
        proveedor.es_preferido = False
    proveedor.actualizado_por=context.usuario
    proveedor.full_clean(); proveedor.save()
    HistorialEstadoProveedor.objects.create(
        empresa=context.empresa, proveedor=proveedor, estado_anterior=anterior,
        estado_nuevo=hacia, motivo=motivo, usuario=context.usuario,
    )
    _audit(context, proveedor, EventoAuditoria.Accion.CAMBIAR_ESTADO,
           f"Estado de proveedor: {anterior} → {hacia}.",
           {"estado": anterior}, {"estado": hacia, "motivo": motivo})
    cls = ProveedorReactivado if hacia == Proveedor.Estado.ACTIVO and anterior != Proveedor.Estado.EN_EVALUACION else EVENTOS_ESTADO[hacia]
    _event(context, cls, proveedor, hacia.lower(), {"estado_anterior": anterior, "estado_nuevo": hacia, "motivo": motivo})
    return proveedor


def activar_proveedor(*, context, proveedor_id, motivo): return _transicionar(context=context, proveedor_id=proveedor_id, hacia="ACTIVO", motivo=motivo, permiso="activar_proveedor")
def suspender_proveedor(*, context, proveedor_id, motivo): return _transicionar(context=context, proveedor_id=proveedor_id, hacia="SUSPENDIDO", motivo=motivo, permiso="suspender_proveedor")
def bloquear_proveedor(*, context, proveedor_id, motivo): return _transicionar(context=context, proveedor_id=proveedor_id, hacia="BLOQUEADO", motivo=motivo, permiso="bloquear_proveedor")
def reactivar_proveedor(*, context, proveedor_id, motivo): return _transicionar(context=context, proveedor_id=proveedor_id, hacia="ACTIVO", motivo=motivo, permiso="reactivar_proveedor")
def inactivar_proveedor(*, context, proveedor_id, motivo): return _transicionar(context=context, proveedor_id=proveedor_id, hacia="INACTIVO", motivo=motivo, permiso="inactivar_proveedor")


def _crear_relacion(*, context, model, permiso, event, datos):
    _perm(context, permiso)
    proveedor = datos["proveedor"]
    if proveedor.empresa_id != context.empresa.pk:
        raise ValidationError("El proveedor pertenece a otra empresa.")
    obj = model(empresa=context.empresa, creado_por=context.usuario, actualizado_por=context.usuario, **datos)
    if isinstance(obj, CuentaBancariaProveedor):
        obj.set_numero(datos["numero_cuenta"])
    obj.full_clean(); obj.save()
    _audit(context, obj, EventoAuditoria.Accion.CREAR, f"{model._meta.verbose_name} creado.",
           despues={"id": obj.pk, "proveedor_id": proveedor.pk})
    _event(context, event, proveedor, f"{model._meta.model_name}:{obj.pk}", {"relacion_id": obj.pk})
    return obj


@transaction.atomic
def crear_contacto_proveedor(*, context, datos): return _crear_relacion(context=context,model=ContactoProveedor,permiso="add_contactoproveedor",event=ContactoProveedorCreado,datos=datos)
@transaction.atomic
def actualizar_contacto_proveedor(*, context, contacto_id, datos):
    _perm(context, "change_contactoproveedor")
    contacto=ContactoProveedor.objects.select_for_update().get(pk=contacto_id,empresa=context.empresa)
    for campo,valor in datos.items():
        if campo not in {"empresa","proveedor","creado_por"}: setattr(contacto,campo,valor)
    contacto.actualizado_por=context.usuario
    contacto.full_clean(); contacto.save()
    _audit(context,contacto,EventoAuditoria.Accion.EDITAR,"Contacto de proveedor actualizado.",despues={"contacto_id":contacto.pk})
    return contacto
@transaction.atomic
def crear_direccion_proveedor(*, context, datos): return _crear_relacion(context=context,model=DireccionProveedor,permiso="add_direccionproveedor",event=DireccionProveedorCreada,datos=datos)
@transaction.atomic
def vincular_producto_proveedor(*, context, datos): return _crear_relacion(context=context,model=ProductoProveedor,permiso="add_productoproveedor",event=ProductoProveedorVinculado,datos=datos)
@transaction.atomic
def registrar_cuenta_bancaria(*, context, datos): return _crear_relacion(context=context,model=CuentaBancariaProveedor,permiso="add_cuentabancariaproveedor",event=CuentaBancariaProveedorRegistrada,datos=datos)


@transaction.atomic
def _principal(*, context, model, pk, filtro, permiso):
    _perm(context, permiso)
    obj=model.objects.select_for_update().get(pk=pk,empresa=context.empresa)
    model.objects.filter(empresa=context.empresa, **filtro).exclude(pk=pk).update(principal=False)
    obj.principal=True; obj.actualizado_por=context.usuario; obj.save(update_fields=["principal","actualizado_por","fecha_actualizacion"])
    return obj


def establecer_contacto_principal(*,context,contacto_id):
    obj=ContactoProveedor.objects.get(pk=contacto_id,empresa=context.empresa)
    return _principal(context=context,model=ContactoProveedor,pk=contacto_id,filtro={"proveedor":obj.proveedor,"activo":True},permiso="change_contactoproveedor")
def establecer_direccion_principal(*,context,direccion_id):
    obj=DireccionProveedor.objects.get(pk=direccion_id,empresa=context.empresa)
    return _principal(context=context,model=DireccionProveedor,pk=direccion_id,filtro={"proveedor":obj.proveedor,"tipo":obj.tipo,"activa":True},permiso="change_direccionproveedor")
def establecer_proveedor_preferido(*,context,producto_proveedor_id):
    _perm(context,"establecer_proveedor_preferido")
    with transaction.atomic():
        obj=ProductoProveedor.objects.select_for_update().get(pk=producto_proveedor_id,empresa=context.empresa)
        ProductoProveedor.objects.filter(empresa=context.empresa,producto=obj.producto,activo=True).exclude(pk=obj.pk).update(preferido=False)
        obj.preferido=True; obj.actualizado_por=context.usuario
        obj.save(update_fields=["preferido","actualizado_por","fecha_actualizacion"])
        _audit(context,obj,EventoAuditoria.Accion.EDITAR,"Proveedor preferido establecido.",despues={"producto_id":obj.producto_id,"proveedor_id":obj.proveedor_id})
        return obj


@transaction.atomic
def verificar_cuenta_bancaria(*,context,cuenta_id):
    _perm(context,"verificar_cuenta_bancaria")
    cuenta=CuentaBancariaProveedor.objects.select_for_update().get(pk=cuenta_id,empresa=context.empresa)
    cuenta.estado="VERIFICADA"; cuenta.verificada=True; cuenta.fecha_verificacion=timezone.now(); cuenta.verificada_por=context.usuario
    cuenta.save(update_fields=["estado","verificada","fecha_verificacion","verificada_por","fecha_actualizacion"])
    _audit(context,cuenta,EventoAuditoria.Accion.CAMBIAR_ESTADO,"Cuenta bancaria verificada.",despues={"estado":"VERIFICADA"})
    _event(context,CuentaBancariaProveedorVerificada,cuenta.proveedor,f"cuenta-verificada:{cuenta.pk}",{"cuenta_id":cuenta.pk})
    return cuenta


@transaction.atomic
def rechazar_cuenta_bancaria(*,context,cuenta_id,motivo):
    _perm(context,"verificar_cuenta_bancaria")
    if not motivo.strip(): raise ValidationError("El motivo es obligatorio.")
    cuenta=CuentaBancariaProveedor.objects.select_for_update().get(pk=cuenta_id,empresa=context.empresa)
    cuenta.estado="RECHAZADA"; cuenta.verificada=False; cuenta.motivo_rechazo=motivo
    cuenta.save(update_fields=["estado","verificada","motivo_rechazo","fecha_actualizacion"])
    return cuenta


@transaction.atomic
def vincular_proveedor_legado(*,context,datos):
    _perm(context,"gestionar_correspondencia_proveedor")
    obj=ProveedorLegadoMap(empresa=context.empresa,creado_por=context.usuario,actualizado_por=context.usuario,**datos)
    obj.full_clean(); obj.save()
    _audit(context,obj,EventoAuditoria.Accion.CREAR,"Correspondencia con proveedor legado creada.",despues={"legacy_id":obj.proveedor_legacy_id,"proveedor_id":obj.proveedor_nuevo_id})
    _event(context,CorrespondenciaProveedorLegadoCreada,obj.proveedor_nuevo,f"legado:{obj.pk}",{"correspondencia_id":obj.pk,"legacy_id":obj.proveedor_legacy_id})
    return obj


@transaction.atomic
def recalcular_estado_documental(*,context,proveedor_id):
    proveedor=Proveedor.objects.select_for_update().get(pk=proveedor_id,empresa=context.empresa)
    requisitos=RequisitoDocumentoProveedor.objects.filter(empresa=context.empresa,categoria=proveedor.categoria,activo=True,obligatorio=True)
    from documentos.services import obtener_documentos
    docs=obtener_documentos(proveedor,context.empresa).filter(estado="ACTIVO")
    tipos=set(docs.values_list("tipo_documento_id",flat=True))
    proveedor.documentacion_completa=all(r.tipo_documento_id in tipos for r in requisitos)
    proveedor.fecha_ultima_revision_documental=timezone.localdate()
    proveedor.save(update_fields=["documentacion_completa","fecha_ultima_revision_documental","fecha_actualizacion"])
    return proveedor
