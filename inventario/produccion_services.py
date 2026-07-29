from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.models import Pedido
from comercial.pedidos_services import siguiente_numero

from .models import (
    DetallePlanProduccion, HistorialEstadoOrdenProduccion, NecesidadMateriaPrima,
    OrdenProduccion, PlanProduccion, RecetaProduccion,
)

CUATRO = Decimal("0.0001")


def q4(valor):
    return Decimal(valor or 0).quantize(CUATRO, rounding=ROUND_HALF_UP)


def receta_vigente(empresa, producto, fecha):
    return RecetaProduccion.objects.filter(
        empresa=empresa, producto_terminado=producto, activa=True,
        fecha_vigencia_desde__lte=fecha,
    ).filter(
        models.Q(fecha_vigencia_hasta__isnull=True) | models.Q(fecha_vigencia_hasta__gte=fecha)
    ).order_by("-version").first()


def calcular_necesidades(*, cantidad, receta, empresa, plan=None, orden=None, fecha_requerida=None):
    if receta.empresa_id != empresa.pk or cantidad <= 0:
        raise ValidationError("Receta, cantidad o empresa inválida.")
    factor = Decimal(cantidad) / Decimal(receta.rendimiento_base)
    resultado = []
    for ingrediente in receta.ingredientes.select_related("materia_prima"):
        teorica = q4(Decimal(ingrediente.cantidad) * factor)
        merma = Decimal(ingrediente.porcentaje_merma or receta.porcentaje_merma_estimada)
        con_merma = q4(teorica * (Decimal("1") + merma / Decimal("100")))
        estado = (
            NecesidadMateriaPrima.Estado.INSUFICIENTE
            if ingrediente.materia_prima.stock_actual < con_merma
            else NecesidadMateriaPrima.Estado.CALCULADA
        )
        resultado.append(NecesidadMateriaPrima.objects.create(
            empresa=empresa, plan=plan, orden=orden, producto_terminado=receta.producto_terminado,
            materia_prima=ingrediente.materia_prima, cantidad_teorica=teorica,
            unidad_medida=ingrediente.unidad_medida, porcentaje_merma_aplicado=merma,
            cantidad_con_merma=con_merma, fecha_requerida=fecha_requerida or timezone.localdate(),
            estado=estado,
        ))
    return resultado


@transaction.atomic
def duplicar_receta(*, receta, usuario, request=None):
    receta = RecetaProduccion.objects.select_for_update().prefetch_related("ingredientes").get(pk=receta.pk)
    nueva = RecetaProduccion.objects.create(
        empresa=receta.empresa, codigo=f"{receta.codigo}-V{receta.version + 1}",
        nombre=receta.nombre, producto_terminado=receta.producto_terminado,
        version=receta.version + 1, rendimiento_base=receta.rendimiento_base,
        unidad_rendimiento=receta.unidad_rendimiento,
        porcentaje_merma_estimada=receta.porcentaje_merma_estimada,
        tiempo_preparacion_minutos=receta.tiempo_preparacion_minutos,
        tiempo_produccion_minutos=receta.tiempo_produccion_minutos,
        instrucciones=receta.instrucciones, activa=False,
        fecha_vigencia_desde=timezone.localdate(), creado_por=usuario, actualizado_por=usuario,
    )
    for ingrediente in receta.ingredientes.all():
        ingrediente.pk = None
        ingrediente.receta = nueva
        ingrediente.save()
    registrar_evento(
        empresa=receta.empresa, usuario=usuario, request=request, objeto=nueva, modulo="produccion",
        accion=EventoAuditoria.Accion.CREAR, descripcion=f"Se duplicó la receta {receta.codigo} como {nueva.codigo}.",
        datos_nuevos={"receta_origen": receta.pk, "version": nueva.version},
    )
    return nueva


@transaction.atomic
def generar_plan_desde_pedidos(*, empresa, pedidos, fecha_plan, usuario, request=None):
    pedidos = Pedido.objects.filter(pk__in=[p.pk for p in pedidos], empresa=empresa, estado=Pedido.Estado.APROBADO).prefetch_related("detalles__producto")
    if not pedidos.exists():
        raise ValidationError("Selecciona pedidos aprobados de la empresa.")
    plan = PlanProduccion.objects.create(
        empresa=empresa, numero=siguiente_numero(empresa, fecha_plan, "PLA"),
        fecha_plan=fecha_plan, estado=PlanProduccion.Estado.GENERADO,
        origen=PlanProduccion.Origen.PEDIDOS, creado_por=usuario, actualizado_por=usuario,
    )
    creados = 0
    for pedido in pedidos:
        for linea in pedido.detalles.all():
            if DetallePlanProduccion.objects.filter(
                detalle_pedido_origen=linea
            ).exclude(plan__estado=PlanProduccion.Estado.CANCELADO).exists():
                continue
            receta = receta_vigente(empresa, linea.producto, pedido.fecha_entrega)
            detalle = DetallePlanProduccion.objects.create(
                plan=plan, producto_terminado=linea.producto, receta=receta,
                cantidad_solicitada=linea.cantidad, cantidad_planificada=linea.cantidad,
                unidad_medida=linea.unidad_medida, prioridad=pedido.prioridad,
                fecha_requerida=pedido.fecha_entrega, pedido_origen=pedido,
                detalle_pedido_origen=linea,
                observaciones="" if receta else "ADVERTENCIA: producto sin receta vigente.",
            )
            if receta:
                calcular_necesidades(
                    cantidad=detalle.cantidad_planificada, receta=receta, empresa=empresa,
                    plan=plan, fecha_requerida=detalle.fecha_requerida,
                )
            creados += 1
    if not creados:
        raise ValidationError("Las líneas seleccionadas ya fueron planificadas.")
    registrar_evento(
        empresa=empresa, usuario=usuario, request=request, objeto=plan, modulo="produccion",
        accion=EventoAuditoria.Accion.CREAR, descripcion=f"Se generó {plan.numero} desde pedidos aprobados.",
        datos_nuevos={"lineas": creados},
    )
    return plan


