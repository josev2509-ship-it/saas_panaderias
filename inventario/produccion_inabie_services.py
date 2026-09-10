from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.pedidos_services import siguiente_numero
from conduces.models import CentroEducativo, DiaNoDocencia, MenuDiario, PerfilUsuario

from .models import (
    AjusteOrdenProduccion, AlertaAbastecimiento, ConfiguracionProduccion,
    ConsumoRealProduccion, HistorialEstadoOrdenProduccion, NecesidadMateriaPrima, OrdenProduccion,
    ProductoInventario, RecetaProduccion, MatriculaCentroVigente,
    SolicitudCambioProducto, VinculoProductoMenu,
)
from .compras_projection import entradas_confirmadas
from .produccion_services import calcular_necesidades, q4


def _puede(usuario, permiso):
    return usuario.has_perm(permiso) or PerfilUsuario.objects.filter(
        user=usuario, activo=True, rol="admin_empresa"
    ).exists()


def es_dia_productivo(empresa, fecha, modalidad="REGULAR"):
    if DiaNoDocencia.objects.filter(empresa=empresa, fecha=fecha, activo=True).exists():
        return False
    return fecha.weekday() < 5 if modalidad == "REGULAR" else fecha.weekday() >= 5


def resolver_fecha_entrega(empresa, fecha_produccion, modalidad="REGULAR"):
    fecha = fecha_produccion + timedelta(days=1)
    for _ in range(370):
        if es_dia_productivo(empresa, fecha, modalidad):
            return fecha
        fecha += timedelta(days=1)
    raise ValidationError("No se encontró un día de entrega válido en el calendario.")


def receta_vigente(empresa, producto, fecha):
    return RecetaProduccion.objects.filter(
        empresa=empresa, producto_terminado=producto, activa=True,
        fecha_vigencia_desde__lte=fecha,
    ).filter(
        models.Q(fecha_vigencia_hasta__isnull=True) | models.Q(fecha_vigencia_hasta__gte=fecha)
    ).order_by("-version").first()


def resolver_producto_menu(empresa, menu):
    vinculo=VinculoProductoMenu.objects.filter(empresa=empresa, menu=menu).select_related("producto").first()
    if vinculo:
        return vinculo.producto
    producto=ProductoInventario.objects.filter(empresa=empresa, activo=True, tipo="producto_terminado", nombre__iexact=menu.producto.strip()).first()
    if producto:
        VinculoProductoMenu.objects.get_or_create(empresa=empresa, menu=menu, defaults={"producto":producto, "revisado":False})
    return producto


def total_raciones(empresa, fecha=None, modalidad="REGULAR", programa="INABIE"):
    fecha=fecha or timezone.localdate(); total=0
    for centro in CentroEducativo.objects.filter(empresa=empresa):
        vigente=MatriculaCentroVigente.objects.filter(empresa=empresa, centro=centro, programa=programa, modalidad=modalidad, fecha_desde__lte=fecha).filter(models.Q(fecha_hasta__isnull=True)|models.Q(fecha_hasta__gte=fecha)).order_by("-fecha_desde").first()
        total += vigente.raciones if vigente else centro.matricula
    return Decimal(total)


@transaction.atomic
def generar_orden_inabie(*, empresa, fecha_produccion, modalidad, usuario, request=None, fecha_entrega=None):
    fecha_entrega = fecha_entrega or resolver_fecha_entrega(empresa, fecha_produccion, modalidad)
    menu = MenuDiario.objects.select_for_update().get(empresa=empresa, fecha=fecha_entrega)
    producto = resolver_producto_menu(empresa, menu)
    if not producto:
        raise ValidationError("El producto del menú no está vinculado al inventario de esta empresa.")
    receta = receta_vigente(empresa, producto, fecha_entrega)
    if not receta:
        raise ValidationError("No existe receta vigente para el producto del menú.")
    raciones = total_raciones(empresa, fecha_entrega, modalidad)
    if raciones <= 0:
        raise ValidationError("La matrícula total debe ser mayor que cero.")
    orden = OrdenProduccion.objects.create(
        empresa=empresa, numero=siguiente_numero(empresa, fecha_produccion, "OP"),
        fecha_programada=fecha_produccion, fecha_entrega=fecha_entrega, modalidad=modalidad,
        producto_planificado=producto, producto_terminado=producto, receta=receta,
        raciones_matricula=raciones, cantidad_sugerida=raciones, cantidad_autorizada=raciones,
        cantidad_planificada=raciones, unidad_medida=receta.unidad_rendimiento,
        creado_por=usuario, actualizado_por=usuario,
    )
    calcular_necesidades(cantidad=raciones, receta=receta, empresa=empresa, orden=orden, fecha_requerida=fecha_produccion)
    registrar_evento(empresa=empresa, usuario=usuario, request=request, objeto=orden, modulo="produccion", accion=EventoAuditoria.Accion.CREAR, descripcion=f"Se generó la orden INABIE {orden.numero}.")
    return orden


