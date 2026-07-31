from dataclasses import dataclass, field

from uuid import uuid4

from core.domain.exceptions import CrossCompanyViolation, InvalidOperationContext
from core.domain.rules import normalize_idempotency_key, validate_safe_payload


@dataclass(frozen=True)
class OperationContext:
    empresa: object
    usuario: object = None
    request: object = None
    referencia: str = ""
    clave_idempotente: str = ""
    origen: str = ""
    observaciones: str = ""
    metadata: dict = field(default_factory=dict)
    identificador_solicitud: str = ""

    def __post_init__(self):
        if not self.empresa or not getattr(self.empresa, "pk", None):
            raise CrossCompanyViolation("La empresa es obligatoria.")
        if self.usuario and hasattr(self.usuario, "empresa_principal"):
            empresa_usuario = getattr(self.usuario, "empresa_principal", None)
            if empresa_usuario and empresa_usuario.pk != self.empresa.pk:
                raise CrossCompanyViolation("El usuario pertenece a otra empresa.")
        validate_safe_payload(self.metadata)
        if self.clave_idempotente:
            object.__setattr__(
                self, "clave_idempotente",
                normalize_idempotency_key(self.clave_idempotente),
            )
        request_id = self.identificador_solicitud
        if not request_id and self.request:
            request_id = self.request.headers.get("X-Request-ID", "")
        object.__setattr__(self, "identificador_solicitud", request_id or str(uuid4()))

    @property
    def ip(self):
        if not self.request:
            return None
        forwarded = self.request.META.get("HTTP_X_FORWARDED_FOR", "")
        return (forwarded.split(",")[0].strip() if forwarded else self.request.META.get("REMOTE_ADDR"))

    @property
    def user_agent(self):
        return self.request.META.get("HTTP_USER_AGENT", "")[:300] if self.request else ""

    @property
    def clave_idempotencia(self):
        return self.clave_idempotente
