from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class DomainEvent:
    empresa_id: int
    agregado_tipo: str
    agregado_id: str
    clave_idempotente: str
    usuario_id: int | None = None
    referencia: str = ""
    payload: dict = field(default_factory=dict)
    fecha: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def tipo_evento(self):
        return self.__class__.__name__

    def serializable_payload(self):
        return asdict(self)


class PedidoAprobado(DomainEvent): pass
class OrdenProduccionIniciada(DomainEvent): pass
class OrdenProduccionCompletada(DomainEvent): pass
class ReservaInventarioCreada(DomainEvent): pass
class ReservaInventarioLiberada(DomainEvent): pass
class ReservaInventarioCancelada(DomainEvent): pass
class InventarioConsumido(DomainEvent): pass
class MermaRegistrada(DomainEvent): pass
class MaterialDevuelto(DomainEvent): pass
class ProductoTerminadoIngresado(DomainEvent): pass
class EjecucionInventarioCompletada(DomainEvent): pass
class EjecucionInventarioRevertida(DomainEvent): pass
class SaldoReconstruido(DomainEvent): pass
class ConciliacionCorregida(DomainEvent): pass
class ConflictoIdempotencia(DomainEvent): pass
class SecuenciaEmitida(DomainEvent): pass
class MovimientoAplicado(DomainEvent): pass