@transaction.atomic
def ajustar_cantidad(*, orden, empresa, usuario, cantidad, motivo, justificacion, request=None):
    orden = OrdenProduccion.objects.select_for_update().get(pk=orden.pk, empresa=empresa)
    if orden.estado not in {OrdenProduccion.Estado.BORRADOR, OrdenProduccion.Estado.PROGRAMADA}:
        raise ValidationError("La orden ya no admite ajustes.")
    cantidad = Decimal(cantidad)
    if cantidad <= 0 or (cantidad != orden.cantidad_sugerida and not justificacion.strip()):
        raise ValidationError("El ajuste requiere cantidad positiva y justificación.")
    if motivo == "OTRO" and not justificacion.strip():
        raise ValidationError("El motivo OTRO requiere una justificación.")
    if not _puede(usuario, "inventario.ajustar_cantidad_ordenproduccion"):
        raise PermissionDenied
    anterior = orden.cantidad_autorizada or orden.cantidad_sugerida
    autorizado = _puede(usuario, "inventario.autorizar_ordenproduccion")
    AjusteOrdenProduccion.objects.create(empresa=empresa, orden=orden, tipo="CANTIDAD", cantidad_original=anterior, cantidad_nueva=cantidad, diferencia=cantidad-anterior, motivo=motivo, justificacion=justificacion, solicitado_por=usuario, autorizado_por=usuario if autorizado else None, fecha_autorizacion=timezone.now() if autorizado else None)
    orden.cantidad_autorizada = cantidad
    orden.cantidad_planificada = cantidad
    orden.autorizada_por = usuario if autorizado else None
    orden.actualizado_por = usuario
    orden.save(update_fields=["cantidad_autorizada", "cantidad_planificada", "autorizada_por", "actualizado_por", "fecha_actualizacion"])
    calcular_necesidades(cantidad=cantidad, receta=orden.receta, empresa=empresa, orden=orden, fecha_requerida=orden.fecha_programada)
    registrar_evento(empresa=empresa, usuario=usuario, request=request, objeto=orden, modulo="produccion", accion=EventoAuditoria.Accion.EDITAR, descripcion=f"Cantidad autorizada ajustada en {orden.numero}.", datos_anteriores={"cantidad": str(anterior)}, datos_nuevos={"cantidad": str(cantidad), "motivo": motivo})
    return orden


