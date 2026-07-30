from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

from conduces.models import Empresa


# =====================================================
# CATEGORÍAS DE INVENTARIO
# =====================================================

class CategoriaInventario(models.Model):
    TIPOS = (
        ("materia_prima", "Materia prima"),
        ("produccion", "Producción"),
        ("activo", "Activo"),
        ("empaque", "Empaque"),
        ("consumible", "Consumible"),
        ("oficina", "Material de oficina"),
        ("limpieza", "Limpieza"),
        ("transporte", "Transporte"),
        ("otro", "Otro"),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=30, choices=TIPOS, default="materia_prima")
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["tipo", "nombre"]
        unique_together = ("empresa", "nombre", "tipo")

    def __str__(self):
        return f"{self.nombre} - {self.get_tipo_display()}"


# =====================================================
# PRODUCTOS / ARTÍCULOS DE INVENTARIO
# =====================================================

class ProductoInventario(models.Model):
    TIPOS = (
        ("materia_prima", "Materia prima"),
        ("producto_terminado", "Producto terminado"),
        ("empaque", "Empaque"),
        ("consumible", "Consumible"),
        ("activo", "Activo"),
        ("oficina", "Material de oficina"),
        ("limpieza", "Limpieza"),
        ("transporte", "Transporte"),
        ("otro", "Otro"),
    )

    UNIDADES_BASE = (
        ("lb", "Libras"),
        ("oz", "Onzas"),
        ("g", "Gramos"),
        ("kg", "Kilogramos"),
        ("unidad", "Unidad"),
        ("galon", "Galón"),
        ("litro", "Litro"),
        ("paquete", "Paquete"),
        ("caja", "Caja"),
        ("yarda", "Yarda"),
    )

    CLASIFICACION_OPERATIVA = (
        ("materia_prima", "Materia prima de producción"),
        ("empaque", "Empaque"),
        ("consumible", "Consumible operativo"),
        ("limpieza", "Limpieza"),
        ("administrativo", "Administrativo"),
        ("transporte", "Transporte"),
        ("otro", "Otro"),
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE
    )

    categoria = models.ForeignKey(
        CategoriaInventario,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    codigo = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    nombre = models.CharField(
        max_length=180
    )

    tipo = models.CharField(
        max_length=30,
        choices=TIPOS,
        default="materia_prima"
    )

    clasificacion_operativa = models.CharField(
        max_length=30,
        choices=CLASIFICACION_OPERATIVA,
        default="materia_prima"
    )

    afecta_produccion = models.BooleanField(
        default=True,
        help_text="Indica si este producto debe limitar la proyección automática de producción."
    )

    unidad_medida = models.CharField(
        max_length=20,
        choices=UNIDADES_BASE,
        default="lb"
    )

    unidad_compra = models.CharField(
        max_length=120,
        blank=True,
        null=True
    )
    cantidad_por_empaque = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=1
    )

    stock_actual = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0
    )

    stock_minimo = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0
    )

    precio_unitario_compra = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0
    )

    porcentaje_itbis = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    proveedor = models.CharField(
        max_length=180,
        blank=True,
        null=True
    )

    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipo", "nombre"]
        unique_together = ("empresa", "codigo")

    def __str__(self):
        return f"{self.codigo or ''} - {self.nombre}"

    @property
    def costo_unitario(self):
        if not self.cantidad_por_empaque:
            return Decimal("0")
        return Decimal(self.precio_unitario_compra or 0) / Decimal(self.cantidad_por_empaque or 1)

    def valor_actual(self):
        return Decimal(self.stock_actual or 0) * self.costo_unitario

    def esta_bajo_minimo(self):
        return Decimal(self.stock_actual or 0) <= Decimal(self.stock_minimo or 0)

    def cantidad_empaques_completos(self):
        if not self.cantidad_por_empaque:
            return 0
        return int(Decimal(self.stock_actual or 0) // Decimal(self.cantidad_por_empaque))

    def cantidad_restante_base(self):
        if not self.cantidad_por_empaque:
            return Decimal(self.stock_actual or 0)
        return Decimal(self.stock_actual or 0) % Decimal(self.cantidad_por_empaque)

    def existencia_formateada(self):
        empaques = self.cantidad_empaques_completos()
        restante = self.cantidad_restante_base()

        if self.unidad_compra:
            return f"{empaques} {self.unidad_compra} + {restante:.2f} {self.get_unidad_medida_display()}"

        return f"{self.stock_actual:.2f} {self.get_unidad_medida_display()}"

    def subtotal_compra(self, cantidad_empaques):
        return Decimal(cantidad_empaques or 0) * Decimal(self.precio_unitario_compra or 0)

    def itbis_compra(self, cantidad_empaques):
        subtotal = self.subtotal_compra(cantidad_empaques)
        return subtotal * (Decimal(self.porcentaje_itbis or 0) / Decimal("100"))

    def total_compra(self, cantidad_empaques):
        return self.subtotal_compra(cantidad_empaques) + self.itbis_compra(cantidad_empaques)


# =====================================================
# LOTES DE INVENTARIO
# =====================================================

class LoteInventario(models.Model):
    class Estado(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", "Disponible"
        AGOTADO = "AGOTADO", "Agotado"
        BLOQUEADO = "BLOQUEADO", "Bloqueado"
        VENCIDO = "VENCIDO", "Vencido"

    class Origen(models.TextChoices):
        INICIAL = "INICIAL", "Inicial"
        COMPRA = "COMPRA", "Compra"
        PRODUCCION = "PRODUCCION", "Produccion"
        DEVOLUCION = "DEVOLUCION", "Devolucion"
        AJUSTE = "AJUSTE", "Ajuste"
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    producto = models.ForeignKey(
        ProductoInventario,
        on_delete=models.CASCADE,
        related_name="lotes"
    )

    lote = models.CharField(max_length=100)
    fecha_ingreso = models.DateField()

    fecha_vencimiento = models.DateField(
        blank=True,
        null=True
    )

    cantidad_inicial = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    cantidad_disponible = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0
    )
    cantidad_reservada = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    tipo_origen = models.CharField(max_length=20, choices=Origen.choices, default=Origen.INICIAL)
    fecha_fabricacion = models.DateField(null=True, blank=True)
    unidad_medida = models.CharField(max_length=30, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.DISPONIBLE)
    referencia_origen = models.CharField(max_length=150, blank=True)
    orden_produccion_origen = models.ForeignKey(
        "OrdenProduccion", on_delete=models.PROTECT, null=True, blank=True,
        related_name="lotes_generados",
    )
    activo = models.BooleanField(default=True)

    proveedor = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    factura = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    observacion = models.TextField(
        blank=True,
        null=True
    )

    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lotes_inventario_actualizados",
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["fecha_vencimiento", "fecha_ingreso"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "producto", "lote"], name="inv_lote_empresa_producto_numero_uniq"),
            models.CheckConstraint(condition=models.Q(cantidad_inicial__gte=0), name="inv_lote_inicial_no_negativa"),
            models.CheckConstraint(condition=models.Q(cantidad_disponible__gte=0), name="inv_lote_disponible_no_negativa"),
            models.CheckConstraint(condition=models.Q(cantidad_reservada__gte=0), name="inv_lote_reservada_no_negativa"),
            models.CheckConstraint(condition=models.Q(cantidad_reservada__lte=models.F("cantidad_disponible")), name="inv_lote_reserva_no_supera_disponible"),
        ]

    def __str__(self):
        return f"{self.producto.nombre} - {self.lote}"

    def porcentaje_disponible(self):
        if self.cantidad_inicial <= 0:
            return 0

        return round(
            (self.cantidad_disponible / self.cantidad_inicial) * 100,
            2
        )

    def esta_vencido(self):
        if not self.fecha_vencimiento:
            return False

        return timezone.now().date() > self.fecha_vencimiento

    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None

        return (self.fecha_vencimiento - timezone.now().date()).days


