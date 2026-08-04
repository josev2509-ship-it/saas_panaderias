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
    requiere_consumidor: bool = False
    fecha: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def tipo_evento(self):
        return self.__class__.__name__

    def serializable_payload(self):
        data = asdict(self)
        payload = data.get("payload") or {}
        data.update({
            "schema_version": payload.get("schema_version", 1),
            "aggregate_type": self.agregado_tipo,
            "aggregate_id": str(self.agregado_id),
            "actor_id": self.usuario_id,
            "correlation_id": payload.get("correlation_id", self.clave_idempotente),
            "causation_id": payload.get("causation_id", ""),
            "timestamp": self.fecha,
        })
        return data


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