@transaction.atomic
def cambiar_producto(*, orden, empresa, usuario, producto, receta, motivo, justificacion, autorizado_por, request=None):
    orden = OrdenProduccion.objects.select_for_update().get(pk=orden.pk, empresa=empresa)
    if orden.estado not in {OrdenProduccion.Estado.BORRADOR, OrdenProduccion.Estado.PROGRAMADA}:
        raise ValidationError("La orden ya no admite cambios de producto.")
    if not _puede(usuario, "inventario.cambiar_producto_ordenproduccion") or not autorizado_por or not _puede(autorizado_por, "inventario.autorizar_ordenproduccion"):
        raise PermissionDenied
    if producto.empresa_id != empresa.id or receta.empresa_id != empresa.id or receta.producto_terminado_id != producto.id or not receta.vigente_en(orden.fecha_entrega or orden.fecha_programada):
        raise ValidationError("Producto o receta no válidos para la empresa y fecha.")
    AjusteOrdenProduccion.objects.create(empresa=empresa, orden=orden, tipo="PRODUCTO", producto_original=orden.producto_terminado, producto_nuevo=producto, motivo=motivo, justificacion=justificacion, solicitado_por=usuario, autorizado_por=autorizado_por, fecha_autorizacion=timezone.now())
    orden.producto_terminado, orden.receta, orden.autorizada_por = producto, receta, autorizado_por
    orden.save(update_fields=["producto_terminado", "receta", "autorizada_por", "fecha_actualizacion"])
    calcular_necesidades(cantidad=orden.cantidad_autorizada, receta=receta, empresa=empresa, orden=orden, fecha_requerida=orden.fecha_programada)
    registrar_evento(empresa=empresa, usuario=usuario, request=request, objeto=orden, modulo="produccion", accion=EventoAuditoria.Accion.EDITAR, descripcion=f"Producto autorizado cambiado en {orden.numero}.", datos_anteriores={"producto_id": orden.producto_planificado_id}, datos_nuevos={"producto_id": producto.pk, "motivo": motivo})
    return orden


@transaction.atomic
def solicitar_cambio_producto(*, orden, empresa, usuario, producto, receta, motivo, justificacion, request=None):
    orden=OrdenProduccion.objects.select_for_update().get(pk=orden.pk, empresa=empresa)
    if orden.estado not in {OrdenProduccion.Estado.BORRADOR, OrdenProduccion.Estado.PROGRAMADA} or not justificacion.strip():
        raise ValidationError("La solicitud requiere una orden editable y justificación.")
    if producto.empresa_id != empresa.id or receta.empresa_id != empresa.id or receta.producto_terminado_id != producto.id:
        raise ValidationError("El producto o receta no pertenecen al tenant.")
    solicitud=SolicitudCambioProducto.objects.create(empresa=empresa, orden=orden, producto_original=orden.producto_terminado, producto_solicitado=producto, receta_solicitada=receta, motivo=motivo, justificacion=justificacion, solicitado_por=usuario)
    registrar_evento(empresa=empresa, usuario=usuario, request=request, objeto=orden, modulo="produccion", accion=EventoAuditoria.Accion.OTRO, descripcion=f"Cambio de producto solicitado para {orden.numero}.", datos_nuevos={"solicitud_id":solicitud.pk,"producto_id":producto.pk})
    return solicitud


@transaction.atomic
def decidir_cambio_producto(*, solicitud, empresa, usuario, decision, comentario="", request=None):
    solicitud=SolicitudCambioProducto.objects.select_for_update().select_related("orden","producto_solicitado","receta_solicitada").get(pk=solicitud.pk, empresa=empresa)
    if solicitud.estado != SolicitudCambioProducto.Estado.PENDIENTE:
        raise ValidationError("La solicitud ya fue decidida.")
    if not _puede(usuario,"inventario.autorizar_cambio_producto"):
        raise PermissionDenied
    ahora=timezone.now(); solicitud.decidido_por=usuario;solicitud.decidido_en=ahora;solicitud.comentario_decision=comentario
    if decision == "AUTORIZAR":
        cambiar_producto(orden=solicitud.orden,empresa=empresa,usuario=solicitud.solicitado_por,producto=solicitud.producto_solicitado,receta=solicitud.receta_solicitada,motivo=solicitud.motivo,justificacion=solicitud.justificacion,autorizado_por=usuario,request=request)
        solicitud.estado=SolicitudCambioProducto.Estado.AUTORIZADA
    elif decision in {"RECHAZAR","CANCELAR"}:
        solicitud.estado=SolicitudCambioProducto.Estado.RECHAZADA if decision=="RECHAZAR" else SolicitudCambioProducto.Estado.CANCELADA
    else: raise ValidationError("Decisión inválida.")
    solicitud.save(update_fields=["estado","decidido_por","decidido_en","comentario_decision"])
    registrar_evento(empresa=empresa,usuario=usuario,request=request,objeto=solicitud.orden,modulo="produccion",accion=EventoAuditoria.Accion.OTRO,descripcion=f"Solicitud de cambio {solicitud.get_estado_display().lower()}.",datos_nuevos={"solicitud_id":solicitud.pk,"estado":solicitud.estado})
    return solicitud