# =====================================================
# PRODUCTOS A PRODUCIR
# =====================================================

class ProductoProduccion(models.Model):
    TIPOS_PRODUCTO = (
        ("pan", "Pan"),
        ("pan_vegetales", "Pan con vegetales"),
        ("bizcocho", "Bizcocho"),
        ("galleta", "Galleta nutritiva"),
        ("otro", "Otro"),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=180)
    tipo = models.CharField(max_length=30, choices=TIPOS_PRODUCTO)
    unidad_resultado = models.CharField(max_length=20, default="unidad")
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["tipo", "nombre"]
        unique_together = ("empresa", "nombre")

    def __str__(self):
        return self.nombre


# =====================================================
# RECETAS
# =====================================================

class Receta(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    producto = models.ForeignKey(ProductoProduccion, on_delete=models.CASCADE)

    nombre = models.CharField(max_length=180)
    rendimiento_unidades = models.DecimalField(max_digits=14, decimal_places=4)

    activa = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True, null=True)

    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    porcentaje_variacion = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    default=0,
    help_text="Porcentaje adicional para cubrir merma, variación de peso o producción manual."
)

    class Meta:
        ordering = ["producto__nombre", "nombre"]
        unique_together = ("empresa", "producto", "nombre")

    def __str__(self):
        return f"{self.nombre} - {self.producto.nombre}"


class DetalleReceta(models.Model):
    receta = models.ForeignKey(
        Receta,
        on_delete=models.CASCADE,
        related_name="detalles"
    )

    materia_prima = models.ForeignKey(
        ProductoInventario,
        on_delete=models.PROTECT
    )

    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    unidad_medida = models.CharField(max_length=20, default="lb")
    porcentaje = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    class Meta:
        ordering = ["materia_prima__nombre"]
        unique_together = ("receta", "materia_prima")

    def __str__(self):
        return f"{self.materia_prima.nombre} - {self.cantidad} {self.unidad_medida}"

    def cantidad_por_unidad(self):
        if not self.receta.rendimiento_unidades:
            return Decimal("0")
        return self.cantidad / self.receta.rendimiento_unidades


