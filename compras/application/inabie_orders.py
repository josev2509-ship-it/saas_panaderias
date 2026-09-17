"""Borradores Enterprise originados en programación escolar confirmada."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from catalogos.models import MonedaEmpresa
from compras.models import DetalleOrdenCompraEnterprise, OrdenCompraEnterprise, Proveedor
from conduces.models import Empresa
from core.application.numbering import obtener_siguiente_numero
from inventario.models import ProductoInventario
from inventario.proyeccion_menu_escolar import proyectar_necesidades_menu_escolar
from .p2p import _audit


PRECISION = Decimal("0.0001")
CENTAVO = Decimal("0.01")


def _exigir_permiso(context, permiso):
    if not context.usuario or not context.usuario.has_perm(f"compras.{permiso}"):
        raise PermissionDenied


def _borrador(context, orden_id):
    orden = OrdenCompraEnterprise.objects.select_for_update().get(
        pk=orden_id, empresa=context.empresa, origen="INABIE"
    )
    if orden.estado != "BORRADOR":
        raise ValidationError("Solo se puede editar una orden INABIE en borrador.")
    return orden


def _cantidad(valor, *, cero=True):
    try:
        cantidad = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("Indique una cantidad decimal válida.")
    if not cantidad.is_finite() or cantidad < 0 or (not cero and cantidad == 0):
        raise ValidationError("La cantidad debe ser positiva.")
    if cantidad.as_tuple().exponent < -4:
        raise ValidationError("La cantidad admite hasta cuatro decimales.")
    return cantidad


def _recalcular(orden):
    total = orden.detalles.aggregate(s=Sum("total"))["s"] or Decimal("0")
    orden.subtotal = total
    orden.total = total
    orden.save(update_fields=["subtotal", "total", "fecha_actualizacion"])


@transaction.atomic
def generar_borrador_inabie(*, context, desde, hasta):
    _exigir_permiso(context, "add_ordencompraenterprise")
    if desde > hasta:
        raise ValidationError("La fecha inicial no puede superar la final.")
    # Serializa generaciones concurrentes por empresa en PostgreSQL; la
    # restricción única del período sigue protegiendo SQLite y la base de datos.
    Empresa.objects.select_for_update().get(pk=context.empresa.pk)
    existente = OrdenCompraEnterprise.objects.filter(
        empresa=context.empresa, origen="INABIE", periodo_desde=desde, periodo_hasta=hasta,
    ).first()
    if existente:
        return existente, False
    moneda = MonedaEmpresa.objects.filter(
        empresa=context.empresa, activa=True, es_base=True,
    ).first()
    if moneda is None:
        raise ValidationError("Configure una moneda base activa para la empresa antes de generar la orden.")
    proyeccion = proyectar_necesidades_menu_escolar(
        empresa=context.empresa, desde=desde, hasta=hasta,
    )
    if not proyeccion.necesidades:
        raise ValidationError("No hay ingredientes calculables en la programación confirmada del período.")
    orden = OrdenCompraEnterprise.objects.create(
        empresa=context.empresa,
        numero=obtener_siguiente_numero(
            empresa=context.empresa, tipo_documento="OCE", usuario=context.usuario, context=context,
        ),
        proveedor=None, moneda=moneda, fecha=timezone.localdate(),
        entrega_desde=desde, entrega_hasta=hasta, periodo_desde=desde, periodo_hasta=hasta,
        origen="INABIE", estado="BORRADOR",
        dimensiones={"origen": "INABIE", "advertencias": proyeccion.advertencias},
        creado_por=context.usuario, actualizado_por=context.usuario,
    )
    for necesidad in proyeccion.necesidades.values():
        producto = necesidad.ingrediente
        cantidad = Decimal(necesidad.empaques)
        precio = Decimal(producto.precio_unitario_compra or 0)
        DetalleOrdenCompraEnterprise.objects.create(
            orden=orden, producto=producto, descripcion=producto.nombre,
            cantidad=cantidad, precio_unitario=precio,
            total=(cantidad * precio).quantize(CENTAVO, rounding=ROUND_HALF_UP),
            origen="INABIE",
            necesidad_base=necesidad.bruta.quantize(PRECISION, rounding=ROUND_HALF_UP),
            disponible_base=necesidad.disponible.quantize(PRECISION, rounding=ROUND_HALF_UP),
            sugerido_base=necesidad.neta.quantize(PRECISION, rounding=ROUND_HALF_UP),
            empaques_sugeridos=necesidad.empaques,
            cantidad_por_empaque=producto.cantidad_por_empaque,
            traza=[{
                "fecha": str(t.fecha), "centro_id": t.centro_id,
                "matricula": t.matricula, "tipo_matricula": t.tipo_matricula,
                "producto": t.producto_programado, "receta_id": t.receta_id,
                "rendimiento": str(t.rendimiento), "factor": str(t.factor),
                "ingrediente_id": t.ingrediente_id, "cantidad": str(t.cantidad),
            } for t in necesidad.trazas],
        )
    _recalcular(orden)
    _audit(context, orden, "Borrador INABIE creado desde programación confirmada.",
           after={"desde": str(desde), "hasta": str(hasta), "lineas": len(proyeccion.necesidades)})
    return orden, True


@transaction.atomic
def editar_borrador_inabie(*, context, orden_id, proveedor_id=None, observaciones=None):
    _exigir_permiso(context, "change_ordencompraenterprise")
    orden = _borrador(context, orden_id)
    if proveedor_id is not None:
        orden.proveedor = (Proveedor.objects.get(pk=proveedor_id, empresa=context.empresa,
                           estado="ACTIVO", bloqueado=False) if proveedor_id else None)
    if observaciones is not None:
        orden.observaciones = observaciones
    orden.actualizado_por = context.usuario
    orden.save(update_fields=["proveedor", "observaciones", "actualizado_por", "fecha_actualizacion"])
    _audit(context, orden, "Borrador INABIE editado.")
    return orden


@transaction.atomic
def editar_linea_inabie(*, context, orden_id, linea_id, cantidad):
    _exigir_permiso(context, "change_ordencompraenterprise")
    orden = _borrador(context, orden_id)
    linea = DetalleOrdenCompraEnterprise.objects.select_for_update().get(
        pk=linea_id, orden=orden,
    )
    linea.cantidad = _cantidad(cantidad)
    linea.total = (linea.cantidad * linea.precio_unitario).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    linea.save(update_fields=["cantidad", "total"])
    _recalcular(orden)
    _audit(context, orden, "Cantidad del borrador INABIE actualizada.", after={"linea_id": linea.pk})
    return linea


@transaction.atomic
def eliminar_linea_inabie(*, context, orden_id, linea_id):
    _exigir_permiso(context, "change_ordencompraenterprise")
    orden = _borrador(context, orden_id)
    linea = DetalleOrdenCompraEnterprise.objects.get(pk=linea_id, orden=orden)
    linea.delete()
    _recalcular(orden)
    _audit(context, orden, "Línea retirada del borrador INABIE.", after={"linea_id": linea_id})


@transaction.atomic
def agregar_linea_inabie(*, context, orden_id, producto_id, cantidad):
    _exigir_permiso(context, "change_ordencompraenterprise")
    orden = _borrador(context, orden_id)
    producto = ProductoInventario.objects.get(pk=producto_id, empresa=context.empresa, activo=True)
    cantidad = _cantidad(cantidad)
    precio = Decimal(producto.precio_unitario_compra or 0)
    linea = DetalleOrdenCompraEnterprise.objects.create(
        orden=orden, producto=producto, descripcion=producto.nombre,
        origen="MANUAL", cantidad=cantidad, precio_unitario=precio,
        cantidad_por_empaque=producto.cantidad_por_empaque,
        total=(cantidad * precio).quantize(CENTAVO, rounding=ROUND_HALF_UP),
    )
    _recalcular(orden)
    _audit(context, orden, "Línea manual añadida al borrador INABIE.", after={"linea_id": linea.pk})
    return linea