def crear_snapshot(orden):
    return {"producto_id": orden.producto_terminado_id, "producto": orden.producto_terminado.nombre, "receta_id": orden.receta_id, "receta": str(orden.receta), "version": orden.receta.version, "cantidad_autorizada": str(orden.cantidad_autorizada or orden.cantidad_planificada), "ingredientes": [{"materia_prima_id": n.materia_prima_id, "nombre": n.materia_prima.nombre, "teorica": str(n.cantidad_con_merma), "unidad": n.unidad_medida} for n in orden.necesidades.select_related("materia_prima")]}


@transaction.atomic
def iniciar_orden_inabie(*, orden, empresa, usuario, request=None):
    orden = OrdenProduccion.objects.select_for_update().get(pk=orden.pk, empresa=empresa)
    if not _puede(usuario, "inventario.iniciar_ordenproduccion"):
        raise PermissionDenied
    if orden.estado != OrdenProduccion.Estado.PROGRAMADA:
        raise ValidationError("La orden no está planificada.")
    origen = orden.estado
    orden.snapshot_produccion = crear_snapshot(orden)
    orden.cantidad_iniciada = orden.cantidad_autorizada or orden.cantidad_planificada
    orden.estado, orden.iniciada_por, orden.fecha_inicio_real = OrdenProduccion.Estado.EN_PROCESO, usuario, timezone.now()
    orden.save()
    HistorialEstadoOrdenProduccion.objects.create(empresa=empresa, orden=orden, estado_anterior=origen, estado_nuevo=orden.estado, usuario=usuario, comentario="Inicio INABIE con snapshot")
    registrar_evento(empresa=empresa, usuario=usuario, request=request, objeto=orden, modulo="produccion", accion=EventoAuditoria.Accion.CAMBIAR_ESTADO, descripcion=f"Se inició {orden.numero} con snapshot técnico.")
    return orden


@transaction.atomic
def cerrar_orden_inabie(*, orden, empresa, usuario, cantidad_real, consumos, request=None):
    orden = OrdenProduccion.objects.select_for_update().get(pk=orden.pk, empresa=empresa)
    if not _puede(usuario, "inventario.cerrar_ordenproduccion"):
        raise PermissionDenied
    if orden.estado != OrdenProduccion.Estado.EN_PROCESO:
        raise ValidationError("La orden no está en producción.")
    config, _ = ConfiguracionProduccion.objects.get_or_create(empresa=empresa)
    teoricos = {n.materia_prima_id: n for n in orden.necesidades.all()}
    for dato in consumos:
        teorico = teoricos.get(int(dato["materia_prima_id"]))
        if not teorico:
            raise ValidationError("La materia prima no pertenece al snapshot de la orden.")
        real = Decimal(dato["cantidad_real"]); base = teorico.cantidad_con_merma
        diferencia = real - base; porcentaje = diferencia * 100 / base if base else Decimal("0")
        if abs(porcentaje) > config.umbral_desviacion and not str(dato.get("justificacion", "")).strip():
            raise ValidationError("Las desviaciones superiores al umbral requieren justificación.")
        ConsumoRealProduccion.objects.update_or_create(orden=orden, materia_prima=teorico.materia_prima, defaults={"empresa": empresa, "cantidad_teorica": base, "cantidad_real": real, "unidad_medida": teorico.unidad_medida, "diferencia": diferencia, "porcentaje_desviacion": porcentaje, "motivo": dato.get("motivo", ""), "justificacion": dato.get("justificacion", ""), "registrado_por": usuario})
    origen = orden.estado
    orden.cantidad_producida = Decimal(cantidad_real)
    orden.estado, orden.cerrada_por, orden.fecha_cierre, orden.fecha_fin_real = OrdenProduccion.Estado.CERRADA, usuario, timezone.now(), timezone.now()
    orden.save()
    HistorialEstadoOrdenProduccion.objects.create(empresa=empresa, orden=orden, estado_anterior=origen, estado_nuevo=orden.estado, usuario=usuario, comentario="Cierre INABIE con consumos reales")
    registrar_evento(empresa=empresa, usuario=usuario, request=request, objeto=orden, modulo="produccion", accion=EventoAuditoria.Accion.CAMBIAR_ESTADO, descripcion=f"Se cerró {orden.numero} con consumos reales.")
    return orden


