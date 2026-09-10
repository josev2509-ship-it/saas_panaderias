from dataclasses import dataclass
from decimal import Decimal

from compras.p2p_models import DetalleOrdenCompraEnterprise


ESTADOS_ENTRADA_CONFIRMADA = {"ACEPTADA"}


@dataclass(frozen=True)
class EntradaConfirmada:
    producto_id: int
    cantidad: Decimal
    unidad: str
    fecha_estimada_recepcion: object
    orden_id: int


def entradas_confirmadas(*, empresa, hasta):
    lineas = DetalleOrdenCompraEnterprise.objects.filter(
        orden__empresa=empresa,
        orden__estado__in=ESTADOS_ENTRADA_CONFIRMADA,
        orden__entrega_desde__lte=hasta,
        producto__isnull=False,
    ).select_related("orden", "producto")
    resultado=[]
    for linea in lineas:
        pendiente=max(Decimal("0"), Decimal(linea.cantidad)-Decimal(linea.cantidad_recibida))
        if pendiente:
            resultado.append(EntradaConfirmada(linea.producto_id, pendiente, linea.producto.unidad_medida, linea.orden.entrega_desde, linea.orden_id))
    return resultado
