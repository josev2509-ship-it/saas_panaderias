from core.application.workflow_adapters import EnterpriseDocumentAdapter
from workflow.domain.adapters import adapter_registry

def register():
    specs={"contabilidad.asiento_manual":dict(reference_field="numero",amount_fields=("total_debito",),start_states=("BORRADOR",),approval_state="CONTABILIZADO"),"contabilidad.cierre":dict(state_field=None),"contabilidad.reapertura":dict(state_field=None),"contabilidad.solicitud_pago":dict(amount_fields=("monto",),start_states=("BORRADOR",)),"contabilidad.orden_pago":dict(reference_field="numero",start_states=("BORRADOR",),approval_state="APROBADA"),"contabilidad.anticipo":dict(amount_fields=("monto",),state_field=None),"contabilidad.gasto_extraordinario":dict(amount_fields=("total_debito",),start_states=("BORRADOR",),approval_state="CONTABILIZADO"),"contabilidad.aporte_socio":dict(amount_fields=("monto",),state_field=None),"contabilidad.prestamo_socio":dict(amount_fields=("monto",),state_field=None)}
    for key,options in specs.items():adapter_registry.register(key,EnterpriseDocumentAdapter(**options))
