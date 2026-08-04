from decimal import Decimal

from workflow.domain.adapters import WorkflowDocumentAdapter


class EnterpriseDocumentAdapter(WorkflowDocumentAdapter):
    allowed_context_fields = frozenset({"monto_total", "estado", "tipo", "es_alto_costo"})

    def __init__(self, *, reference_field="pk", amount_fields=(), state_field="estado", start_states=(), approval_state="APROBADO", rejection_state="RECHAZADO"):
        self.reference_field = reference_field
        self.amount_fields = amount_fields
        self.state_field = state_field
        self.start_states = frozenset(start_states)
        self.approval_state = approval_state
        self.rejection_state = rejection_state

    def get_empresa(self, document): return document.empresa
    def get_solicitante(self, document): return getattr(document, "creado_por", None) or document.empresa.usuario

    def _amount(self, document):
        for name in self.amount_fields:
            value = getattr(document, name, None)
            if value is not None: return Decimal(str(value))
        return Decimal("0")

    def build_context(self, document):
        amount = self._amount(document)
        return {"monto_total": amount, "estado": str(getattr(document, self.state_field, "")) if self.state_field else "", "tipo": str(getattr(document, "tipo", "")), "es_alto_costo": amount >= Decimal("100000")}

    def can_start(self, document): return not self.start_states or getattr(document, self.state_field, None) in self.start_states
    def snapshot(self, document): return {"referencia": str(getattr(document, self.reference_field, document.pk)), "modelo": document._meta.label_lower, "estado": str(getattr(document, self.state_field, "")) if self.state_field else "", "monto": str(self._amount(document))}

    def on_state_change(self, document, state):
        if self.state_field and hasattr(document, self.state_field) and state == "EN_APROBACION":
            setattr(document, self.state_field, "EN_APROBACION"); document.save(update_fields=[self.state_field])

    def on_final_result(self, document, result):
        if self.state_field and hasattr(document, self.state_field):
            setattr(document, self.state_field, self.approval_state if result == "APROBADA" else self.rejection_state); document.save(update_fields=[self.state_field])
