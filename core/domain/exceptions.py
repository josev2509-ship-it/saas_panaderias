class DomainError(Exception):
    default_message = "No fue posible completar la operacion."
    default_code = "domain_error"

    def __init__(self, message=None, *, code=None, metadata=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.metadata = metadata or {}
        super().__init__(self.message)

    def as_dict(self):
        return {"code": self.code, "message": self.message, "metadata": self.metadata}


class BusinessRuleViolation(DomainError): pass
class InvalidStateTransition(DomainError): pass
class InsufficientStock(DomainError): pass
class IdempotencyConflict(DomainError): pass
class CrossCompanyViolation(DomainError): pass
class ConcurrentOperationError(DomainError): pass
class ProtectedHistoricalRecord(DomainError): pass
class NumberingError(DomainError): pass
class ReversalNotAllowed(DomainError): pass
class DirectStockMutationNotAllowed(DomainError): pass
class InventoryConsistencyError(DomainError): pass
class PermissionDeniedDomain(DomainError): pass
class InvalidOperationContext(DomainError): pass
class InactiveSequenceError(DomainError): pass
class UnsafePayloadError(DomainError): pass
