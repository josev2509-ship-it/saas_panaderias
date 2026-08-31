from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
import secrets

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
    modulo_catalogos = models.BooleanField(default=True)
    modulo_compras = models.BooleanField(default=False)
    modulo_workflow = models.BooleanField(default=False)
    modulo_inabie = models.BooleanField(default=False)

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
class ConduceQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(eliminado_en__isnull=True)


class ConduceManager(models.Manager.from_queryset(ConduceQuerySet)):
    def get_queryset(self):
        return super().get_queryset().activos()


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
    eliminado_en = models.DateTimeField(null=True, blank=True, db_index=True)
    eliminado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conduces_eliminados",
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="borrador"
    )

    objects = ConduceManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-fecha", "-id"]

    def save(self, *args, **kwargs):
        if not self.numero:
            formato_base = str(self.empresa.numero_inicial_conduce or "0001")
            # La numeracion considera tambien bajas logicas para no reutilizar
            # identificadores documentales previamente emitidos.
            conduces_empresa = Conduce.all_objects.filter(empresa=self.empresa)

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

    def eliminar_logicamente(self, usuario=None):
        if self.eliminado_en is not None:
            return False

        self.eliminado_en = timezone.now()
        self.eliminado_por = usuario if getattr(usuario, "is_authenticated", False) else None
        self.save(update_fields=("eliminado_en", "eliminado_por"))
        return True

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
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = f"{secrets.randbelow(900000) + 100000:06d}"

        if not self.expira_en:
            self.expira_en = timezone.now() + timedelta(minutes=15)

        super().save(*args, **kwargs)

    def esta_vigente(self):
        return not self.usado and timezone.now() <= self.expira_en

    def __str__(self):
        return f"Validación {self.tipo} · usuario {self.user_id}"
    # ==========================
# CALENDARIO ESCOLAR / DÍAS NO LABORABLES
# ==========================
class DiaNoDocencia(models.Model):
    TIPOS = (
        ("feriado", "Feriado"),
        ("no_docencia", "No docencia"),
        ("suspension", "Suspensión de clases"),
        ("otro", "Otro"),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    fecha = models.DateField()
    motivo = models.CharField(max_length=255)
    tipo = models.CharField(max_length=30, choices=TIPOS, default="feriado")
    observacion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["fecha"]
        unique_together = ("empresa", "fecha", "motivo")
        verbose_name = "Día no docencia"
        verbose_name_plural = "Días no docencia"

    def __str__(self):
        return f"{self.fecha} - {self.motivo}"


class CalendarioEscolar(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        EN_REVISION = "EN_REVISION", "En revision"
        ACTIVO = "ACTIVO", "Activo"
        CERRADO = "CERRADO", "Cerrado"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="calendarios_escolares")
    nombre = models.CharField(max_length=120)
    anio_inicio = models.PositiveSmallIntegerField()
    anio_fin = models.PositiveSmallIntegerField()
    inicio_docencia = models.DateField()
    fin_docencia = models.DateField()
    dias_docencia_oficiales = models.PositiveSmallIntegerField(default=190)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)
    documento_fuente = models.FileField(upload_to="calendarios_escolares/", blank=True, null=True)
    diferencia_justificada = models.TextField(blank=True)
    activado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="calendarios_activados")
    activado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-anio_inicio", "empresa_id")
        constraints = [models.UniqueConstraint(fields=("empresa", "anio_inicio", "anio_fin"), name="cal_escolar_empresa_anio_uniq")]
        permissions = [("activar_calendario_escolar", "Puede activar calendario escolar")]

    def clean(self):
        if self.anio_fin != self.anio_inicio + 1:
            raise ValidationError({"anio_fin": "El ano escolar debe abarcar anos consecutivos."})
        if self.inicio_docencia > self.fin_docencia:
            raise ValidationError({"fin_docencia": "La fecha final debe ser posterior al inicio."})

    def __str__(self):
        return f"{self.nombre} ({self.anio_inicio}-{self.anio_fin})"


