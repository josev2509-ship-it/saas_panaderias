from core.application.workflow_adapters import EnterpriseDocumentAdapter
from workflow.domain.adapters import adapter_registry
def register():
 adapter_registry.register("nomina.nomina",EnterpriseDocumentAdapter(reference_field="numero",amount_fields=("total_neto",),start_states=("CALCULADA","BORRADOR")))
 adapter_registry.register("nomina.liquidacion",EnterpriseDocumentAdapter(amount_fields=("total",),start_states=("BORRADOR",)))
