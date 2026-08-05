from core.application.workflow_adapters import EnterpriseDocumentAdapter
from workflow.domain.adapters import adapter_registry

def register():
    specs={
        "compras.adjudicacion":dict(reference_field="numero",start_states=("BORRADOR",),approval_state="APROBADA",rejection_state="RECHAZADA"),
        "compras.orden":dict(reference_field="numero",amount_fields=("total",),start_states=("PENDIENTE_APROBACION",),approval_state="APROBADA",rejection_state="BORRADOR"),
        "compras.modificacion_orden":dict(reference_field="numero",amount_fields=("total",),start_states=("APROBADA","ENVIADA","ACEPTADA")),
        "compras.ampliacion_orden":dict(reference_field="numero",amount_fields=("total",),start_states=("APROBADA","ENVIADA","ACEPTADA")),
        "compras.cancelacion_orden":dict(reference_field="numero",amount_fields=("total",),approval_state="CANCELADA"),
        "compras.recepcion_diferencias":dict(reference_field="numero",start_states=("CON_DIFERENCIAS",)),
        "compras.factura_observada":dict(reference_field="numero",amount_fields=("total",),start_states=("OBSERVADA",),approval_state="VALIDADA"),
        "compras.solicitud_pago":dict(amount_fields=("monto",),start_states=("PENDIENTE_APROBACION",),approval_state="APROBADA"),
        "compras.orden_pago":dict(reference_field="numero",start_states=("BORRADOR",),approval_state="APROBADA"),
        "compras.pago_masivo":dict(state_field=None,amount_fields=("monto",)),
        "compras.anticipo":dict(state_field=None,amount_fields=("monto",)),
        "compras.devolucion":dict(reference_field="numero",start_states=("BORRADOR",),approval_state="APROBADA"),
    }
    for key,options in specs.items():adapter_registry.register(key,EnterpriseDocumentAdapter(**options))
