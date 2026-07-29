from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from conduces.models import Empresa


class EventoAuditoria(models.Model):
    class Accion(models.TextChoices):
        CREAR = "CREAR", "Crear"
        EDITAR = "EDITAR", "Editar"
        CAMBIAR_ESTADO = "CAMBIAR_ESTADO", "Cambiar estado"
        CARGAR_DOCUMENTO = "CARGAR_DOCUMENTO", "Cargar documento"
        REEMPLAZAR_DOCUMENTO = "REEMPLAZAR_DOCUMENTO", "Reemplazar documento"
        ANULAR_DOCUMENTO = "ANULAR_DOCUMENTO", "Anular documento"
        DESCARGAR_DOCUMENTO = "DESCARGAR_DOCUMENTO", "Descargar documento"
        OTRO = "OTRO", "Otro"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="eventos_auditoria")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    modulo = models.CharField(max_length=80)
    accion = models.CharField(max_length=30, choices=Accion.choices)
    descripcion = models.TextField()
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["empresa", "fecha"], name="aud_emp_fecha_idx"),
            models.Index(fields=["empresa", "modulo"], name="aud_emp_modulo_idx"),
            models.Index(fields=["content_type", "object_id"], name="aud_objeto_idx"),
            models.Index(fields=["usuario", "fecha"], name="aud_usuario_fecha_idx"),
        ]

    def __str__(self):
        return f"{self.get_accion_display()} · {self.modulo} · {self.fecha:%d/%m/%Y %H:%M}"
