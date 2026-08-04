from django.apps import AppConfig
class MantenimientoConfig(AppConfig):
 name="mantenimiento"
 def ready(self):
  from .workflow_adapters import register
  register()
