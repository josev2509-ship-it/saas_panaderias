from core.application.workflow_adapters import EnterpriseDocumentAdapter
from workflow.domain.adapters import adapter_registry
def register():
 adapter_registry.register("rrhh.vacaciones",EnterpriseDocumentAdapter(amount_fields=("dias",),start_states=("BORRADOR","PENDIENTE")))
 adapter_registry.register("rrhh.horas_extra",EnterpriseDocumentAdapter(amount_fields=("horas",),start_states=("PENDIENTE",)))
