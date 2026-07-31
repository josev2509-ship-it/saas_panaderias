from uuid import uuid4

from django.utils import timezone

from core.domain.rules import normalize_idempotency_key


def resolve_idempotency_context(request, *, operation, reference="", metadata=None):
    """Resolve a request key without permanently deduplicating equal business data."""
    explicit = request.headers.get("Idempotency-Key", "").strip()
    request_id = request.headers.get("X-Request-ID", "").strip() or str(uuid4())
    if explicit:
        key = normalize_idempotency_key(explicit)
        source = "header"
    else:
        # A new HTTP request is a new operation. Clients that retry after a timeout
        # must resend an explicit Idempotency-Key.
        key = normalize_idempotency_key(f"request-{request_id}")
        source = "request_id"
    safe_metadata = {
        "key_source": source,
        "request_id": request_id,
        "path": request.path,
        "user_id": getattr(request.user, "pk", None),
        "timestamp": timezone.now().isoformat(),
        "operation": operation,
    }
    safe_metadata.update(metadata or {})
    return {
        "clave_idempotente": key,
        "identificador_solicitud": request_id,
        "referencia": reference or request.path,
        "origen": operation,
        "metadata": safe_metadata,
    }