# =====================================================
# MOVIMIENTOS DE INVENTARIO
# =====================================================

class MovimientoInventario(models.Model):
    TIPOS = (
        ("entrada", "Entrada"),
        ("entrada_compra", "Entrada por compra"),
        ("salida", "Salida"),
        ("ajuste", "Ajuste"),
        ("produccion", "Producción"),
        ("merma", "Merma"),
        ("prestamo_entregado", "Préstamo entregado"),
        ("prestamo_recibido", "Préstamo recibido"),
        ("devolucion_prestamo", "Devolución préstamo"),
    )

    TIPOS = TIPOS + (
        ("consumo_produccion", "Consumo de produccion"),
        ("merma_produccion", "Merma de produccion"),
        ("devolucion_produccion", "Devolucion de produccion"),
        ("entrada_producto_terminado", "Entrada de producto terminado"),
        ("reversion_consumo", "Reversion de consumo"),
        ("reversion_entrada", "Reversion de entrada"),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    producto = models.ForeignKey(ProductoInventario, on_delete=models.PROTECT)
    lote = models.ForeignKey(LoteInventario, on_delete=models.PROTECT, null=True, blank=True, related_name="movimientos")
    orden_produccion = models.ForeignKey("OrdenProduccion", on_delete=models.PROTECT, null=True, blank=True, related_name="movimientos_inventario")
    ejecucion = models.ForeignKey("EjecucionInventarioOrden", on_delete=models.PROTECT, null=True, blank=True, related_name="movimientos")

    tipo = models.CharField(max_length=30, choices=TIPOS)
    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    costo_unitario = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    fecha = models.DateField(default=timezone.localdate)
    referencia = models.CharField(max_length=150, blank=True, null=True)
    observacion = models.TextField(blank=True, null=True)

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    saldo_anterior = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    saldo_posterior = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    clave_idempotencia = models.CharField(max_length=180, null=True, blank=True, unique=True)
    aplicado_por_servicio = models.BooleanField(default=False, editable=False)
    revertido_de = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="reversiones")

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.producto.nombre} - {self.cantidad}"

    def save(self, *args, **kwargs):
        nuevo = self.pk is None

        super().save(*args, **kwargs)

        if nuevo and not self.aplicado_por_servicio:
            producto = self.producto
            cantidad = self.cantidad or Decimal("0")

            if self.tipo in [
               "entrada",
               "entrada_compra",
               "ajuste",
               "prestamo_recibido",
               "devolucion_prestamo"
              ]:
                producto.stock_actual += cantidad

            elif self.tipo in [
                "salida",
                "produccion",
                "merma",
                "prestamo_entregado"
            ]:
                producto.stock_actual -= cantidad

                cantidad_restante = cantidad

                lotes = LoteInventario.objects.filter(
                    producto=producto,
                    cantidad_disponible__gt=0
                ).order_by(
                    "fecha_vencimiento",
                    "fecha_ingreso"
                )

                for lote in lotes:
                    if cantidad_restante <= 0:
                        break

                    disponible = lote.cantidad_disponible

                    if disponible >= cantidad_restante:
                        lote.cantidad_disponible -= cantidad_restante
                        lote.save()
                        cantidad_restante = 0
                    else:
                        cantidad_restante -= disponible
                        lote.cantidad_disponible = 0
                        lote.save()

            if self.costo_unitario:
                producto.precio_unitario_compra = self.costo_unitario

            producto.save()


# =====================================================
# PRODUCCIÓN PROGRAMADA / EJECUTADA
# =====================================================

class ProduccionProgramada(models.Model):
    ESTADOS = (
        ("programada", "Programada"),
        ("ejecutada", "Ejecutada"),
        ("cancelada", "Cancelada"),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    producto = models.ForeignKey(ProductoProduccion, on_delete=models.PROTECT)
    receta = models.ForeignKey(Receta, on_delete=models.PROTECT)

    fecha = models.DateField()
    cantidad_unidades = models.DecimalField(max_digits=14, decimal_places=4)

    estado = models.CharField(max_length=20, choices=ESTADOS, default="programada")
    observacion = models.TextField(blank=True, null=True)

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    creada_en = models.DateTimeField(auto_now_add=True)
    ejecutada_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.fecha} - {self.producto.nombre} - {self.cantidad_unidades}"
    
    # =====================================================
# CONSUMOS MANUALES DE PRODUCCIÓN
# =====================================================

