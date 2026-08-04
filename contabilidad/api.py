from dataclasses import asdict, dataclass, replace
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from core.application.event_bus import event_bus
from core.application.numbering import obtener_siguiente_numero

from .domain_events import AsientoContabilizado, AsientoCreado, AsientoValidado, DocumentoContabilizado
from .models import AsientoContable, CuentaContable, DiarioContable, LineaAsientoContable, PeriodoContable, ReglaContabilizacion, ValorDimensionContable


@dataclass(frozen=True)
class LineaContableDTO:
    cuenta: str
    debito: str
    credito: str
    descripcion: str = ""
    dimensiones: dict | None = None


@dataclass(frozen=True)
class ResultadoContabilizacion:
    asiento_id: int | None
    numero: str
    estado: str
    origen_tipo: str
    origen_id: str
    total_debito: str
    total_credito: str
    simulado: bool
    lineas: tuple[LineaContableDTO, ...]


class ConfiguracionContableError(ValidationError):
    pass


def _validar_origen(context, obj):
    if not getattr(obj, "pk", None):
        raise ValidationError("El documento origen debe estar persistido.")
    if getattr(obj, "empresa_id", context.empresa.pk) != context.empresa.pk:
        raise ValidationError("El documento origen pertenece a otra empresa.")


def _normalizar_lineas(context, lineas):
    resultado = []
    for item in lineas:
        cuenta = item["cuenta"] if hasattr(item["cuenta"], "pk") else CuentaContable.objects.get(empresa=context.empresa, codigo=item["cuenta"], activa=True)
        if cuenta.empresa_id != context.empresa.pk or not cuenta.acepta_movimientos or not cuenta.activa:
            raise ConfiguracionContableError("Cuenta contable inválida para movimientos.")
        dimensiones = item.get("dimensiones") or {}
        if not isinstance(dimensiones, dict):
            raise ValidationError("Las dimensiones deben ser un objeto.")
        ids = [value for value in dimensiones.values() if isinstance(value, int)]
        if ids:
            valores = ValorDimensionContable.objects.filter(pk__in=ids, empresa=context.empresa, activo=True, dimension__activa=True).select_related("dimension")
            encontrados = {valor.pk: valor for valor in valores}
            if set(ids) != set(encontrados):
                raise ValidationError("La línea contiene una dimensión inválida, inactiva o de otra empresa.")
            for codigo, value in dimensiones.items():
                if isinstance(value, int) and encontrados[value].dimension.codigo != codigo:
                    raise ValidationError("El valor no corresponde a la dimensión indicada.")
        if cuenta.requiere_centro_costo and not dimensiones.get("CENTRO_COSTO"):
            raise ValidationError("La cuenta exige centro de costo.")
        if cuenta.requiere_proyecto and not dimensiones.get("PROYECTO"):
            raise ValidationError("La cuenta exige proyecto.")
        debito, credito = Decimal(str(item.get("debito", 0))), Decimal(str(item.get("credito", 0)))
        if (debito > 0) == (credito > 0):
            raise ValidationError("Cada línea debe tener exactamente un lado contable.")
        resultado.append({**item, "cuenta": cuenta, "debito": debito, "credito": credito, "dimensiones": dimensiones})
    debito = sum((x["debito"] for x in resultado), Decimal(0))
    credito = sum((x["credito"] for x in resultado), Decimal(0))
    if debito <= 0 or debito != credito:
        raise ValidationError("El asiento debe estar balanceado.")
    return resultado, debito, credito


def _dto(asiento=None, *, origen_tipo, origen_id, lineas, debito, credito, simulado=False):
    return ResultadoContabilizacion(
        asiento_id=getattr(asiento, "pk", None), numero=getattr(asiento, "numero", "SIMULACION"),
        estado=getattr(asiento, "estado", "SIMULADO"), origen_tipo=origen_tipo, origen_id=str(origen_id),
        total_debito=str(debito), total_credito=str(credito), simulado=simulado,
        lineas=tuple(LineaContableDTO(cuenta=x["cuenta"].codigo, debito=str(x["debito"]), credito=str(x["credito"]), descripcion=x.get("descripcion", ""), dimensiones=x.get("dimensiones", {})) for x in lineas),
    )


def _emitir(context, clase, asiento, clave):
    event_bus.publish(clase(empresa_id=context.empresa.pk, usuario_id=getattr(context.usuario, "pk", None), agregado_tipo="contabilidad.asientocontable", agregado_id=str(asiento.pk), referencia=asiento.numero, clave_idempotente=clave, payload={"schema_version": 1, "empresa_id": context.empresa.pk, "asiento_id": asiento.pk, "numero": asiento.numero, "origen_tipo": asiento.origen_tipo, "origen_id": asiento.origen_id, "moneda_id": asiento.moneda_id, "tasa_cambio": str(asiento.tasa_cambio), "dimensiones": [x.dimensiones for x in asiento.lineas.all()]}))


