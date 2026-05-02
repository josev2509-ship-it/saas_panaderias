from django.db import models


# ==========================
# EMPRESA
# ==========================
class Empresa(models.Model):
    nombre = models.CharField(max_length=255)
    rnc = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)

    numero_inicial_conduce = models.CharField(max_length=20, default="0001")

    def __str__(self):
        return self.nombre


# ==========================
# CENTRO EDUCATIVO
# ==========================
class CentroEducativo(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=255)
    director = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    provincia = models.CharField(max_length=100, blank=True, null=True)
    regional_distrito = models.CharField(max_length=100, blank=True, null=True)
    matricula = models.IntegerField(default=0)
    orden_carga = models.PositiveIntegerField(default=0)

    latitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    class Meta:
        ordering = ["orden_carga", "id"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# ==========================
# MENÚ DIARIO
# ==========================
class MenuDiario(models.Model):
    fecha = models.DateField(unique=True)
    producto = models.CharField(max_length=255)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.fecha} - {self.producto}"


# ==========================
# CONDUCE
# ==========================
class Conduce(models.Model):
    ESTADOS = (
        ("borrador", "Borrador"),
        ("generado", "Generado"),
        ("entregado", "Entregado"),
        ("anulado", "Anulado"),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    numero = models.CharField(max_length=20, unique=True, blank=True, null=True)
    fecha = models.DateField()
    centro = models.ForeignKey(CentroEducativo, on_delete=models.CASCADE)
    producto = models.CharField(max_length=255)
    cantidad = models.IntegerField(default=0)
    observaciones = models.TextField(blank=True, null=True)

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="borrador"
    )

    class Meta:
        ordering = ["-fecha", "-id"]

    def save(self, *args, **kwargs):
        if not self.numero:
            formato_base = str(self.empresa.numero_inicial_conduce or "0001")
            conduces_empresa = Conduce.objects.filter(empresa=self.empresa)

            numeros_validos = []
            largo_formato = len(formato_base)

            for conduce in conduces_empresa:
                if conduce.numero and str(conduce.numero).isdigit():
                    numeros_validos.append(int(conduce.numero))
                    largo_formato = max(largo_formato, len(str(conduce.numero)))

            nuevo_numero = max(numeros_validos) + 1 if numeros_validos else int(formato_base)
            self.numero = str(nuevo_numero).zfill(largo_formato)

        if not self.cantidad or self.cantidad == 0:
            self.cantidad = self.centro.matricula

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Conduce {self.numero} - {self.centro.nombre}"


# ==========================
# PRODUCTOS DE FACTURACIÓN
# ==========================
class ProductoFacturacion(models.Model):
    CATEGORIAS = (
        ("PAN", "PAN"),
        ("PAN_CON_VEGETALES", "PAN CON VEGETALES"),
        ("GALLETA", "GALLETA"),
        ("BIZCOCHO", "BIZCOCHO"),
    )

    categoria = models.CharField(max_length=50, choices=CATEGORIAS, unique=True)
    nombre_factura = models.CharField(max_length=100)
    precio_sin_itbis = models.DecimalField(max_digits=12, decimal_places=2)
    aplica_itbis = models.BooleanField(default=True)
    porcentaje_itbis = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.nombre_factura} - RD$ {self.precio_sin_itbis}"


# ==========================
# COMPROBANTE GUBERNAMENTAL
# ==========================
class ComprobanteFiscal(models.Model):
    TIPO_NCF = (
        ("GUBERNAMENTAL", "Factura gubernamental"),
    )

    tipo = models.CharField(
        max_length=30,
        choices=TIPO_NCF,
        default="GUBERNAMENTAL"
    )

    ncf = models.CharField(max_length=20, unique=True)
    fecha_validez = models.DateField()
    usado = models.BooleanField(default=False)
    fecha_uso = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["ncf"]
        verbose_name = "Comprobante gubernamental"
        verbose_name_plural = "Comprobantes gubernamentales"

    def __str__(self):
        estado = "Usado" if self.usado else "Disponible"
        return f"{self.ncf} - {estado}"


# ==========================
# RANGO DE NCF GUBERNAMENTAL
# ==========================
class RangoComprobanteGubernamental(models.Model):
    prefijo = models.CharField(max_length=3, default="B15")
    numero_desde = models.PositiveIntegerField()
    numero_hasta = models.PositiveIntegerField()
    fecha_validez = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Rango de comprobantes gubernamentales"
        verbose_name_plural = "Rangos de comprobantes gubernamentales"

    def __str__(self):
        return f"{self.prefijo}{str(self.numero_desde).zfill(8)} - {self.prefijo}{str(self.numero_hasta).zfill(8)}"


# ==========================
# FACTURA
# ==========================
class Factura(models.Model):
    ESTADOS = (
        ("borrador", "Borrador"),
        ("emitida", "Emitida"),
        ("anulada", "Anulada"),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    comprobante = models.ForeignKey(
        ComprobanteFiscal,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    cliente_nombre = models.CharField(
        max_length=255,
        default="INSTITUTO NACIONAL DE BIENESTAR ESTUDIANTIL"
    )
    cliente_rnc = models.CharField(max_length=20, default="401-50561-4")

    fecha_factura = models.DateField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    cantidad_conduces = models.IntegerField(default=0)
    conduce_inicial = models.CharField(max_length=20, blank=True, null=True)
    conduce_final = models.CharField(max_length=20, blank=True, null=True)

    bloques = models.PositiveIntegerField(default=1)

    subtotal_exento = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    subtotal_gravado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    itbis = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    estado = models.CharField(max_length=20, choices=ESTADOS, default="borrador")
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_factura", "-id"]

    def __str__(self):
        ncf = self.comprobante.ncf if self.comprobante else "Sin NCF"
        return f"Factura {ncf} - {self.fecha_factura}"


# ==========================
# DETALLE DE FACTURA
# ==========================
class DetalleFactura(models.Model):
    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name="detalles"
    )

    producto = models.CharField(max_length=100)
    categoria = models.CharField(max_length=50)
    cantidad = models.IntegerField(default=0)
    precio_sin_itbis = models.DecimalField(max_digits=12, decimal_places=2)
    aplica_itbis = models.BooleanField(default=True)
    valor = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.producto} - {self.cantidad}"