class DetalleConsumoProduccion(models.Model):
    produccion = models.ForeignKey(
        ProduccionProgramada,
        on_delete=models.CASCADE,
        related_name="consumos_manuales"
    )

    producto = models.ForeignKey(
        ProductoInventario,
        on_delete=models.PROTECT
    )

    cantidad = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0
    )

    observacion = models.TextField(blank=True, null=True)

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["producto__nombre"]

    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad}"


# =====================================================
# PROYECCIÓN AUTOMÁTICA DE CONSUMO DIARIO
# =====================================================

class ProyeccionConsumoDiario(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    fecha = models.DateField()
    producto_menu = models.CharField(max_length=180)

    receta = models.ForeignKey(
        Receta,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    materia_prima = models.ForeignKey(
        ProductoInventario,
        on_delete=models.PROTECT
    )

    raciones = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0
    )

    cantidad_proyectada = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0
    )

    cantidad_real = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0
    )

    diferencia = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0
    )

    porcentaje_diferencia = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    generado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    generado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "materia_prima__nombre"]
        unique_together = (
            "empresa",
            "fecha",
            "producto_menu",
            "materia_prima",
        )

    def calcular_diferencia(self):
        self.diferencia = Decimal(self.cantidad_real or 0) - Decimal(self.cantidad_proyectada or 0)

        if self.cantidad_proyectada and Decimal(self.cantidad_proyectada) > 0:
            self.porcentaje_diferencia = (
                self.diferencia / Decimal(self.cantidad_proyectada)
            ) * Decimal("100")
        else:
            self.porcentaje_diferencia = Decimal("0")

    def save(self, *args, **kwargs):
        self.calcular_diferencia()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fecha} - {self.materia_prima.nombre}"


# =====================================================
# PRÉSTAMOS DE MATERIA PRIMA
# =====================================================

class PrestamoMateriaPrima(models.Model):
    TIPOS = (
        ("entregado", "De la panadería a terceros"),
        ("recibido", "De terceros a la panadería"),
    )

    ESTADOS = (
        ("pendiente", "Pendiente"),
        ("parcial", "Parcial"),
        ("cerrado", "Cerrado"),
        ("vencido", "Vencido"),
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    producto = models.ForeignKey(ProductoInventario, on_delete=models.PROTECT)

    tipo = models.CharField(max_length=20, choices=TIPOS)
    tercero = models.CharField(max_length=180)

    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    cantidad_devuelta = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    fecha_prestamo = models.DateField(default=timezone.localdate)
    fecha_compromiso = models.DateField(blank=True, null=True)
    fecha_cierre = models.DateField(blank=True, null=True)

    responsable_entrega = models.CharField(max_length=180, blank=True, null=True)
    responsable_recibe = models.CharField(max_length=180, blank=True, null=True)

    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    observacion = models.TextField(blank=True, null=True)

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_prestamo", "-id"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.producto.nombre} - {self.tercero}"

    def cantidad_pendiente(self):
        return self.cantidad - self.cantidad_devuelta

    def actualizar_estado(self):
        pendiente = self.cantidad_pendiente()

        if pendiente <= 0:
            self.estado = "cerrado"
            self.fecha_cierre = timezone.localdate()
        elif self.cantidad_devuelta > 0:
            self.estado = "parcial"
        elif self.fecha_compromiso and timezone.localdate() > self.fecha_compromiso:
            self.estado = "vencido"
        else:
            self.estado = "pendiente"

        self.save()


# =====================================================
# ÓRDENES DE COMPRA
# =====================================================

class OrdenCompra(models.Model):
    ESTADOS = (
    ("borrador", "Borrador"),
    ("solicitada", "Solicitada"),
    ("aprobada", "Aprobada"),
    ("recibida", "Recibida"),
    ("parcial", "Recibida parcial"),
    ("cancelada", "Cancelada"),
)

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)

    numero = models.CharField(max_length=30, blank=True, null=True)
    proveedor = models.CharField(max_length=180, blank=True, null=True)

    ciudad = models.CharField(max_length=120, blank=True, null=True)

    fecha = models.DateField(default=timezone.localdate)
    fecha_requerida = models.DateField(blank=True, null=True)

    fecha_recepcion = models.DateField(blank=True, null=True)

    recibida_por = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    blank=True,
    null=True,
    related_name="ordenes_recibidas"
)

    inventario_actualizado = models.BooleanField(default=False)

    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)

    estado = models.CharField(max_length=20, choices=ESTADOS, default="borrador")

    observacion = models.TextField(blank=True, null=True)

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    itbis = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    creada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def save(self, *args, **kwargs):
        if not self.numero:
            ultimo = OrdenCompra.objects.filter(
                empresa=self.empresa
            ).exclude(
                numero__isnull=True
            ).order_by("-id").first()

            if ultimo and ultimo.numero:
                try:
                    ultimo_numero = int(str(ultimo.numero).replace("OC-", ""))
                    nuevo_numero = ultimo_numero + 1
                except Exception:
                    nuevo_numero = 1
            else:
                nuevo_numero = 1

            self.numero = f"OC-{str(nuevo_numero).zfill(5)}"

        if not self.ciudad and self.empresa:
            self.ciudad = self.empresa.ciudad

        super().save(*args, **kwargs)

    def recalcular_totales(self):
        detalles = self.detalles.all()

        subtotal = sum(detalle.subtotal for detalle in detalles)
        itbis = sum(detalle.itbis for detalle in detalles)

        self.subtotal = subtotal
        self.itbis = itbis
        self.total = subtotal + itbis
        self.save(update_fields=["subtotal", "itbis", "total"])

    def __str__(self):
        return f"Orden {self.numero or self.id} - {self.estado}"


