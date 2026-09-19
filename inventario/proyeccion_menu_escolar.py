"""Proyección de solo lectura basada exclusivamente en programación confirmada."""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_CEILING
from types import SimpleNamespace

from conduces.models import CalendarioEscolar, DiaCalendarioEscolar, ProgramacionMenuEscolar
from .engine import InventoryEngine
from .models import ProductoInventario
from .produccion_inabie_services import receta_vigente
from .recipe_matching import encontrar_producto_terminado_match


@dataclass(frozen=True)
class TrazaIngrediente:
    fecha: object
    centro_id: int
    matricula: int
    tipo_matricula: str
    producto_programado: str
    receta_id: int
    rendimiento: Decimal
    factor: Decimal
    ingrediente_id: int
    cantidad: Decimal


@dataclass
class NecesidadProyectada:
    ingrediente: ProductoInventario
    bruta: Decimal = Decimal("0")
    disponible: Decimal = Decimal("0")
    neta: Decimal = Decimal("0")
    empaques: int = 0
    compra_pendiente: bool = False
    trazas: list = field(default_factory=list)


@dataclass
class ProyeccionMenuEscolar:
    raciones: Decimal = Decimal("0")
    necesidades: dict = field(default_factory=dict)
    advertencias: list = field(default_factory=list)


def proyectar_necesidades_menu_escolar(*, empresa, desde, hasta):
    if desde > hasta:
        raise ValueError("El inicio del período debe preceder al final.")
    resultado = ProyeccionMenuEscolar()
    filas = ProgramacionMenuEscolar.objects.filter(
        empresa=empresa, centro__empresa=empresa, programa__empresa=empresa,
        calendario__empresa=empresa, version__programa__empresa=empresa,
        fecha__range=(desde, hasta), confirmada=True,
        calendario__estado=CalendarioEscolar.Estado.ACTIVO,
        estado__in=(ProgramacionMenuEscolar.Estado.PROGRAMADO,
                    ProgramacionMenuEscolar.Estado.EXTRAORDINARIO),
    ).exclude(producto="").select_related("centro", "calendario", "asignacion").order_by("fecha", "id")
    dias = {
        (dia.calendario_id, dia.fecha): dia
        for dia in DiaCalendarioEscolar.objects.filter(
            calendario_id__in=filas.values("calendario_id"),
            fecha__range=(desde, hasta),
        ).only(
            "calendario_id",
            "fecha",
            "clasificacion",
            "origen",
        )
    }
    productos = {}
    recetas = {}
    for fila in filas:
        if not (
            fila.calendario.inicio_docencia
            <= fila.fecha
            <= fila.calendario.fin_docencia
        ):
            continue

        dia = dias.get((fila.calendario_id, fila.fecha))

        if fila.asignacion.modalidad == "PREPARA":
            suspension_real = (
                dia is not None
                and dia.clasificacion != DiaCalendarioEscolar.Clasificacion.DOCENCIA
                and not (dia.origen or "").startswith("PREVISUALIZACION")
            )
            if suspension_real:
                continue
        else:
            if (
                dia is None
                or dia.clasificacion != DiaCalendarioEscolar.Clasificacion.DOCENCIA
            ):
                continue
        if not (fila.asignacion.vigente_desde <= fila.fecha and
                (fila.asignacion.vigente_hasta is None or fila.fecha <= fila.asignacion.vigente_hasta)):
            continue
        matricula, origen = fila.centro.obtener_matricula_para_fecha(fila.fecha, con_origen=True)
        if not matricula:
            continue
        clave = fila.producto.strip().casefold()
        if clave not in productos:
            match = encontrar_producto_terminado_match(empresa=empresa, nombre=fila.producto)
            productos[clave] = (ProductoInventario.objects.filter(
                pk=match.producto_id, empresa=empresa, activo=True, tipo="producto_terminado"
            ).first() if match.producto_id else None)
        producto = productos[clave]
        if producto is None:
            resultado.advertencias.append(f"{fila.fecha}: producto sin vínculo inequívoco: {fila.producto}")
            continue
        llave_receta = (producto.pk, fila.fecha)
        if llave_receta not in recetas:
            recetas[llave_receta] = receta_vigente(empresa, producto, fila.fecha)
        receta = recetas[llave_receta]
        if receta is None or receta.rendimiento_base <= 0:
            resultado.advertencias.append(f"{fila.fecha}: producto sin receta vigente: {fila.producto}")
            continue
        raciones = Decimal(matricula)
        factor = raciones / receta.rendimiento_base
        resultado.raciones += raciones
        for detalle in receta.ingredientes.select_related("materia_prima").all():
            ingrediente = detalle.materia_prima
            if ingrediente.empresa_id != empresa.pk or detalle.unidad_medida != ingrediente.unidad_medida:
                resultado.advertencias.append(f"{fila.fecha}: unidad incompatible para {ingrediente.nombre}")
                continue
            cantidad = detalle.cantidad * factor
            necesidad = resultado.necesidades.setdefault(
                ingrediente.pk, NecesidadProyectada(ingrediente=ingrediente)
            )
            necesidad.bruta += cantidad
            necesidad.trazas.append(TrazaIngrediente(
                fila.fecha, fila.centro_id, matricula, origen, fila.producto,
                receta.pk, receta.rendimiento_base, factor, ingrediente.pk, cantidad,
            ))
    for necesidad in resultado.necesidades.values():
        producto = necesidad.ingrediente
        necesidad.disponible = InventoryEngine.commercial_availability(
            context=SimpleNamespace(empresa=empresa), producto=producto,
        )["disponible"]
        necesidad.neta = max(Decimal("0"), necesidad.bruta - necesidad.disponible)
        if not producto.listo_para_compras:
            necesidad.compra_pendiente = True
            resultado.advertencias.append(f"Producto pendiente de configuración de compra: {producto.nombre}")
            continue
        empaque = Decimal(producto.cantidad_por_empaque or 0)
        if empaque <= 0:
            resultado.advertencias.append(f"Empaque inválido para {producto.nombre}")
        else:
            necesidad.empaques = int((necesidad.neta / empaque).to_integral_value(rounding=ROUND_CEILING))
    return resultado
