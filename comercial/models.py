from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from conduces.models import Empresa


class Cliente(models.Model):
    class Tipo(models.TextChoices):
        CENTRO_EDUCATIVO = "CENTRO_EDUCATIVO", "Centro educativo"
        DISTRITO_ESCOLAR = "DISTRITO_ESCOLAR", "Distrito escolar"
        REGIONAL_EDUCATIVA = "REGIONAL_EDUCATIVA", "Regional educativa"
        INSTITUCION_GUBERNAMENTAL = "INSTITUCION_GUBERNAMENTAL", "Institución gubernamental"
        CLIENTE_PRIVADO = "CLIENTE_PRIVADO", "Cliente privado"
        SUPERMERCADO = "SUPERMERCADO", "Supermercado"
        COLMADO = "COLMADO", "Colmado"
        RESTAURANTE = "RESTAURANTE", "Restaurante"
        DISTRIBUIDOR = "DISTRIBUIDOR", "Distribuidor"
        CONSUMIDOR_FINAL = "CONSUMIDOR_FINAL", "Consumidor final"
        OTRO = "OTRO", "Otro"

    class CondicionPago(models.TextChoices):
        CONTADO = "CONTADO", "Contado"
        CREDITO = "CREDITO", "Crédito"
        MIXTO = "MIXTO", "Mixto"

    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        INACTIVO = "INACTIVO", "Inactivo"
        SUSPENDIDO = "SUSPENDIDO", "Suspendido"
        BLOQUEADO_CREDITO = "BLOQUEADO_CREDITO", "Bloqueado por crédito"
        EN_EVALUACION = "EN_EVALUACION", "En evaluación"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="clientes_comerciales")
    codigo = models.CharField(max_length=30)
    tipo_cliente = models.CharField(max_length=40, choices=Tipo.choices)
    nombre_comercial = models.CharField(max_length=255)
    razon_social = models.CharField(max_length=255, blank=True)
    rnc_cedula = models.CharField("RNC o cédula", max_length=30, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    whatsapp = models.CharField(max_length=50, blank=True)
    correo = models.EmailField(blank=True)
    direccion_fiscal = models.TextField(blank=True)
    provincia = models.CharField(max_length=100, blank=True)
    municipio = models.CharField(max_length=100, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    requiere_ncf = models.BooleanField(default=False)
    tipo_comprobante_preferido = models.CharField(max_length=30, blank=True)
    contribuyente = models.BooleanField(default=False)
    condicion_pago = models.CharField(max_length=10, choices=CondicionPago.choices, default=CondicionPago.CONTADO)
    dias_credito = models.PositiveIntegerField(default=0)
    limite_credito = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    descuento_maximo = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
    )
    lista_precio = models.CharField(max_length=100, blank=True)
    vendedor_asignado = models.CharField(max_length=150, blank=True)
    ruta_asignada = models.CharField(max_length=150, blank=True)
    observaciones = models.TextField(blank=True)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.ACTIVO)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="clientes_creados")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre_comercial", "codigo"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo"], name="comercial_cliente_empresa_codigo_uniq"),
            models.CheckConstraint(condition=Q(limite_credito__gte=0), name="comercial_cliente_limite_no_negativo"),
            models.CheckConstraint(condition=Q(descuento_maximo__gte=0, descuento_maximo__lte=100), name="comercial_cliente_descuento_rango"),
        ]
        indexes = [
            models.Index(fields=["empresa", "estado"], name="com_cli_emp_estado_idx"),
            models.Index(fields=["empresa", "nombre_comercial"], name="com_cli_emp_nombre_idx"),
            models.Index(fields=["empresa", "rnc_cedula"], name="com_cli_emp_rnc_idx"),
        ]

    def clean(self):
        errors = {}
        if self.condicion_pago == self.CondicionPago.CONTADO and self.dias_credito != 0:
            errors["dias_credito"] = "Los clientes de contado deben tener cero días de crédito."
        if self.limite_credito is not None and self.limite_credito < 0:
            errors["limite_credito"] = "El límite de crédito no puede ser negativo."
        if self.descuento_maximo is not None and not 0 <= self.descuento_maximo <= 100:
            errors["descuento_maximo"] = "El descuento máximo debe estar entre 0 y 100."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.codigo} - {self.nombre_comercial}"


class DireccionCliente(models.Model):
    class Tipo(models.TextChoices):
        FISCAL = "FISCAL", "Fiscal"
        ENTREGA = "ENTREGA", "Entrega"
        COBRO = "COBRO", "Cobro"
        OTRO = "OTRO", "Otro"

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="direcciones")
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    direccion = models.TextField()
    provincia = models.CharField(max_length=100, blank=True)
    municipio = models.CharField(max_length=100, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    referencia = models.TextField(blank=True)
    latitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    contacto_recepcion = models.CharField(max_length=150, blank=True)
    telefono_recepcion = models.CharField(max_length=50, blank=True)
    horario_recepcion = models.CharField(max_length=150, blank=True)
    instrucciones_entrega = models.TextField(blank=True)
    es_principal = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-es_principal", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "tipo"],
                condition=Q(es_principal=True, activa=True),
                name="comercial_direccion_principal_activa_uniq",
            )
        ]

    def clean(self):
        if self.es_principal and self.activa:
            iguales = type(self).objects.filter(
                cliente=self.cliente, tipo=self.tipo, es_principal=True, activa=True
            )
            if self.pk:
                iguales = iguales.exclude(pk=self.pk)
            if iguales.exists():
                raise ValidationError({"es_principal": "Ya existe una dirección principal activa de este tipo."})

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class ContactoCliente(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="contactos")
    nombre = models.CharField(max_length=150)
    cargo = models.CharField(max_length=120, blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    whatsapp = models.CharField(max_length=50, blank=True)
    correo = models.EmailField(blank=True)
    es_principal = models.BooleanField(default=False)
    recibe_facturas = models.BooleanField(default=False)
    recibe_cobros = models.BooleanField(default=False)
    recibe_entregas = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-es_principal", "nombre"]

    def __str__(self):
        return f"{self.nombre} - {self.cliente.nombre_comercial}"