@transaction.atomic
def generar_ordenes_desde_plan(*, plan, empresa, usuario, request=None):
    plan = PlanProduccion.objects.select_for_update().prefetch_related("detalles__receta").get(pk=plan.pk, empresa=empresa)
    if plan.estado != PlanProduccion.Estado.APROBADO:
        raise ValidationError("El plan debe estar aprobado.")
    creadas = []
    for detalle in plan.detalles.all():
        if not detalle.receta_id or detalle.ordenes.exists():
            continue
        orden = OrdenProduccion.objects.create(
            empresa=empresa, numero=siguiente_numero(empresa, plan.fecha_plan, "OP"),
            plan=plan, detalle_plan=detalle, producto_terminado=detalle.producto_terminado,
            receta=detalle.receta, fecha_programada=detalle.fecha_requerida,
            prioridad=detalle.prioridad, cantidad_planificada=detalle.cantidad_planificada,
            unidad_medida=detalle.unidad_medida, creado_por=usuario, actualizado_por=usuario,
        )
        calcular_necesidades(
            cantidad=orden.cantidad_planificada, receta=orden.receta, empresa=empresa,
            orden=orden, fecha_requerida=orden.fecha_programada,
        )
        creadas.append(orden)
    if not creadas:
        raise ValidationError("No hay líneas con receta pendientes de generar.")
    registrar_evento(
        empresa=empresa, usuario=usuario, request=request, objeto=plan, modulo="produccion",
        accion=EventoAuditoria.Accion.OTRO, descripcion=f"Se generaron {len(creadas)} órdenes desde {plan.numero}.",
    )
    return creadas


TRANSICIONES = {
    "programar": (OrdenProduccion.Estado.BORRADOR, OrdenProduccion.Estado.PROGRAMADA, "inventario.programar_ordenproduccion"),
    "iniciar": (OrdenProduccion.Estado.PROGRAMADA, OrdenProduccion.Estado.EN_PROCESO, "inventario.iniciar_ordenproduccion"),
    "completar": (OrdenProduccion.Estado.EN_PROCESO, OrdenProduccion.Estado.COMPLETADA, "inventario.completar_ordenproduccion"),
}


@transaction.atomic
def transicionar_orden(*, orden, empresa, usuario, accion, request=None, comentario="", cantidad_iniciada=None, cantidad_producida=None, cantidad_rechazada=None):
    orden = OrdenProduccion.objects.select_for_update().get(pk=orden.pk, empresa=empresa)
    if accion == "cancelar":
        if orden.estado not in {OrdenProduccion.Estado.BORRADOR, OrdenProduccion.Estado.PROGRAMADA}:
            raise ValidationError("La orden no puede cancelarse en su estado actual.")
        origen, destino, permiso = orden.estado, OrdenProduccion.Estado.CANCELADA, "inventario.cancelar_ordenproduccion"
    else:
        if accion not in TRANSICIONES: raise ValidationError("Acción no permitida.")
        origen, destino, permiso = TRANSICIONES[accion]
    if not usuario.has_perm(permiso): raise PermissionDenied
    if orden.estado != origen: raise ValidationError("La orden ya fue procesada o no admite esta transición.")
    ahora = timezone.now()
    if accion == "iniciar":
        if not orden.receta.vigente_en(orden.fecha_programada): raise ValidationError("La receta no está activa y vigente.")
        iniciada = Decimal(cantidad_iniciada or orden.cantidad_planificada)
        if iniciada <= 0: raise ValidationError("La cantidad iniciada debe ser positiva.")
        orden.cantidad_iniciada, orden.fecha_inicio_real = iniciada, ahora
    if accion == "completar":
        producida, rechazada = Decimal(cantidad_producida or 0), Decimal(cantidad_rechazada or 0)
        if producida < 0 or rechazada < 0 or producida + rechazada > orden.cantidad_iniciada:
            raise ValidationError("Las cantidades producidas y rechazadas no son válidas.")
        orden.cantidad_producida, orden.cantidad_rechazada, orden.fecha_fin_real = producida, rechazada, ahora
    orden.estado, orden.actualizado_por = destino, usuario
    orden.save()
    HistorialEstadoOrdenProduccion.objects.create(
        empresa=empresa, orden=orden, estado_anterior=origen, estado_nuevo=destino,
        usuario=usuario, comentario=comentario,
    )
    registrar_evento(
        empresa=empresa, usuario=usuario, request=request, objeto=orden, modulo="produccion",
        accion=EventoAuditoria.Accion.CAMBIAR_ESTADO,
        descripcion=f"Orden {orden.numero}: {orden.get_estado_display()}.",
        datos_anteriores={"estado": origen}, datos_nuevos={"estado": destino},
    )
    return orden


# Import local para evitar contaminar modelos con lógica de consultas.
from django.db import models