class DetalleOrdenCompra(models.Model):
    orden = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        related_name="detalles"
    )

    producto = models.ForeignKey(
        ProductoInventario,
        on_delete=models.PROTECT,
        blank=True,
        null=True
    )

    producto_manual = models.CharField(
        max_length=180,
        blank=True,
        null=True,
        help_text="Usar solo si el producto no está registrado en inventario."
    )

    unidad_base = models.CharField(max_length=30, blank=True, null=True)
    unidad_compra = models.CharField(max_length=120, blank=True, null=True)

    cantidad_necesaria = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    cantidad_disponible = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    cantidad_faltante = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    cantidad_sugerida_compra = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    cantidad_compra = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    precio_unitario_compra = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    porcentaje_itbis = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    itbis = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    observacion = models.TextField(blank=True, null=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["producto__nombre", "producto_manual"]

    def save(self, *args, **kwargs):
        if self.producto:
            self.unidad_base = self.producto.unidad_medida
            self.unidad_compra = self.producto.unidad_compra
            self.precio_unitario_compra = self.precio_unitario_compra or self.producto.precio_unitario_compra
            self.porcentaje_itbis = self.porcentaje_itbis or self.producto.porcentaje_itbis

        if not self.cantidad_compra:
            self.cantidad_compra = self.cantidad_sugerida_compra

        self.subtotal = self.cantidad_compra * self.precio_unitario_compra
        self.itbis = self.subtotal * (self.porcentaje_itbis / Decimal("100"))
        self.total = self.subtotal + self.itbis

        super().save(*args, **kwargs)

        if self.orden:
            self.orden.recalcular_totales()

    def nombre_producto(self):
        if self.producto:
            return self.producto.nombre
        return self.producto_manual or "Producto manual"

    def __str__(self):
        return f"{self.nombre_producto()} - {self.cantidad_compra}"


# =====================================================
# PLANIFICACIÓN DE PRODUCCIÓN (SPRINT PRODUCCIÓN 1)
# =====================================================
class RecetaProduccion(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="recetas_produccion")
    codigo = models.CharField(max_length=40)
    nombre = models.CharField(max_length=180)
    producto_terminado = models.ForeignKey(ProductoInventario, on_delete=models.PROTECT, related_name="recetas_produccion")
    version = models.PositiveIntegerField(default=1)
    rendimiento_base = models.DecimalField(max_digits=14, decimal_places=4)
    unidad_rendimiento = models.CharField(max_length=30)
    porcentaje_merma_estimada = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tiempo_preparacion_minutos = models.PositiveIntegerField(null=True, blank=True)
    tiempo_produccion_minutos = models.PositiveIntegerField(null=True, blank=True)
    instrucciones = models.TextField(blank=True)
    activa = models.BooleanField(default=False)
    fecha_vigencia_desde = models.DateField()
    fecha_vigencia_hasta = models.DateField(null=True, blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="recetas_prod_creadas")
    actualizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="recetas_prod_actualizadas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["producto_terminado__nombre", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo"], name="inv_recprod_empresa_codigo_uniq"),
            models.UniqueConstraint(fields=["empresa", "producto_terminado", "version"], name="inv_recprod_producto_version_uniq"),
            models.CheckConstraint(condition=models.Q(rendimiento_base__gt=0), name="inv_recprod_rendimiento_positivo"),
            models.CheckConstraint(condition=models.Q(porcentaje_merma_estimada__gte=0, porcentaje_merma_estimada__lte=100), name="inv_recprod_merma_rango"),
        ]
        permissions = []

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.producto_terminado_id:
            if self.empresa_id and self.producto_terminado.empresa_id != self.empresa_id:
                errors["producto_terminado"] = "El producto pertenece a otra empresa."
            elif self.producto_terminado.tipo != "producto_terminado" or not self.producto_terminado.activo:
                errors["producto_terminado"] = "Selecciona un producto terminado activo."
        if self.rendimiento_base is not None and self.rendimiento_base <= 0:
            errors["rendimiento_base"] = "El rendimiento debe ser mayor que cero."
        if self.fecha_vigencia_hasta and self.fecha_vigencia_hasta < self.fecha_vigencia_desde:
            errors["fecha_vigencia_hasta"] = "La fecha final no puede ser anterior a la inicial."
        if errors: raise ValidationError(errors)

    def vigente_en(self, fecha):
        return self.activa and self.fecha_vigencia_desde <= fecha and (
            self.fecha_vigencia_hasta is None or self.fecha_vigencia_hasta >= fecha
        )

    def __str__(self):
        return f"{self.codigo} · {self.nombre} v{self.version}"


