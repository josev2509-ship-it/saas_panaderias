from django.apps import AppConfig
class NominaConfig(AppConfig):
 name="nomina"
 def ready(self):
  from .workflow_adapters import register
  register()