def _validar_moneda(context, moneda, tasa_cambio, fecha):
    from catalogos.models import MonedaEmpresa, TasaCambio
    moneda = moneda or MonedaEmpresa.objects.filter(empresa=context.empresa, es_base=True, activa=True).first()
    if not moneda or moneda.empresa_id != context.empresa.pk or not moneda.activa:
        raise ValidationError("La moneda no pertenece a la empresa o está inactiva.")
    if moneda.es_base:
        tasa = Decimal("1") if tasa_cambio is None else Decimal(str(tasa_cambio))
        if tasa != Decimal("1"):
            raise ValidationError("La moneda base debe contabilizarse con tasa 1.")
        return moneda, tasa
    if tasa_cambio is None:
        raise ValidationError("La tasa de cambio es obligatoria para moneda extranjera.")
    tasa = Decimal(str(tasa_cambio))
    if tasa <= 0:
        raise ValidationError("La tasa de cambio debe ser positiva.")
    vigente = TasaCambio.objects.filter(empresa=context.empresa, moneda=moneda, tasa=tasa, activa=True, vigente_desde__lte=fecha).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=fecha)).exists()
    if not vigente:
        raise ValidationError("La tasa no está vigente para la fecha contable.")
    return moneda, tasa


@transaction.atomic
def contabilizar(*, context, origen_tipo, origen_id, concepto, lineas, fecha=None, diario=None, moneda=None, tasa_cambio=None, simular=False):
    if not context.usuario or not context.usuario.has_perm("contabilidad.contabilizar_asiento"):
        raise PermissionDenied("Se requiere contabilidad.contabilizar_asiento.")
    fecha = fecha or timezone.localdate()
    moneda, tasa_cambio = _validar_moneda(context, moneda, tasa_cambio, fecha)
    clave = f"contabilidad:{origen_tipo}:{origen_id}"
    previo = AsientoContable.objects.filter(empresa=context.empresa, clave_idempotencia=clave).first()
    if previo:
        solicitado_debito=sum((Decimal(str(x.get("debito",0))) for x in lineas),Decimal(0));solicitado_credito=sum((Decimal(str(x.get("credito",0))) for x in lineas),Decimal(0))
        if previo.concepto!=concepto or previo.total_debito!=solicitado_debito or previo.total_credito!=solicitado_credito or previo.moneda_id != moneda.pk or previo.tasa_cambio != tasa_cambio:
            raise ValidationError("La clave idempotente fue reutilizada con un payload diferente.")
        return previo
    periodo = PeriodoContable.objects.select_for_update().filter(empresa=context.empresa, anio=fecha.year, mes=fecha.month, estado="ABIERTO").first()
    if not periodo:
        raise ValidationError("No existe un periodo contable abierto para la fecha.")
    diario = diario or DiarioContable.objects.get(empresa=context.empresa, codigo="GENERAL", activo=True)
    lineas, debito, credito = _normalizar_lineas(context, lineas)
    if simular:
        return _dto(origen_tipo=origen_tipo, origen_id=origen_id, lineas=lineas, debito=debito, credito=credito, simulado=True)
    numero = obtener_siguiente_numero(empresa=context.empresa, tipo_documento="ASI", usuario=context.usuario, context=replace(context, clave_idempotente=f"{clave}:numero"))
    asiento = AsientoContable.objects.create(empresa=context.empresa, numero=numero, periodo=periodo, diario=diario, fecha=fecha, concepto=concepto, moneda=moneda, tasa_cambio=tasa_cambio, estado="CONTABILIZADO", origen_tipo=origen_tipo, origen_id=str(origen_id), clave_idempotencia=clave, total_debito=debito, total_credito=credito, creado_por=context.usuario)
    for item in lineas:
        LineaAsientoContable.objects.create(asiento=asiento, cuenta=item["cuenta"], descripcion=item.get("descripcion", concepto), debito=item["debito"], credito=item["credito"], dimensiones=item.get("dimensiones", {}))
    registrar_evento(empresa=context.empresa, usuario=context.usuario, request=context.request, objeto=asiento, modulo="contabilidad", accion=EventoAuditoria.Accion.CREAR, descripcion="Documento contabilizado.", datos_nuevos={"numero": numero, "origen_tipo": origen_tipo, "origen_id": str(origen_id), "total": str(debito), "moneda_id": moneda.pk, "tasa_cambio": str(tasa_cambio), "dimensiones": [x["dimensiones"] for x in lineas], "correlation_id": context.identificador_solicitud})
    _emitir(context, AsientoCreado, asiento, f"asiento-creado:{asiento.pk}")
    _emitir(context, AsientoValidado, asiento, f"asiento-validado:{asiento.pk}")
    _emitir(context, AsientoContabilizado, asiento, f"asiento-contabilizado:{asiento.pk}")
    _emitir(context, DocumentoContabilizado, asiento, f"documento-contabilizado:{origen_tipo}:{origen_id}")
    return asiento


