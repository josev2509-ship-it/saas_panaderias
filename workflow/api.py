from django.contrib.contenttypes.models import ContentType
from .application.services import iniciar_workflow,obtener_estado_workflow
from .domain.adapters import adapter_registry

class WorkflowService:
    def register_adapter(self,key,adapter):adapter_registry.register(key,adapter)
    def start(self,*,document,adapter,context,idempotency_key,dominio,tipo_documento,proposito="APROBACION"):
        return iniciar_workflow(document=document,adapter_key=adapter,context=context,idempotency_key=idempotency_key,dominio=dominio,tipo_documento=tipo_documento,proposito=proposito)
    def get_status(self,*,document,empresa,proposito="APROBACION"):
        return obtener_estado_workflow(empresa=empresa,content_type=ContentType.objects.get_for_model(document),object_id=document.pk,proposito=proposito)
workflow_service=WorkflowService()
