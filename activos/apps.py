from django.apps import AppConfig
class ActivosConfig(AppConfig):
 name="activos"
 def ready(self):
  from .workflow_adapters import register
  register()