def _regla(context, evento, obj, monto, concepto, *, simular=False):
    _validar_origen(context, obj)
    reglas = ReglaContabilizacion.objects.filter(empresa=context.empresa, evento=evento, activa=True).order_by("-version")
    if not reglas.exists():
        raise ConfiguracionContableError(f"No existe regla contable activa para {evento}.")
    version = reglas.first().version
    candidatas = list(reglas.filter(version=version)[:2])
    if len(candidatas) != 1:
        raise ConfiguracionContableError(f"La regla contable para {evento} es ambigua.")
    regla = candidatas[0]
    try:
        debito = CuentaContable.objects.get(empresa=context.empresa, codigo=regla.configuracion["debito"], activa=True)
        credito = CuentaContable.objects.get(empresa=context.empresa, codigo=regla.configuracion["credito"], activa=True)
    except (KeyError, CuentaContable.DoesNotExist) as exc:
        raise ConfiguracionContableError(f"Configuración contable incompleta para {evento}.") from exc
    dimensiones = getattr(obj, "dimensiones", {}) or {}
    asiento = contabilizar(
        context=context, origen_tipo=evento, origen_id=obj.pk, concepto=concepto,
        lineas=[{"cuenta": debito, "debito": monto, "dimensiones": dimensiones}, {"cuenta": credito, "credito": monto, "dimensiones": dimensiones}],
        fecha=getattr(obj, "fecha", None), moneda=getattr(obj, "moneda", None),
        tasa_cambio=getattr(obj, "tasa_cambio", None), simular=simular,
    )
    if isinstance(asiento, ResultadoContabilizacion):
        return asiento
    lineas_dto = [{"cuenta": linea.cuenta, "debito": linea.debito, "credito": linea.credito, "descripcion": linea.descripcion, "dimensiones": linea.dimensiones} for linea in asiento.lineas.select_related("cuenta")]
    return _dto(asiento, origen_tipo=evento, origen_id=obj.pk, lineas=lineas_dto, debito=asiento.total_debito, credito=asiento.total_credito)


def _monto(obj, *atributos):
    for nombre in atributos:
        valor = getattr(obj, nombre, None)
        if valor is not None:
            return Decimal(str(valor))
    raise ValidationError("El documento no expone un monto contabilizable.")