class DiaCalendarioEscolar(models.Model):
    class Clasificacion(models.TextChoices):
        DOCENCIA = "DOCENCIA", "Docencia"
        FERIADO = "FERIADO", "Feriado"
        VACACIONES = "VACACIONES", "Vacaciones"
        NO_LECTIVO = "NO_LECTIVO", "No lectivo"
        SUSPENSION = "SUSPENSION", "Suspension"
        REQUIERE_REVISION = "REQUIERE_REVISION", "Requiere revision"

    calendario = models.ForeignKey(CalendarioEscolar, on_delete=models.CASCADE, related_name="dias")
    fecha = models.DateField()
    clasificacion = models.CharField(max_length=25, choices=Clasificacion.choices, default=Clasificacion.REQUIERE_REVISION)
    motivo = models.CharField(max_length=255, blank=True)
    origen = models.CharField(max_length=30, default="MANUAL")
    ajustado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="dias_calendario_ajustados")
    ajustado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("fecha",)
        constraints = [models.UniqueConstraint(fields=("calendario", "fecha"), name="dia_calendario_fecha_uniq")]

    def clean(self):
        if self.calendario_id and not (self.calendario.inicio_docencia <= self.fecha <= self.calendario.fin_docencia):
            raise ValidationError({"fecha": "La fecha queda fuera de la vigencia del calendario."})


class ProgramaMenu(models.Model):
    class Modalidad(models.TextChoices):
        REGULAR = "REGULAR", "Regular"
        PREPARA = "PREPARA", "PREPARA"
        OTRA = "OTRA", "Otra"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="programas_menu")
    codigo = models.CharField(max_length=40)
    nombre = models.CharField(max_length=160)
    modalidad = models.CharField(max_length=20, choices=Modalidad.choices)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("modalidad", "nombre")
        constraints = [models.UniqueConstraint(fields=("empresa", "codigo"), name="programa_menu_empresa_codigo_uniq")]

    def __str__(self):
        return f"{self.nombre} - {self.get_modalidad_display()}"


class VersionProgramaMenu(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ACTIVA = "ACTIVA", "Activa"
        CERRADA = "CERRADA", "Cerrada"

    class InicioCiclo(models.TextChoices):
        CONTINUAR = "CONTINUAR", "Continuar ciclo existente"
        REINICIAR = "REINICIAR", "Reiniciar en semana 1"
        ESPECIFICA = "ESPECIFICA", "Iniciar en semana especifica"

    programa = models.ForeignKey(ProgramaMenu, on_delete=models.PROTECT, related_name="versiones")
    nombre = models.CharField(max_length=80)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)
    semanas_ciclo = models.PositiveSmallIntegerField(default=5)
    fecha_ancla_ciclo = models.DateField()
    modo_inicio_ciclo = models.CharField(max_length=15, choices=InicioCiclo.choices, default=InicioCiclo.REINICIAR)
    semana_inicial = models.PositiveSmallIntegerField(default=1)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.BORRADOR)
    documento_fuente = models.FileField(upload_to="programas_menu/", blank=True, null=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="versiones_menu_creadas")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("programa_id", "-vigente_desde")
        constraints = [models.UniqueConstraint(fields=("programa", "nombre"), name="version_programa_nombre_uniq")]

    def clean(self):
        if self.vigente_hasta and self.vigente_hasta < self.vigente_desde:
            raise ValidationError({"vigente_hasta": "La vigencia final no puede preceder a la inicial."})
        if not 1 <= self.semana_inicial <= self.semanas_ciclo:
            raise ValidationError({"semana_inicial": "La semana inicial debe pertenecer al ciclo."})

    def __str__(self):
        return f"{self.programa.nombre} / {self.nombre}"


class ItemCicloMenu(models.Model):
    version = models.ForeignKey(VersionProgramaMenu, on_delete=models.PROTECT, related_name="items")
    semana = models.PositiveSmallIntegerField()
    dia_semana = models.PositiveSmallIntegerField(help_text="0=Lunes, 6=Domingo")
    producto = models.CharField(max_length=180, blank=True)
    es_suministrado = models.BooleanField(default=True, help_text="Desmarcar para bebidas u otros componentes no suministrados.")
    observacion = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("semana", "dia_semana")
        constraints = [models.UniqueConstraint(fields=("version", "semana", "dia_semana"), name="item_ciclo_semana_dia_uniq")]

    def clean(self):
        if self.version_id and not 1 <= self.semana <= self.version.semanas_ciclo:
            raise ValidationError({"semana": "La semana no pertenece al ciclo configurado."})
        if not 0 <= self.dia_semana <= 6:
            raise ValidationError({"dia_semana": "El dia debe estar entre lunes (0) y domingo (6)."})
        if self.es_suministrado and not self.producto.strip():
            raise ValidationError({"producto": "Indique el producto suministrado."})


