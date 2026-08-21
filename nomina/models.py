from django.core.validators import MinValueValidator
from django.db import models


class Base(models.Model):
    empresa = models.ForeignKey("conduces.Empresa", on_delete=models.CASCADE)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class TipoNomina(Base):
    nombre = models.CharField(max_length=100)
    periodicidad = models.CharField(max_length=15)


class PeriodoNomina(Base):
    tipo = models.ForeignKey(TipoNomina, on_delete=models.PROTECT)
    desde = models.DateField()
    hasta = models.DateField()
    estado = models.CharField(max_length=15, default="ABIERTO")


class ConceptoNomina(Base):
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=12, choices=[("INGRESO", "Ingreso"), ("DEDUCCION", "Deducción"), ("APORTE", "Aporte")])
    gravable = models.BooleanField(default=False)
    cotiza_tss = models.BooleanField(default=False)
    cotiza_infotep = models.BooleanField(default=False)
    recurrencia = models.CharField(max_length=20, default="PERIODO")
    origen = models.CharField(max_length=30, default="CONFIGURACION")
    vigente_desde = models.DateField(null=True, blank=True)
    vigente_hasta = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)


class ReglaNomina(Base):
    concepto = models.ForeignKey(ConceptoNomina, on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)
    condiciones = models.JSONField(default=dict)
    formula = models.JSONField(default=dict)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True)


class ParametroLegalNomina(Base):
    """Versión inmutable de tasas y escalas aplicables a una fecha de nómina."""

    nombre = models.CharField(max_length=120)
    version = models.PositiveIntegerField(default=1)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)
    sfs_empleado = models.DecimalField(max_digits=8, decimal_places=6)
    afp_empleado = models.DecimalField(max_digits=8, decimal_places=6)
    sfs_empleador = models.DecimalField(max_digits=8, decimal_places=6)
    svds_empleador = models.DecimalField(max_digits=8, decimal_places=6)
    srl_fijo = models.DecimalField(max_digits=8, decimal_places=6)
    srl_variable = models.DecimalField(max_digits=8, decimal_places=6, default=0)
    infotep_empleador = models.DecimalField(max_digits=8, decimal_places=6, default=0)
    tope_sfs = models.DecimalField(max_digits=18, decimal_places=2)
    tope_svds = models.DecimalField(max_digits=18, decimal_places=2)
    tope_srl = models.DecimalField(max_digits=18, decimal_places=2)
    escala_isr = models.JSONField(default=list)
    fuentes = models.JSONField(default=list)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("-vigente_desde", "-version")
        constraints = [models.UniqueConstraint(fields=("empresa", "version"), name="nomina_param_legal_empresa_version_uniq")]


class NovedadNomina(Base):
    empleado = models.ForeignKey("rrhh.Empleado", on_delete=models.PROTECT)
    concepto = models.ForeignKey(ConceptoNomina, on_delete=models.PROTECT)
    periodo = models.ForeignKey(PeriodoNomina, on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=15, default="APROBADA")


class PrestamoEmpleado(Base):
    TIPOS = [("PRESTAMO", "Préstamo"), ("ADELANTO", "Adelanto"), ("UNICO", "Descuento único"), ("RECURRENTE", "Descuento recurrente"), ("OTRO", "Otro")]
    ESTADOS = [("BORRADOR", "Borrador"), ("ACTIVO", "Activo"), ("PAGADO", "Pagado"), ("SUSPENDIDO", "Suspendido"), ("CANCELADO", "Cancelado")]
    codigo = models.CharField(max_length=30, blank=True)
    empleado = models.ForeignKey("rrhh.Empleado", on_delete=models.PROTECT, related_name="prestamos_descuentos")
    tipo = models.CharField(max_length=15, choices=TIPOS, default="PRESTAMO")
    fecha = models.DateField(null=True, blank=True)
    principal = models.DecimalField(max_digits=18, decimal_places=2)
    saldo = models.DecimalField(max_digits=18, decimal_places=2)
    cuotas = models.PositiveIntegerField()
    monto_cuota = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    primera_nomina = models.ForeignKey("PeriodoNomina", on_delete=models.PROTECT, null=True, blank=True)
    observacion = models.TextField(blank=True)
    documento_soporte = models.FileField(upload_to="nomina/prestamos/", blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default="BORRADOR")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("empresa", "codigo"), name="nomina_prestamo_empresa_codigo_uniq")]


class CuotaPrestamoEmpleado(models.Model):
    prestamo = models.ForeignKey(PrestamoEmpleado, on_delete=models.CASCADE, related_name="cuotas_detalle")
    numero = models.PositiveIntegerField()
    monto = models.DecimalField(max_digits=18, decimal_places=2)
    pagada = models.BooleanField(default=False)
    nomina = models.ForeignKey("Nomina", on_delete=models.PROTECT, null=True, blank=True, related_name="cuotas_prestamos")
    fecha = models.DateField(null=True, blank=True)
    saldo_anterior = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    saldo_posterior = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    estado = models.CharField(max_length=15, default="PROVISIONAL", choices=[("PROVISIONAL","Provisional"),("APLICADA","Aplicada"),("REVERSADA","Reversada")])

    class Meta:
        constraints = [models.UniqueConstraint(fields=("prestamo", "nomina"), condition=models.Q(nomina__isnull=False), name="nomina_cuota_prestamo_nomina_uniq")]


