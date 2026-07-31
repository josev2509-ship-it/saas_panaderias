from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentState:
    code: str
    label: str
    tone: str
    category: str
    final: bool = False
    reversible: bool = True


STATES = {
    state.code: state for state in (
        DocumentState("BORRADOR", "Borrador", "neutral", "draft"),
        DocumentState("PENDIENTE", "Pendiente", "warning", "pending"),
        DocumentState("APROBADO", "Aprobado", "success", "approved", True, False),
        DocumentState("RECHAZADO", "Rechazado", "danger", "rejected", True),
        DocumentState("CANCELADO", "Cancelado", "neutral", "cancelled", True, False),
        DocumentState("ACTIVO", "Activo", "success", "active"),
        DocumentState("SUSPENDIDO", "Suspendido", "warning", "suspended"),
        DocumentState("BLOQUEADO", "Bloqueado", "danger", "blocked"),
        DocumentState("INACTIVO", "Inactivo", "neutral", "inactive", True),
    )
}


def state_contract(code, *, fallback_tone="neutral"):
    return STATES.get(
        str(code or "").upper(),
        DocumentState(str(code or ""), str(code or "").replace("_", " ").title(), fallback_tone, "custom"),
    )