class AsignacionProgramaCentro(models.Model):
    centro = models.ForeignKey(CentroEducativo, on_delete=models.PROTECT, related_name="asignaciones_menu")
    programa = models.ForeignKey(ProgramaMenu, on_delete=models.PROTECT, related_name="asignaciones_centros")
    modalidad = models.CharField(max_length=20, choices=ProgramaMenu.Modalidad.choices)
    dias_entrega = models.JSONField(default=list, help_text="Dias Python: lunes=0, domingo=6")
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("centro_id", "-vigente_desde")

    def clean(self):
        if self.centro_id and self.programa_id and self.centro.empresa_id != self.programa.empresa_id:
            raise ValidationError("El centro y el programa deben pertenecer a la misma empresa.")
        if self.modalidad != self.programa.modalidad:
            raise ValidationError({"modalidad": "La modalidad debe coincidir con el programa."})
        if any(not isinstance(dia, int) or dia < 0 or dia > 6 for dia in self.dias_entrega):
            raise ValidationError({"dias_entrega": "Los dias configurados no son validos."})
        if self.vigente_hasta and self.vigente_hasta < self.vigente_desde:
            raise ValidationError({"vigente_hasta": "La vigencia final no puede preceder a la inicial."})


class ProgramacionMenuEscolar(models.Model):
    class Estado(models.TextChoices):
        PROGRAMADO = "PROGRAMADO", "Programado"
        SIN_DOCENCIA = "SIN_DOCENCIA", "Sin docencia"
        NO_PROGRAMADO = "NO_PROGRAMADO", "No programado"
        NO_SUMINISTRADO = "NO_SUMINISTRADO", "Componente no suministrado"
        OMITIDO = "OMITIDO", "Omitido por excepcion"
        EXTRAORDINARIO = "EXTRAORDINARIO", "Entrega extraordinaria"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="programaciones_menu")
    calendario = models.ForeignKey(CalendarioEscolar, on_delete=models.PROTECT, related_name="programaciones")
    asignacion = models.ForeignKey(AsignacionProgramaCentro, on_delete=models.PROTECT, related_name="programaciones")
    centro = models.ForeignKey(CentroEducativo, on_delete=models.PROTECT, related_name="programaciones_menu")
    fecha = models.DateField()
    dia_semana = models.PositiveSmallIntegerField()
    semana_ciclo = models.PositiveSmallIntegerField(null=True, blank=True)
    programa = models.ForeignKey(ProgramaMenu, on_delete=models.PROTECT)
    version = models.ForeignKey(VersionProgramaMenu, on_delete=models.PROTECT)
    item_ciclo = models.ForeignKey(ItemCicloMenu, on_delete=models.PROTECT, null=True, blank=True)
    producto = models.CharField(max_length=180, blank=True)
    programa_snapshot = models.CharField(max_length=160)
    version_snapshot = models.CharField(max_length=80)
    modalidad_snapshot = models.CharField(max_length=20)
    estado = models.CharField(max_length=20, choices=Estado.choices)
    confirmada = models.BooleanField(default=False)
    bloqueada = models.BooleanField(default=False)
    creada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="programaciones_menu_creadas")
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("fecha", "centro_id")
        constraints = [models.UniqueConstraint(fields=("asignacion", "fecha"), name="programacion_asignacion_fecha_uniq")]
        permissions = [("confirmar_programacion_menu", "Puede confirmar programacion de menu")]


class ExcepcionProgramacionMenu(models.Model):
    programacion = models.ForeignKey(ProgramacionMenuEscolar, on_delete=models.PROTECT, related_name="excepciones")
    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20, choices=ProgramacionMenuEscolar.Estado.choices)
    producto_anterior = models.CharField(max_length=180, blank=True)
    producto_nuevo = models.CharField(max_length=180, blank=True)
    motivo = models.TextField()
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-creado_en",)