def contabilizar_factura_venta(*, context, factura, simular=False): return _regla(context, "FACTURA_VENTA", factura, _monto(factura, "total"), f"Factura {factura.numero}", simular=simular)
def contabilizar_nota_credito_venta(*, context, nota, simular=False): return _regla(context, "NOTA_CREDITO_VENTA", nota, _monto(nota, "total", "monto"), f"Nota crédito {nota.numero}", simular=simular)
def contabilizar_nota_debito_venta(*, context, nota, simular=False): return _regla(context, "NOTA_DEBITO_VENTA", nota, _monto(nota, "total", "monto"), f"Nota débito {nota.numero}", simular=simular)
def contabilizar_cobro(*, context, cobro, simular=False): return _regla(context, "COBRO", cobro, _monto(cobro, "monto"), f"Cobro {cobro.numero}", simular=simular)
def contabilizar_factoring(*, context, factoring, simular=False): return _regla(context, "FACTORING", factoring, _monto(factoring, "monto", "monto_cedido"), f"Factoring {factoring.pk}", simular=simular)
def contabilizar_factura_proveedor(*, context, factura, simular=False): return _regla(context, "FACTURA_PROVEEDOR", factura, factura.total, f"Factura proveedor {factura.numero}", simular=simular)
def contabilizar_nota_credito_proveedor(*, context, nota, simular=False): return _regla(context, "NOTA_CREDITO_PROVEEDOR", nota, nota.monto, f"Nota proveedor {nota.numero}", simular=simular)
def contabilizar_anticipo_proveedor(*, context, anticipo, simular=False): return _regla(context, "ANTICIPO_PROVEEDOR", anticipo, anticipo.monto, f"Anticipo proveedor {anticipo.pk}", simular=simular)
def contabilizar_pago_proveedor(*, context, pago, simular=False): return _regla(context, "PAGO_PROVEEDOR", pago, pago.monto, f"Pago proveedor {pago.pk}", simular=simular)
def contabilizar_movimiento_inventario(*, context, movimiento, simular=False): return _regla(context, "INVENTARIO", movimiento, _monto(movimiento, "valor_total", "monto") if not hasattr(movimiento, "cantidad") else movimiento.cantidad * getattr(movimiento, "costo_unitario", getattr(movimiento, "precio_unitario", 0)), f"Inventario {movimiento.pk}", simular=simular)
def contabilizar_transferencia_inventario(*, context, movimiento, simular=False): return _regla(context, "TRANSFERENCIA_INVENTARIO", movimiento, _monto(movimiento, "valor_total", "monto"), f"Transferencia {movimiento.pk}", simular=simular)
def contabilizar_ajuste_inventario(*, context, movimiento, simular=False): return _regla(context, "AJUSTE_INVENTARIO", movimiento, _monto(movimiento, "valor_total", "monto"), f"Ajuste {movimiento.pk}", simular=simular)
def contabilizar_merma_inventario(*, context, movimiento, simular=False): return _regla(context, "MERMA_INVENTARIO", movimiento, _monto(movimiento, "valor_total", "monto"), f"Merma {movimiento.pk}", simular=simular)
def contabilizar_consumo_produccion(*, context, consumo, simular=False): return _regla(context, "CONSUMO_PRODUCCION", consumo, consumo.cantidad * consumo.movimiento.costo_unitario, f"Consumo {consumo.pk}", simular=simular)
def contabilizar_entrada_producto_terminado(*, context, entrada, simular=False): return _regla(context, "ENTRADA_PRODUCTO_TERMINADO", entrada, _monto(entrada, "valor_total", "monto"), f"Entrada terminada {entrada.pk}", simular=simular)
def contabilizar_cierre_orden_produccion(*, context, orden, simular=False): return _regla(context, "CIERRE_ORDEN_PRODUCCION", orden, _monto(orden, "costo_real", "costo_total"), f"Cierre producción {orden.pk}", simular=simular)
def contabilizar_nomina(*, context, nomina, simular=False): return _regla(context, "NOMINA", nomina, nomina.total_neto, f"Nómina {nomina.numero}", simular=simular)
def contabilizar_pago_nomina(*, context, pago, simular=False): return _regla(context, "PAGO_NOMINA", pago, _monto(pago, "monto", "total_neto"), f"Pago nómina {pago.pk}", simular=simular)
def contabilizar_prestaciones(*, context, prestacion, simular=False): return _regla(context, "PRESTACIONES", prestacion, prestacion.monto, f"Prestación {prestacion.pk}", simular=simular)
def contabilizar_liquidacion(*, context, liquidacion, simular=False): return _regla(context, "LIQUIDACION", liquidacion, liquidacion.total, f"Liquidación {liquidacion.pk}", simular=simular)
def contabilizar_alta_activo(*, context, activo, simular=False): return _regla(context, "ALTA_ACTIVO", activo, activo.costo, f"Alta {activo.codigo}", simular=simular)
def contabilizar_depreciacion(*, context, depreciacion, simular=False): return _regla(context, "DEPRECIACION", depreciacion, depreciacion.monto, f"Depreciación {depreciacion.pk}", simular=simular)
def contabilizar_revaluacion(*, context, revaluacion, simular=False): return _regla(context, "REVALUACION", revaluacion, abs(revaluacion.valor_nuevo - revaluacion.valor_anterior), f"Revaluación {revaluacion.activo.codigo}", simular=simular)
def contabilizar_baja_activo(*, context, baja, simular=False): return _regla(context, "BAJA_ACTIVO", baja, baja.activo.costo - baja.activo.depreciacion_acumulada, f"Baja {baja.activo.codigo}", simular=simular)
def contabilizar_mantenimiento_capitalizable(*, context, mantenimiento, simular=False): return _regla(context, "MANTENIMIENTO_CAPITALIZABLE", mantenimiento, _monto(mantenimiento, "costo_total", "monto"), f"Mantenimiento {mantenimiento.pk}", simular=simular)
def contabilizar_ajuste_manual(*, context, concepto, lineas, referencia, simular=False): return contabilizar(context=context, origen_tipo="AJUSTE_MANUAL", origen_id=referencia, concepto=concepto, lineas=lineas, simular=simular)


def balanza(*, empresa, periodo):
    return list(LineaAsientoContable.objects.filter(asiento__empresa=empresa, asiento__periodo=periodo, asiento__estado="CONTABILIZADO").values("cuenta__codigo", "cuenta__nombre").annotate(debito=Sum("debito"), credito=Sum("credito")))

def revertir_documento(*,context,origen_tipo,origen_id,motivo):
    from .services import revertir_asiento
    asiento=AsientoContable.objects.get(empresa=context.empresa,origen_tipo=origen_tipo,origen_id=str(origen_id))
    reversa=revertir_asiento(context=context,asiento=asiento,motivo=motivo)
    return {"asiento_origen_id":asiento.pk,"asiento_reversion_id":reversa.pk,"numero":reversa.numero}