class DetalleRecetaProduccion(models.Model):
    receta = models.ForeignKey(RecetaProduccion, on_delete=models.PROTECT, related_name="ingredientes")
    materia_prima = models.ForeignKey(ProductoInventario, on_delete=models.PROTECT, related_name="uso_en_recetas_produccion")
    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    unidad_medida = models.CharField(max_length=30)
    porcentaje_merma = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    es_opcional = models.BooleanField(default=False)
    observaciones = models.CharField(max_length=255, blank=True)
    orden = models.PositiveIntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["orden", "id"]
        constraints = [
            models.UniqueConstraint(fields=["receta", "materia_prima"], name="inv_detrecprod_materia_uniq"),
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name="inv_detrecprod_cantidad_positiva"),
            models.CheckConstraint(condition=models.Q(porcentaje_merma__gte=0, porcentaje_merma__lte=100), name="inv_detrecprod_merma_rango"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        if self.materia_prima_id and self.receta_id:
            if self.materia_prima.empresa_id != self.receta.empresa_id:
                errors["materia_prima"] = "La materia prima pertenece a otra empresa."
            if self.materia_prima_id == self.receta.producto_terminado_id:
                errors["materia_prima"] = "La materia prima no puede ser el producto terminado."
            if not self.materia_prima.activo or self.materia_prima.tipo == "producto_terminado":
                errors["materia_prima"] = "Selecciona una materia prima activa."
        if errors: raise ValidationError(errors)


class PlanProduccion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        GENERADO = "GENERADO", "Generado"
        EN_REVISION = "EN_REVISION", "En revisión"
        APROBADO = "APROBADO", "Aprobado"
        CERRADO = "CERRADO", "Cerrado"
        CANCELADO = "CANCELADO", "Cancelado"
    class Origen(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        PEDIDOS = "PEDIDOS", "Pedidos"
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="planes_produccion")
    numero = models.CharField(max_length=30)
    fecha_plan = models.DateField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)
    origen = models.CharField(max_length=10, choices=Origen.choices, default=Origen.MANUAL)
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="planes_prod_creados")
    actualizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="planes_prod_actualizados")
    aprobado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="planes_prod_aprobados")
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-fecha_plan", "-id"]
        constraints = [models.UniqueConstraint(fields=["empresa", "numero"], name="inv_planprod_empresa_numero_uniq")]
        permissions = [
            ("aprobar_planproduccion", "Puede aprobar planes de producción"),
            ("cancelar_planproduccion", "Puede cancelar planes de producción"),
        ]
    def __str__(self): return self.numero


class DetallePlanProduccion(models.Model):
    plan = models.ForeignKey(PlanProduccion, on_delete=models.CASCADE, related_name="detalles")
    producto_terminado = models.ForeignKey(ProductoInventario, on_delete=models.PROTECT)
    receta = models.ForeignKey(RecetaProduccion, on_delete=models.PROTECT, null=True, blank=True)
    cantidad_solicitada = models.DecimalField(max_digits=14, decimal_places=4)
    cantidad_planificada = models.DecimalField(max_digits=14, decimal_places=4)
    unidad_medida = models.CharField(max_length=30)
    prioridad = models.CharField(max_length=10, choices=(("BAJA","Baja"),("NORMAL","Normal"),("ALTA","Alta"),("URGENTE","Urgente")), default="NORMAL")
    fecha_requerida = models.DateField()
    pedido_origen = models.ForeignKey("comercial.Pedido", on_delete=models.PROTECT, null=True, blank=True)
    detalle_pedido_origen = models.ForeignKey("comercial.DetallePedido", on_delete=models.PROTECT, null=True, blank=True)
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["producto_terminado__nombre", "id"]
        constraints = [models.CheckConstraint(condition=models.Q(cantidad_planificada__gt=0), name="inv_detplan_cantidad_positiva")]

    def clean(self):
        from django.core.exceptions import ValidationError
        errors={}
        if self.producto_terminado_id and self.plan_id and self.producto_terminado.empresa_id != self.plan.empresa_id: errors["producto_terminado"]="El producto pertenece a otra empresa."
        if self.receta_id and self.receta.producto_terminado_id != self.producto_terminado_id: errors["receta"]="La receta no corresponde al producto."
        if self.pedido_origen_id and (self.pedido_origen.empresa_id != self.plan.empresa_id or self.pedido_origen.estado != "APROBADO"): errors["pedido_origen"]="El pedido debe estar aprobado y pertenecer a la empresa."
        if self.detalle_pedido_origen_id and (self.detalle_pedido_origen.pedido_id != self.pedido_origen_id or self.detalle_pedido_origen.producto_id != self.producto_terminado_id): errors["detalle_pedido_origen"]="La línea comercial no corresponde al pedido y producto."
        if errors: raise ValidationError(errors)


