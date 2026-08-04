from django.apps import AppConfig
class RrhhConfig(AppConfig):
 name="rrhh"
 def ready(self):
  from .workflow_adapters import register
  register()
