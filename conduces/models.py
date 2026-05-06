from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
import random

# ==========================
# EMPRESA
# ==========================
class Empresa(models.Model):
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="empresa_principal"
    )

    nombre = models.CharField(max_length=255)
    rnc = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)

    numero_inicial_conduce = models.CharField(max_length=20, default="0001")

    # Módulos personalizados por empresa
    modulo_conduces = models.BooleanField(default=True)
    modulo_centros = models.BooleanField(default=True)
    modulo_menu = models.BooleanField(default=True)
    modulo_facturacion = models.BooleanField(default=True)
    modulo_reportes = models.BooleanField(default=True)
    modulo_rutas = models.BooleanField(default=False)
    modulo_nomina = models.BooleanField(default=False)
    modulo_inventario = models.BooleanField(default=False)

    activa = models.BooleanField(default=True)

    logo = models.ImageField(
    upload_to="empresas/logos/",
    blank=True,
    null=True
)

    def __str__(self):
        return self.nombre


# ==========================
# CENTRO EDUCATIVO
# ==========================
class CentroEducativo(models.Model):
    empresa = models.ForeignKey(
    Empresa,
    on_delete=models.CASCADE,
    blank=True,
    null=True
)
    codigo = models.CharField(max_length=20)
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
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    fecha = models.DateField()
    producto = models.CharField(max_length=255)

    class Meta:
        ordering = ["-fecha"]
        unique_together = ("empresa", "fecha")

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
    empresa = models.ForeignKey(
    Empresa,
    on_delete=models.CASCADE,
    blank=True,
    null=True
)
    CATEGORIAS = (
        ("PAN", "PAN"),
        ("PAN_CON_VEGETALES", "PAN CON VEGETALES"),
        ("GALLETA", "GALLETA"),
        ("BIZCOCHO", "BIZCOCHO"),
    )

    categoria = models.CharField(max_length=50, choices=CATEGORIAS)
    nombre_factura = models.CharField(max_length=100)
    precio_sin_itbis = models.DecimalField(max_digits=12, decimal_places=2)
    aplica_itbis = models.BooleanField(default=True)
    porcentaje_itbis = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    activo = models.BooleanField(default=True)

    class Meta:
          ordering = ["id"]
          unique_together = ("empresa", "categoria")

    def __str__(self):
        return f"{self.nombre_factura} - RD$ {self.precio_sin_itbis}"


# ==========================
# COMPROBANTE / NCF
# ==========================
class ComprobanteFiscal(models.Model):
    empresa = models.ForeignKey(
    Empresa,
    on_delete=models.CASCADE,
    blank=True,
    null=True
)
    TIPO_NCF = (
        ("B01", "B01 - Crédito fiscal"),
        ("B02", "B02 - Consumo"),
        ("B14", "B14 - Régimen especial"),
        ("B15", "B15 - Gubernamental"),
        ("E31", "E31 - e-CF crédito fiscal"),
        ("E32", "E32 - e-CF consumo"),
        ("E44", "E44 - e-CF gubernamental"),
        ("OTRO", "Otro"),
    )

    tipo = models.CharField(
        max_length=30,
        choices=TIPO_NCF,
        default="B15"
    )

    ncf = models.CharField(max_length=30)
    fecha_validez = models.DateField()
    usado = models.BooleanField(default=False)
    fecha_uso = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["ncf"]
        verbose_name = "Comprobante / NCF"
        verbose_name_plural = "Comprobantes / NCF"
        unique_together = ("empresa", "ncf")

    def __str__(self):
        estado = "Usado" if self.usado else "Disponible"
        return f"{self.ncf} - {estado}"


# ==========================
# RANGO DE COMPROBANTES / NCF
# ==========================
class RangoComprobanteGubernamental(models.Model):
    prefijo = models.CharField(max_length=5, default="B15")
    numero_desde = models.PositiveIntegerField()
    numero_hasta = models.PositiveIntegerField()
    fecha_validez = models.DateField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Rango de comprobantes"
        verbose_name_plural = "Rangos de comprobantes"

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

    # ==========================
    # FACTURACIÓN ELECTRÓNICA E-CF
    # ==========================
    es_electronica = models.BooleanField(default=False)
    encf = models.CharField(max_length=30, blank=True, null=True)
    codigo_seguridad = models.CharField(max_length=20, blank=True, null=True)
    fecha_firma_digital = models.DateTimeField(blank=True, null=True)
    url_qr = models.TextField(blank=True, null=True)

    estado_dgii = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        default="pendiente"
    )

    xml_ecf = models.FileField(
        upload_to="facturas/xml/",
        blank=True,
        null=True
    )

    pdf_ecf_externo = models.FileField(
        upload_to="facturas/pdf_externo/",
        blank=True,
        null=True
    )

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
    

# ==========================
# PLANES
# ==========================
class Plan(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    limite_conduces = models.IntegerField(default=500)
    limite_usuarios = models.IntegerField(default=3)
    almacenamiento_gb = models.IntegerField(default=1)

    incluye_contabilidad = models.BooleanField(default=False)
    incluye_nomina = models.BooleanField(default=False)
    incluye_rutas = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre


# ==========================
# EMPRESA (CUENTA SaaS)
# ==========================
class EmpresaSaaS(models.Model):
    nombre = models.CharField(max_length=255)
    rnc = models.CharField(max_length=20)
    correo = models.EmailField(unique=True)

    activa = models.BooleanField(default=True)

    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


# ==========================
# SUSCRIPCIÓN
# ==========================
class Suscripcion(models.Model):
    ESTADOS = (
        ("prueba", "Prueba"),
        ("activa", "Activa"),
        ("vencida", "Vencida"),
        ("bloqueada", "Bloqueada"),
    )

    empresa = models.OneToOneField(EmpresaSaaS, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)

    estado = models.CharField(max_length=20, choices=ESTADOS, default="prueba")

    fecha_inicio = models.DateField(default=timezone.now)
    fecha_fin = models.DateField()

    en_prueba = models.BooleanField(default=True)

    def esta_activa(self):
        return self.estado in ["activa", "prueba"]

    def __str__(self):
        return f"{self.empresa.nombre} - {self.plan.nombre if self.plan else 'Sin plan'}"
    


class PerfilUsuario(models.Model):
    ROLES = (
        ("admin_empresa", "Administrador de empresa"),
        ("facturacion", "Facturación"),
        ("operaciones", "Operaciones"),
        ("chofer", "Chofer"),
        ("consulta", "Consulta"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    empresa = models.ForeignKey(EmpresaSaaS, on_delete=models.CASCADE, null=True, blank=True)
    rol = models.CharField(max_length=30, choices=ROLES, default="admin_empresa")
    correo_validado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email} - {self.rol}"


class CodigoValidacion(models.Model):
    TIPOS = (
        ("correo", "Validación de correo"),
        ("password", "Recuperación de contraseña"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    codigo = models.CharField(max_length=6)
    usado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = str(random.randint(100000, 999999))

        if not self.expira_en:
            self.expira_en = timezone.now() + timedelta(minutes=15)

        super().save(*args, **kwargs)

    def esta_vigente(self):
        return not self.usado and timezone.now() <= self.expira_en

    def __str__(self):
        return f"{self.user.email} - {self.tipo} - {self.codigo}"