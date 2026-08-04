from dataclasses import replace
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from core.application.event_bus import event_bus

from .api import contabilizar
from .domain_events import AsientoReversado, PeriodoCerrado, PeriodoReabierto
from .models import (
    AsientoContable, CierreContable, HistorialAsiento, LineaAsientoContable,
    PeriodoContable, ReversionContable,
)


def _evento(evento, obj, context, accion):
    event_bus.publish(evento(
        empresa_id=context.empresa.pk, usuario_id=getattr(context.usuario, "pk", None),
        agregado_tipo=f"contabilidad.{obj._meta.model_name}", agregado_id=str(obj.pk),
        referencia=str(obj.pk), clave_idempotente=f"{accion}:{obj.pk}",
        payload={"schema_version": 1, "empresa_id": context.empresa.pk, "objeto_id": obj.pk},
    ))


@transaction.atomic
def cerrar_periodo(*, context, periodo, motivo=""):
    periodo = PeriodoContable.objects.select_for_update().get(pk=periodo.pk, empresa=context.empresa)
    existente = CierreContable.objects.filter(periodo=periodo).first()
    if existente:
        return existente
    if periodo.estado != "ABIERTO":
        raise ValidationError("El periodo no está abierto.")
    invalidos = AsientoContable.objects.filter(periodo=periodo).exclude(total_debito=models.F("total_credito"))
    if invalidos.exists() or AsientoContable.objects.filter(periodo=periodo, estado="BORRADOR").exists():
        raise ValidationError("El periodo contiene asientos borrador o desbalanceados.")
    cierre = CierreContable.objects.create(empresa=context.empresa, periodo=periodo, motivo=motivo, creado_por=context.usuario)
    periodo.estado = "CERRADO"
    periodo.save(update_fields=["estado"])
    registrar_evento(empresa=context.empresa, usuario=context.usuario, objeto=periodo, modulo="contabilidad", accion=EventoAuditoria.Accion.CAMBIAR_ESTADO, descripcion="Periodo contable cerrado.", datos_anteriores={"estado": "ABIERTO"}, datos_nuevos={"estado": "CERRADO", "motivo": motivo})
    _evento(PeriodoCerrado, periodo, context, "periodo-cerrado")
    return cierre


@transaction.atomic
def reabrir_periodo(*, context, periodo, motivo):
    if not motivo:
        raise ValidationError("El motivo de reapertura es obligatorio.")
    periodo = PeriodoContable.objects.select_for_update().get(pk=periodo.pk, empresa=context.empresa)
    if periodo.estado == "ABIERTO":
        return periodo
    periodo.estado = "ABIERTO"
    periodo.save(update_fields=["estado"])
    CierreContable.objects.filter(periodo=periodo).delete()
    registrar_evento(empresa=context.empresa, usuario=context.usuario, objeto=periodo, modulo="contabilidad", accion=EventoAuditoria.Accion.CAMBIAR_ESTADO, descripcion="Periodo contable reabierto.", datos_anteriores={"estado": "CERRADO"}, datos_nuevos={"estado": "ABIERTO", "motivo": motivo})
    _evento(PeriodoReabierto, periodo, context, "periodo-reabierto")
    return periodo


@transaction.atomic
def revertir_asiento(*, context, asiento, motivo):
    asiento = AsientoContable.objects.select_for_update().get(pk=asiento.pk, empresa=context.empresa)
    previa = ReversionContable.objects.filter(asiento_origen=asiento).first()
    if previa:
        return previa.asiento_reversion
    if asiento.estado != "CONTABILIZADO" or asiento.periodo.estado != "ABIERTO":
        raise ValidationError("Solo se revierten asientos contabilizados en periodos abiertos.")
    lineas = [{"cuenta": x.cuenta, "debito": x.credito, "credito": x.debito, "descripcion": f"Reversión: {x.descripcion}", "dimensiones": x.dimensiones} for x in asiento.lineas.select_related("cuenta")]
    reversa = contabilizar(context=replace(context, clave_idempotente=f"reversion:{asiento.pk}"), origen_tipo="REVERSION", origen_id=asiento.pk, concepto=f"Reversión {asiento.numero}: {motivo}", lineas=lineas, fecha=timezone.localdate(), diario=asiento.diario, moneda=asiento.moneda, tasa_cambio=asiento.tasa_cambio)
    ReversionContable.objects.create(empresa=context.empresa, asiento_origen=asiento, asiento_reversion=reversa, motivo=motivo, creado_por=context.usuario)
    asiento.estado = "REVERSADO"
    asiento.save(update_fields=["estado"])
    HistorialAsiento.objects.create(asiento=asiento, estado_anterior="CONTABILIZADO", estado_nuevo="REVERSADO", usuario=context.usuario)
    _evento(AsientoReversado, asiento, context, "asiento-reversado")
    return reversa


# Import tardío evitado en el nivel de módulo para conservar una API pequeña.
from django.db import models