@dataclass
class CoberturaMaterial:
    materia_prima: object
    existencia: Decimal
    necesidad: Decimal
    entradas_confirmadas: Decimal
    saldo_proyectado: Decimal
    compra_sugerida: Decimal
    cobertura_dias: Decimal
    fecha_agotamiento: object
    produccion_riesgo_fecha: object


def proyectar_cobertura(*, empresa, desde=None, dias_productivos=15, modalidad="REGULAR"):
    desde = desde or timezone.localdate(); fechas=[]; fecha=desde
    while len(fechas) < dias_productivos:
        if es_dia_productivo(empresa, fecha, modalidad): fechas.append(fecha)
        fecha += timedelta(days=1)
    consumos=defaultdict(Decimal); dias_con_consumo=defaultdict(int); eventos_consumo=defaultdict(list)
    for entrega in fechas:
        orden = OrdenProduccion.objects.filter(empresa=empresa, fecha_entrega=entrega).exclude(estado=OrdenProduccion.Estado.CANCELADA).first()
        if orden:
            lineas = orden.consumos_reales.all() if orden.estado == OrdenProduccion.Estado.CERRADA else orden.necesidades.all()
            pares = [(x.materia_prima, x.cantidad_real if orden.estado == OrdenProduccion.Estado.CERRADA else x.cantidad_con_merma) for x in lineas]
        else:
            menu=MenuDiario.objects.filter(empresa=empresa, fecha=entrega).first()
            producto=resolver_producto_menu(empresa,menu) if menu else None
            receta=receta_vigente(empresa, producto, entrega) if producto else None
            pares=[(x.materia_prima, q4((x.cantidad * total_raciones(empresa,entrega,modalidad) / receta.rendimiento_base) * (Decimal("1") + x.porcentaje_merma / 100))) for x in receta.ingredientes.select_related("materia_prima")] if receta else []
        for material, cantidad in pares:
            consumos[material] += cantidad; dias_con_consumo[material] += 1
            eventos_consumo[material].append((entrega,cantidad))
    resultados=[]
    for material, necesidad in consumos.items():
        existencia=Decimal(material.stock_actual)
        entradas_material=[x for x in entradas_confirmadas(empresa=empresa,hasta=fechas[-1]) if x.producto_id==material.pk]
        entradas=sum((x.cantidad for x in entradas_material),Decimal("0"))
        saldo_vivo=existencia;agotado=None
        entradas_por_fecha=defaultdict(Decimal)
        for entrada in entradas_material: entradas_por_fecha[entrada.fecha_estimada_recepcion]+=entrada.cantidad
        for fecha_consumo,cantidad in eventos_consumo[material]:
            saldo_vivo += sum((cantidad_entrada for fecha_entrada,cantidad_entrada in entradas_por_fecha.items() if fecha_entrada <= fecha_consumo),Decimal("0"))
            entradas_por_fecha={f:q for f,q in entradas_por_fecha.items() if f>fecha_consumo}
            saldo_vivo -= cantidad
            if saldo_vivo < 0 and agotado is None: agotado=fecha_consumo
        saldo=existencia+entradas-necesidad
        promedio=necesidad / max(dias_con_consumo[material], 1); cobertura=(existencia+entradas)/promedio if promedio else Decimal("0")
        compra=max(Decimal("0"), necesidad-existencia-entradas)
        resultados.append(CoberturaMaterial(material, existencia, necesidad, entradas, saldo, compra, cobertura, agotado, agotado))
        config,_=ConfiguracionProduccion.objects.get_or_create(empresa=empresa)
        AlertaAbastecimiento.objects.update_or_create(empresa=empresa, materia_prima=material, defaults={"fecha_calculo": desde, "cobertura_dias": cobertura, "fecha_agotamiento": agotado, "cantidad_sugerida_compra": compra, "produccion_riesgo_fecha": agotado, "activa": cobertura <= config.alerta_cobertura_dias})
    return resultados


from django.db import models
