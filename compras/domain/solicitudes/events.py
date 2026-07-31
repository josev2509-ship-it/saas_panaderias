from core.domain.events import DomainEvent


class SolicitudCompraCreada(DomainEvent): pass
class SolicitudCompraActualizada(DomainEvent): pass
class LineaSolicitudCompraAgregada(DomainEvent): pass
class LineaSolicitudCompraActualizada(DomainEvent): pass
class LineaSolicitudCompraRetirada(DomainEvent): pass
class SolicitudCompraMarcadaLista(DomainEvent): pass
class SolicitudCompraDevueltaABorrador(DomainEvent): pass
class SolicitudCompraEnviadaAWorkflow(DomainEvent): pass
class SolicitudCompraDevuelta(DomainEvent): pass
class SolicitudCompraCorregida(DomainEvent): pass
class SolicitudCompraReenviada(DomainEvent): pass
class SolicitudCompraAprobada(DomainEvent): pass
class SolicitudCompraRechazada(DomainEvent): pass
class SolicitudCompraCancelada(DomainEvent): pass
class SolicitudCompraDuplicada(DomainEvent): pass
class DocumentoSolicitudCompraActualizado(DomainEvent): pass
class ExportacionSolicitudesCompraGenerada(DomainEvent): pass