class EmbargoEmpleado(Base):
    empleado = models.ForeignKey("rrhh.Empleado", on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=18, decimal_places=2)
    saldo = models.DecimalField(max_digits=18, decimal_places=2)
    referencia = models.CharField(max_length=80)


class Nomina(Base):
    numero = models.CharField(max_length=30)
    periodo = models.OneToOneField(PeriodoNomina, on_delete=models.PROTECT)
    estado = models.CharField(max_length=15, default="BORRADOR")
    total_ingresos = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_deducciones = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_neto = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_afp = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_sfs = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_isr = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_otros_descuentos = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_aportes_patronales = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    snapshot_reglas = models.JSONField(default=dict)


class DetalleNominaEmpleado(models.Model):
    nomina = models.ForeignKey(Nomina, on_delete=models.CASCADE, related_name="detalles")
    empleado = models.ForeignKey("rrhh.Empleado", on_delete=models.PROTECT)
    ingresos = models.DecimalField(max_digits=18, decimal_places=2)
    deducciones = models.DecimalField(max_digits=18, decimal_places=2)
    aportes = models.DecimalField(max_digits=18, decimal_places=2)
    neto = models.DecimalField(max_digits=18, decimal_places=2)
    salario_periodo = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    horas_extra = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    otros_ingresos = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    afp_empleado = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    sfs_empleado = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    isr = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    otros_descuentos = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    sfs_empleador = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    svds_empleador = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    srl_empleador = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    infotep_empleador = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    snapshot = models.JSONField(default=dict)
    alerta = models.CharField(max_length=250, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("nomina", "empleado"), name="nomina_detalle_empleado_uniq")]


class LineaDetalleNomina(models.Model):
    detalle = models.ForeignKey(DetalleNominaEmpleado, on_delete=models.CASCADE, related_name="lineas")
    concepto = models.ForeignKey(ConceptoNomina, on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=18, decimal_places=2)
    snapshot = models.JSONField(default=dict)


class ReciboNomina(models.Model):
    detalle = models.OneToOneField(DetalleNominaEmpleado, on_delete=models.PROTECT)
    numero = models.CharField(max_length=30)
    archivo = models.FileField(upload_to="nomina/recibos/", blank=True)
    snapshot = models.JSONField(default=dict)
    generado_en = models.DateTimeField(auto_now=True)


class LiquidacionLaboral(Base):
    empleado = models.ForeignKey("rrhh.Empleado", on_delete=models.PROTECT)
    fecha = models.DateField()
    fecha_salida = models.DateField(null=True, blank=True)
    tipo_terminacion = models.CharField(max_length=30, default="DESAHUCIO")
    salario_promedio = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    salario_diario = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=18, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=20, default="BORRADOR")
    requiere_revision = models.BooleanField(default=False)
    motivo_revision = models.CharField(max_length=250, blank=True)
    snapshot = models.JSONField(default=dict)


class PrestacionLaboral(models.Model):
    liquidacion = models.ForeignKey(LiquidacionLaboral, on_delete=models.CASCADE, related_name="prestaciones")
    tipo = models.CharField(max_length=30)
    dias = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    base = models.DecimalField(max_digits=18, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    formula = models.CharField(max_length=250, blank=True)
    referencia_legal = models.CharField(max_length=120, blank=True)
    monto = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0)])


class PlantillaDocumentoRRHH(Base):
    TIPOS = [("VOLANTE", "Volante de pago"), ("NOMINA", "Resumen de nómina"), ("PRESTACIONES", "Cálculo de prestaciones"), ("LIQUIDACION", "Carta de liquidación"), ("LABORAL", "Carta laboral"), ("CONSULAR", "Carta consular"), ("BANCARIA", "Carta bancaria"), ("CONTRATO", "Contrato"), ("ANEXO", "Anexo de funciones")]
    tipo = models.CharField(max_length=20, choices=TIPOS)
    encabezado = models.TextField(blank=True)
    firmante = models.CharField(max_length=150, blank=True)
    cargo_firmante = models.CharField(max_length=150, blank=True)
    pie = models.TextField(blank=True)
    cuerpo = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("empresa", "tipo"), name="nomina_plantilla_tipo_uniq")]


class RegaliaPascual(Base):
    empleado = models.ForeignKey("rrhh.Empleado", on_delete=models.PROTECT)
    anio = models.PositiveIntegerField()
    monto = models.DecimalField(max_digits=18, decimal_places=2)


class HistorialNomina(models.Model):
    nomina = models.ForeignKey(Nomina, on_delete=models.CASCADE, related_name="historial")
    estado_anterior = models.CharField(max_length=15)
    estado_nuevo = models.CharField(max_length=15)
    fecha = models.DateTimeField(auto_now_add=True)
