from core.domain.events import DomainEvent


class ProveedorCreado(DomainEvent): pass
class ProveedorActualizado(DomainEvent): pass
class ProveedorActivado(DomainEvent): pass
class ProveedorSuspendido(DomainEvent): pass
class ProveedorBloqueado(DomainEvent): pass
class ProveedorReactivado(DomainEvent): pass
class ProveedorInactivado(DomainEvent): pass
class ContactoProveedorCreado(DomainEvent): pass
class DireccionProveedorCreada(DomainEvent): pass
class ProductoProveedorVinculado(DomainEvent): pass
class CuentaBancariaProveedorRegistrada(DomainEvent): pass
class CuentaBancariaProveedorVerificada(DomainEvent): pass
class DocumentoProveedorActualizado(DomainEvent): pass
class CorrespondenciaProveedorLegadoCreada(DomainEvent): pass
