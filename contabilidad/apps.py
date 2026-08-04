from django.apps import AppConfig


class ContabilidadConfig(AppConfig):
    name = 'contabilidad'
    def ready(self):
        from .workflow_adapters import register
        register()