class OrdenProduccion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR="BORRADOR","Borrador"; PROGRAMADA="PROGRAMADA","Programada"; LIBERADA="LIBERADA","Liberada"; EN_PROCESO="EN_PROCESO","En proceso"; PAUSADA="PAUSADA","Pausada"; COMPLETADA="COMPLETADA","Completada"; CERRADA="CERRADA","Cerrada"; CANCELADA="CANCELADA","Cancelada"
    class Turno(models.TextChoices):
        MANANA="MANANA","Mañana"; TARDE="TARDE","Tarde"; NOCHE="NOCHE","Noche"; UNICO="UNICO","Único"
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="ordenes_produccion")
    numero = models.CharField(max_length=30)
    plan = models.ForeignKey(PlanProduccion, on_delete=models.PROTECT, null=True, blank=True, related_name="ordenes")
    detalle_plan = models.ForeignKey(DetallePlanProduccion, on_delete=models.PROTECT, null=True, blank=True, related_name="ordenes")
    producto_terminado = models.ForeignKey(ProductoInventario, on_delete=models.PROTECT)
    receta = models.ForeignKey(RecetaProduccion, on_delete=models.PROTECT)
    fecha_programada = models.DateField()
    turno = models.CharField(max_length=10, choices=Turno.choices, default=Turno.UNICO)
    prioridad = models.CharField(max_length=10, choices=DetallePlanProduccion._meta.get_field("prioridad").choices, default="NORMAL")
    cantidad_planificada = models.DecimalField(max_digits=14, decimal_places=4)
    cantidad_iniciada = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    cantidad_producida = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    cantidad_rechazada = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    unidad_medida = models.CharField(max_length=30)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.BORRADOR)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes_produccion_responsable")
    fecha_inicio_real = models.DateTimeField(null=True, blank=True)
    fecha_fin_real = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes_prod_creadas")
    actualizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes_prod_actualizadas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-fecha_programada", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["empresa","numero"], name="inv_ordenprod_empresa_numero_uniq"),
            models.CheckConstraint(condition=models.Q(cantidad_planificada__gt=0), name="inv_ordenprod_planificada_positiva"),
            models.CheckConstraint(condition=models.Q(cantidad_producida__gte=0, cantidad_rechazada__gte=0), name="inv_ordenprod_cantidades_no_negativas"),
        ]
        permissions = [
            ("programar_ordenproduccion","Puede programar órdenes de producción"),
            ("iniciar_ordenproduccion","Puede iniciar órdenes de producción"),
            ("completar_ordenproduccion","Puede completar órdenes de producción"),
            ("cancelar_ordenproduccion","Puede cancelar órdenes de producción"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        errors={}
        if self.producto_terminado_id and self.empresa_id and self.producto_terminado.empresa_id != self.empresa_id: errors["producto_terminado"]="El producto pertenece a otra empresa."
        if self.receta_id and (self.receta.empresa_id != self.empresa_id or self.receta.producto_terminado_id != self.producto_terminado_id): errors["receta"]="La receta no corresponde a la empresa y producto."
        if self.plan_id and self.plan.empresa_id != self.empresa_id: errors["plan"]="El plan pertenece a otra empresa."
        if self.detalle_plan_id and self.detalle_plan.plan_id != self.plan_id: errors["detalle_plan"]="El detalle no pertenece al plan."
        if self.cantidad_producida + self.cantidad_rechazada > self.cantidad_iniciada: errors["cantidad_producida"]="Producida más rechazada no puede superar la iniciada."
        if self.fecha_inicio_real and self.fecha_fin_real and self.fecha_fin_real < self.fecha_inicio_real: errors["fecha_fin_real"]="La fecha final no puede ser anterior al inicio."
        if errors: raise ValidationError(errors)


class NecesidadMateriaPrima(models.Model):
    class Estado(models.TextChoices):
        CALCULADA="CALCULADA","Calculada"; REVISADA="REVISADA","Revisada"; CUBIERTA="CUBIERTA","Cubierta"; INSUFICIENTE="INSUFICIENTE","Insuficiente"; CANCELADA="CANCELADA","Cancelada"
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    plan = models.ForeignKey(PlanProduccion, on_delete=models.CASCADE, null=True, blank=True, related_name="necesidades")
    orden = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, null=True, blank=True, related_name="necesidades")
    producto_terminado = models.ForeignKey(ProductoInventario, on_delete=models.PROTECT, related_name="+")
    materia_prima = models.ForeignKey(ProductoInventario, on_delete=models.PROTECT, related_name="necesidades_produccion")
    cantidad_teorica = models.DecimalField(max_digits=16, decimal_places=4)
    unidad_medida = models.CharField(max_length=30)
    porcentaje_merma_aplicado = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cantidad_con_merma = models.DecimalField(max_digits=16, decimal_places=4)
    fecha_requerida = models.DateField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.CALCULADA)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)


