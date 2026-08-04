from core.application.workflow_adapters import EnterpriseDocumentAdapter
from workflow.domain.adapters import adapter_registry
def register():
 adapter_registry.register("activos.alta",EnterpriseDocumentAdapter(reference_field="codigo",amount_fields=("costo",),start_states=("BORRADOR","ACTIVO"),approval_state="ACTIVO"))
 adapter_registry.register("activos.baja",EnterpriseDocumentAdapter(amount_fields=("valor_recuperado",),state_field=None))
 adapter_registry.register("activos.revaluacion",EnterpriseDocumentAdapter(amount_fields=("valor_nuevo",),state_field=None))
