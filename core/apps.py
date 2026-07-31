from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Motor transaccional"

    def ready(self):
        from core.application.handlers import register_handlers
        register_handlers()
