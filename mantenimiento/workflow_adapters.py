from core.application.workflow_adapters import EnterpriseDocumentAdapter
from workflow.domain.adapters import adapter_registry
def register():adapter_registry.register("mantenimiento.alto_costo",EnterpriseDocumentAdapter(reference_field="numero",amount_fields=("costo_total",),start_states=("BORRADOR",)))
