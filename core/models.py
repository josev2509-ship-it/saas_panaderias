from django.conf import settings
from django.db import models

from conduces.models import Empresa


class RegistroIdempotencia(models.Model):
    class Estado(models.TextChoices):
        INICIADA = "INICIADA", "Iniciada"
        COMPLETADA = "COMPLETADA", "Completada"
        FALLIDA = "FALLIDA", "Fallida"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    clave = models.CharField(max_length=180)
    operacion = models.CharField(max_length=100)
    referencia = models.CharField(max_length=180, blank=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.INICIADA)
    resultado_referencia = models.CharField(max_length=250, blank=True)
    hash_solicitud = models.CharField(max_length=64)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    mensaje_error = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    intentos = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "operacion", "clave"],
                name="core_idem_empresa_operacion_clave_uniq",
            )
        ]
        permissions = [("retry_registroidempotencia", "Puede reintentar operaciones fallidas")]


class EventoDominio(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PROCESANDO = "PROCESANDO", "Procesando"
        PROCESADO = "PROCESADO", "Procesado"
        ERROR = "ERROR", "Error"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    tipo_evento = models.CharField(max_length=120)
    agregado_tipo = models.CharField(max_length=120)
    agregado_id = models.CharField(max_length=100)
    referencia = models.CharField(max_length=180, blank=True)
    clave_idempotente = models.CharField(max_length=180)
    payload = models.JSONField(default=dict, blank=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)
    intentos = models.PositiveIntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_procesamiento = models.DateTimeField(null=True, blank=True)
    ultimo_error = models.CharField(max_length=500, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "tipo_evento", "clave_idempotente"],
                name="core_evento_empresa_tipo_clave_uniq",
            )
        ]
        permissions = [("retry_eventodominio", "Puede reintentar eventos de dominio")]


class ConciliacionInventario(models.Model):
    class Estado(models.TextChoices):
        CONSISTENTE = "CONSISTENTE", "Consistente"
        DIFERENCIA = "DIFERENCIA", "Diferencia"
        CORREGIDA = "CORREGIDA", "Corregida"
        IGNORADA = "IGNORADA", "Ignorada"

    class Modo(models.TextChoices):
        DIAGNOSTICO = "DIAGNOSTICO", "Diagnostico"
        CORRECCION = "CORRECCION", "Correccion"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    producto = models.ForeignKey("inventario.ProductoInventario", on_delete=models.PROTECT)
    saldo_movimientos = models.DecimalField(max_digits=16, decimal_places=4)
    saldo_cacheado = models.DecimalField(max_digits=16, decimal_places=4)
    saldo_lotes = models.DecimalField(max_digits=16, decimal_places=4)
    diferencia_movimientos_cache = models.DecimalField(max_digits=16, decimal_places=4)
    diferencia_lotes_cache = models.DecimalField(max_digits=16, decimal_places=4)
    estado = models.CharField(max_length=15, choices=Estado.choices)
    modo = models.CharField(max_length=15, choices=Modo.choices)
    motivo = models.TextField(blank=True)
    ejecutado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)
    lote = models.ForeignKey("inventario.LoteInventario", on_delete=models.PROTECT, null=True, blank=True)
    fecha_correccion = models.DateTimeField(null=True, blank=True)
    referencia = models.CharField(max_length=180, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-fecha"]
        permissions = [
            ("run_inventory_diagnosis", "Puede diagnosticar saldos de inventario"),
            ("rebuild_inventory_balance", "Puede reconstruir saldos de inventario"),
            ("manage_document_sequences", "Puede administrar secuencias documentales"),
            ("view_transaction_engine", "Puede ver el motor transaccional"),
        ]
