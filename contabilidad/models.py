from django.db import models
from django.contrib.auth.models import User


# =====================================================
# SOCIOS
# =====================================================

class Socio(models.Model):
    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


# =====================================================
# APORTES DE SOCIOS
# =====================================================

class AporteSocio(models.Model):
    socio = models.ForeignKey(
        Socio,
        on_delete=models.CASCADE,
        related_name="aportes"
    )

    monto = models.DecimalField(max_digits=14, decimal_places=2)
    fecha = models.DateField()
    descripcion = models.TextField(blank=True, null=True)

    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.socio.nombre} - RD${self.monto}"


# =====================================================
# DEUDAS SOCIOS
# =====================================================

class DeudaSocio(models.Model):
    TIPO_CHOICES = (
        ("empresa_debe", "Empresa debe al socio"),
        ("socio_debe", "Socio debe a la empresa"),
    )

    socio = models.ForeignKey(
        Socio,
        on_delete=models.CASCADE,
        related_name="deudas"
    )

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    fecha = models.DateField()
    descripcion = models.TextField(blank=True, null=True)
    pagada = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.socio.nombre} - {self.get_tipo_display()} - RD${self.monto}"


# =====================================================
# GASTOS / FACTURAS
# =====================================================

class Gasto(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("pagado", "Pagado"),
        ("vencido", "Vencido"),
    ]

    proveedor = models.CharField(max_length=255)
    rnc = models.CharField(max_length=20, blank=True, null=True)
    ncf = models.CharField(max_length=30, blank=True, null=True)
    concepto = models.TextField()
    fecha_factura = models.DateField()
    fecha_vencimiento = models.DateField(blank=True, null=True)

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    itbis = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2)

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="pendiente"
    )

    relacionado_empresa = models.BooleanField(default=True)

    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.proveedor} - RD${self.total}"


# =====================================================
# FACTORING / UMPI
# =====================================================

class Factoring(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("depositado", "Depositado"),
        ("cerrado", "Cerrado"),
    ]

    entidad = models.CharField(max_length=255, default="UMPI")
    numero_factura = models.CharField(max_length=50)
    monto_factura = models.DecimalField(max_digits=14, decimal_places=2)
    fecha_factura = models.DateField()
    fecha_estimada_pago = models.DateField(blank=True, null=True)

    porcentaje_anticipo = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    porcentaje_retencion = models.DecimalField(max_digits=5, decimal_places=2, default=25)
    porcentaje_servicio = models.DecimalField(max_digits=5, decimal_places=2, default=5)

    deuda_materia_prima = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    monto_estimado_deposito = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="pendiente"
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.numero_factura


# =====================================================
# PAGOS FACTORING
# =====================================================

class PagoFactoring(models.Model):
    factoring = models.ForeignKey(
        Factoring,
        on_delete=models.CASCADE,
        related_name="pagos"
    )

    fecha = models.DateField()
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    observacion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.factoring.numero_factura} - RD${self.monto}"


# =====================================================
# CUENTAS POR PAGAR
# =====================================================

class CuentaPorPagar(models.Model):
    proveedor = models.CharField(max_length=255)
    concepto = models.TextField()
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    fecha_vencimiento = models.DateField()
    pagada = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.proveedor


# =====================================================
# CUENTAS POR COBRAR
# =====================================================

class CuentaPorCobrar(models.Model):
    cliente = models.CharField(max_length=255)
    concepto = models.TextField()
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    fecha_vencimiento = models.DateField()
    cobrada = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.cliente


# =====================================================
# PRESUPUESTOS
# =====================================================

class Presupuesto(models.Model):
    nombre = models.CharField(max_length=255)
    año = models.IntegerField()
    descripcion = models.TextField(blank=True, null=True)
    monto_estimado = models.DecimalField(max_digits=14, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} - {self.año}"
    # =====================================================
# DETALLE 606 DGII
# =====================================================

class TipoBienesServicios(models.Model):

    codigo = models.CharField(
        max_length=2,
        unique=True
    )

    nombre = models.CharField(
        max_length=255
    )

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# =====================================================
# PROVEEDORES
# =====================================================

class Proveedor(models.Model):

    nombre = models.CharField(
        max_length=255
    )

    rnc = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    nombre_comercial = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    correo = models.EmailField(
        blank=True,
        null=True
    )

    direccion = models.TextField(
        blank=True,
        null=True
    )

    estado_dgii = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    actividad_economica = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    provincia = models.CharField(
        max_length=120,
        blank=True,
        null=True
    )

    municipio = models.CharField(
        max_length=120,
        blank=True,
        null=True
    )

    consultado_dgii = models.BooleanField(
        default=False
    )

    activo = models.BooleanField(
        default=True
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.nombre


# =====================================================
# FACTURAS 606
# =====================================================

class Factura606(models.Model):

    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("PAGADA", "Pagada"),
        ("VENCIDA", "Vencida"),
    ]

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE
    )

    tipo_bienes_servicios = models.ForeignKey(
        TipoBienesServicios,
        on_delete=models.SET_NULL,
        null=True
    )

    numero_comprobante = models.CharField(
        max_length=30
    )

    ncf_modificado = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    fecha_comprobante = models.DateField()

    fecha_pago = models.DateField(
        blank=True,
        null=True
    )

    monto_facturado = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    itbis_facturado = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    retencion_renta = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    retencion_itbis = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    total_pagado = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="PENDIENTE"
    )

    relacionado_empresa = models.BooleanField(
        default=True
    )

    agregado_por_socio = models.BooleanField(
        default=False
    )

    socio_relacionado = models.ForeignKey(
        Socio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    observacion = models.TextField(
        blank=True,
        null=True
    )

    fecha_vencimiento = models.DateField(
        blank=True,
        null=True
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.numero_comprobante

from .enterprise_models import *  # noqa: E402,F401,F403
