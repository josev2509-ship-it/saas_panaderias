from django.apps import AppConfig


class ComprasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "compras"
    verbose_name = "Compras"

    def ready(self):
        from workflow.api import workflow_service
        from .domain.solicitudes.workflow_adapter import SolicitudCompraWorkflowAdapter
        workflow_service.register_adapter("compras.solicitud_compra",SolicitudCompraWorkflowAdapter())