class HistorialEstadoOrdenProduccion(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    orden = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name="historial_estados")
    estado_anterior = models.CharField(max_length=20, choices=OrdenProduccion.Estado.choices)
    estado_nuevo = models.CharField(max_length=20, choices=OrdenProduccion.Estado.choices)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-fecha"]


class ReservaInventario(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        PARCIAL = "PARCIAL", "Parcial"
        CONSUMIDA = "CONSUMIDA", "Consumida"
        LIBERADA = "LIBERADA", "Liberada"
        CANCELADA = "CANCELADA", "Cancelada"
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="reservas_inventario")
    numero = models.CharField(max_length=30)
    orden = models.ForeignKey(OrdenProduccion, on_delete=models.PROTECT, related_name="reservas_inventario")
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.ACTIVA)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["empresa", "numero"], name="inv_reserva_empresa_numero_uniq")]


class DetalleReservaInventario(models.Model):
    reserva = models.ForeignKey(ReservaInventario, on_delete=models.CASCADE, related_name="detalles")
    necesidad = models.ForeignKey(NecesidadMateriaPrima, on_delete=models.PROTECT, related_name="reservas")
    lote = models.ForeignKey(LoteInventario, on_delete=models.PROTECT, related_name="reservas")
    cantidad_reservada = models.DecimalField(max_digits=14, decimal_places=4)
    cantidad_consumida = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    cantidad_liberada = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["reserva", "necesidad", "lote"], name="inv_reserva_detalle_uniq"),
            models.CheckConstraint(condition=models.Q(cantidad_reservada__gt=0), name="inv_reserva_detalle_positiva"),
        ]
    @property
    def cantidad_pendiente(self):
        return self.cantidad_reservada - self.cantidad_consumida - self.cantidad_liberada


class EjecucionInventarioOrden(models.Model):
    class Estado(models.TextChoices):
        PREPARADA = "PREPARADA", "Preparada"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CERRADA = "CERRADA", "Cerrada"
        REVERSADA = "REVERSADA", "Reversada"
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    orden = models.OneToOneField(OrdenProduccion, on_delete=models.PROTECT, related_name="ejecucion_inventario")
    reserva = models.ForeignKey(ReservaInventario, on_delete=models.PROTECT, related_name="ejecuciones")
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PREPARADA)
    clave_idempotencia = models.CharField(max_length=180, unique=True)
    iniciado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    iniciado_en = models.DateTimeField(auto_now_add=True)
    cerrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    cerrado_en = models.DateTimeField(null=True, blank=True)
    reversado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    reversado_en = models.DateTimeField(null=True, blank=True)


class ConsumoProduccion(models.Model):
    ejecucion = models.ForeignKey(EjecucionInventarioOrden, on_delete=models.PROTECT, related_name="consumos")
    detalle_reserva = models.ForeignKey(DetalleReservaInventario, on_delete=models.PROTECT, related_name="consumos")
    movimiento = models.OneToOneField(MovimientoInventario, on_delete=models.PROTECT, related_name="consumo")
    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)


class MermaProduccion(models.Model):
    ejecucion = models.ForeignKey(EjecucionInventarioOrden, on_delete=models.PROTECT, related_name="mermas")
    lote = models.ForeignKey(LoteInventario, on_delete=models.PROTECT)
    movimiento = models.OneToOneField(MovimientoInventario, on_delete=models.PROTECT, related_name="merma_produccion")
    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    motivo = models.CharField(max_length=255)
    requiere_aprobacion = models.BooleanField(default=False)
    aprobado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)


class DevolucionProduccion(models.Model):
    ejecucion = models.ForeignKey(EjecucionInventarioOrden, on_delete=models.PROTECT, related_name="devoluciones")
    lote = models.ForeignKey(LoteInventario, on_delete=models.PROTECT)
    movimiento = models.OneToOneField(MovimientoInventario, on_delete=models.PROTECT, related_name="devolucion_produccion")
    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)


class LoteProduccion(models.Model):
    ejecucion = models.OneToOneField(EjecucionInventarioOrden, on_delete=models.PROTECT, related_name="lote_produccion")
    lote = models.OneToOneField(LoteInventario, on_delete=models.PROTECT, related_name="produccion")
    movimiento_entrada = models.OneToOneField(MovimientoInventario, on_delete=models.PROTECT, related_name="lote_producido")
    cantidad_neta = models.DecimalField(max_digits=14, decimal_places=4)
