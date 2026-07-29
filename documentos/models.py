from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from conduces.models import Empresa

EXTENSIONES_ADMITIDAS = {"pdf", "jpg", "jpeg", "png", "webp"}


def ruta_documento(instance, filename):
    from django.utils import timezone
    from uuid import uuid4
    ahora = timezone.now()
    extension = instance.extension or Path(filename).suffix.lower().lstrip(".")
    return f"documentos/{instance.empresa_id}/{ahora:%Y/%m}/{uuid4().hex}.{extension}"


def extension_por_contenido(archivo):
    posicion = archivo.tell()
    archivo.seek(0)
    cabecera = archivo.read(16)
    archivo.seek(posicion)
    if cabecera.startswith(b"%PDF-"):
        return "pdf"
    if cabecera.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if cabecera.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WEBP":
        return "webp"
    return None


class TipoDocumento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="tipos_documento")
    nombre = models.CharField(max_length=120)
    codigo = models.CharField(max_length=30)
    descripcion = models.TextField(blank=True)
    requiere_vencimiento = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [models.UniqueConstraint(fields=["empresa", "codigo"], name="doc_tipo_empresa_codigo_uniq")]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Documento(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        VENCIDO = "VENCIDO", "Vencido"
        REEMPLAZADO = "REEMPLAZADO", "Reemplazado"
        ANULADO = "ANULADO", "Anulado"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="documentos")
    tipo_documento = models.ForeignKey(TipoDocumento, on_delete=models.SET_NULL, null=True, blank=True)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    archivo = models.FileField(upload_to=ruta_documento)
    nombre_original = models.CharField(max_length=255, editable=False)
    extension = models.CharField(max_length=10, editable=False)
    tamano_bytes = models.PositiveBigIntegerField(editable=False)
    fecha_documento = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    confidencial = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)
    version = models.PositiveIntegerField(default=1)
    documento_anterior = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="reemplazos")
    creado_por = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        indexes = [
            models.Index(fields=["empresa", "estado"], name="doc_emp_estado_idx"),
            models.Index(fields=["content_type", "object_id"], name="doc_objeto_idx"),
            models.Index(fields=["empresa", "fecha_vencimiento"], name="doc_emp_venc_idx"),
            models.Index(fields=["empresa", "fecha_creacion"], name="doc_emp_creacion_idx"),
        ]

    def clean(self):
        errors = {}
        objeto = self.content_object
        if objeto is not None and hasattr(objeto, "empresa_id") and objeto.empresa_id != self.empresa_id:
            errors["object_id"] = "El registro relacionado pertenece a otra empresa."
        if self.tipo_documento_id:
            if self.empresa_id and self.tipo_documento.empresa_id != self.empresa_id:
                errors["tipo_documento"] = "El tipo documental pertenece a otra empresa."
            if self.tipo_documento.requiere_vencimiento and not self.fecha_vencimiento:
                errors["fecha_vencimiento"] = "Este tipo documental requiere fecha de vencimiento."
        if self.fecha_documento and self.fecha_vencimiento and self.fecha_vencimiento < self.fecha_documento:
            errors["fecha_vencimiento"] = "La fecha de vencimiento no puede ser anterior a la fecha del documento."
        if self.archivo and not self.pk:
            detectada = extension_por_contenido(self.archivo)
            declarada = Path(self.archivo.name).suffix.lower().lstrip(".")
            if detectada not in EXTENSIONES_ADMITIDAS or (declarada == "jpg" and detectada != "jpeg") or (declarada != "jpg" and declarada != detectada):
                errors["archivo"] = "El contenido del archivo no corresponde a un formato permitido: PDF, JPG, JPEG, PNG o WEBP."
            maximo = getattr(settings, "DOCUMENTOS_MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
            if self.archivo.size > maximo:
                errors["archivo"] = f"El archivo supera el tamaño máximo permitido de {maximo // (1024 * 1024)} MB."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.titulo} (v{self.version})"
