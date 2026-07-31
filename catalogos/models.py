from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from conduces.models import Empresa


class AuditadoEmpresa(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=120)
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["orden", "nombre"]


class Moneda(models.Model):
    codigo = models.CharField(max_length=3, unique=True)
    nombre = models.CharField(max_length=80)
    simbolo = models.CharField(max_length=8)
    decimales = models.PositiveSmallIntegerField(default=2)
    activa = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "codigo"]
        constraints = [models.CheckConstraint(condition=Q(decimales__lte=6), name="cat_moneda_decimales_validos")]

    def __str__(self):
        return self.codigo


class MonedaEmpresa(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    moneda = models.ForeignKey(Moneda, on_delete=models.PROTECT)
    activa = models.BooleanField(default=True)
    es_base = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "moneda"], name="cat_moneda_empresa_uniq"),
            models.UniqueConstraint(fields=["empresa"], condition=Q(es_base=True, activa=True), name="cat_moneda_base_empresa_uniq"),
        ]


class CondicionPago(AuditadoEmpresa):
    class Tipo(models.TextChoices):
        CONTADO = "CONTADO", "Contado"
        CREDITO = "CREDITO", "Crédito"
        MIXTO = "MIXTO", "Mixto"
        ANTICIPO = "ANTICIPO", "Anticipo"
        OTRO = "OTRO", "Otro"

    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    dias_credito = models.PositiveIntegerField(default=0)
    porcentaje_anticipo = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    predeterminada = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)

    class Meta(AuditadoEmpresa.Meta):
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo"], name="cat_pago_empresa_codigo_uniq"),
            models.UniqueConstraint(fields=["empresa"], condition=Q(predeterminada=True, activo=True), name="cat_pago_pred_empresa_uniq"),
            models.CheckConstraint(condition=Q(porcentaje_anticipo__gte=0, porcentaje_anticipo__lte=100), name="cat_pago_anticipo_rango"),
        ]
        indexes = [models.Index(fields=["empresa", "activo"], name="cat_pago_emp_act_idx")]


class UnidadMedida(AuditadoEmpresa):
    class Magnitud(models.TextChoices):
        UNIDAD="UNIDAD","Unidad"; PESO="PESO","Peso"; VOLUMEN="VOLUMEN","Volumen"
        LONGITUD="LONGITUD","Longitud"; AREA="AREA","Área"; TIEMPO="TIEMPO","Tiempo"
        EMPAQUE="EMPAQUE","Empaque"; OTRO="OTRO","Otro"
    simbolo = models.CharField(max_length=15)
    magnitud = models.CharField(max_length=12, choices=Magnitud.choices)
    decimales = models.PositiveSmallIntegerField(default=4)
    es_base = models.BooleanField(default=False)

    class Meta(AuditadoEmpresa.Meta):
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo"], name="cat_unidad_empresa_codigo_uniq"),
            models.UniqueConstraint(fields=["empresa", "magnitud"], condition=Q(es_base=True, activo=True), name="cat_unidad_base_magnitud_uniq"),
            models.CheckConstraint(condition=Q(decimales__lte=6), name="cat_unidad_decimales_validos"),
        ]


class ConversionUnidad(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    unidad_origen = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT, related_name="conversiones_origen")
    unidad_destino = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT, related_name="conversiones_destino")
    producto = models.ForeignKey("inventario.ProductoInventario", on_delete=models.PROTECT, null=True, blank=True)
    factor = models.DecimalField(max_digits=18, decimal_places=8)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "unidad_origen", "unidad_destino", "producto", "vigente_desde"], name="cat_conversion_vigencia_uniq"),
            models.CheckConstraint(condition=Q(factor__gt=0), name="cat_conversion_factor_positivo"),
            models.CheckConstraint(condition=~Q(unidad_origen=models.F("unidad_destino")), name="cat_conversion_unidades_distintas"),
        ]

    def clean(self):
        errors = {}
        for field in ("unidad_origen", "unidad_destino", "producto"):
            obj = getattr(self, field, None)
            if obj and obj.empresa_id != self.empresa_id:
                errors[field] = "El registro pertenece a otra empresa."
        if self.vigente_hasta and self.vigente_hasta < self.vigente_desde:
            errors["vigente_hasta"] = "La vigencia final no puede ser anterior."
        if errors:
            raise ValidationError(errors)


class Almacen(AuditadoEmpresa):
    TIPOS = [(v, v.replace("_", " ").title()) for v in ("MATERIA_PRIMA","EMPAQUE","PRODUCCION","PRODUCTO_TERMINADO","REPUESTOS","DEVOLUCIONES","CUARENTENA","GENERAL")]
    tipo = models.CharField(max_length=25, choices=TIPOS)
    direccion = models.TextField(blank=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    permite_recepcion = models.BooleanField(default=True)
    permite_despacho = models.BooleanField(default=True)
    permite_stock = models.BooleanField(default=True)
    principal = models.BooleanField(default=False)

    class Meta(AuditadoEmpresa.Meta):
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo"], name="cat_almacen_empresa_codigo_uniq"),
            models.UniqueConstraint(fields=["empresa"], condition=Q(principal=True, activo=True), name="cat_almacen_principal_empresa_uniq"),
        ]


class CentroCosto(AuditadoEmpresa):
    descripcion = models.TextField(blank=True)
    centro_padre = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="hijos")
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    nivel = models.PositiveSmallIntegerField(default=1)
    ruta = models.CharField(max_length=500, blank=True)
    acepta_movimientos = models.BooleanField(default=True)
    vigente_desde = models.DateField(null=True, blank=True)
    vigente_hasta = models.DateField(null=True, blank=True)

    class Meta(AuditadoEmpresa.Meta):
        constraints = [models.UniqueConstraint(fields=["empresa", "codigo"], name="cat_centro_empresa_codigo_uniq")]

    def clean(self):
        if self.centro_padre:
            if self.centro_padre.empresa_id != self.empresa_id:
                raise ValidationError({"centro_padre": "El centro padre pertenece a otra empresa."})
            actual = self.centro_padre
            while actual:
                if actual.pk == self.pk:
                    raise ValidationError({"centro_padre": "La jerarquía no puede contener ciclos."})
                actual = actual.centro_padre


class Impuesto(AuditadoEmpresa):
    TIPOS = [("ITBIS","ITBIS"),("ISC","ISC"),("RETENCION","Retención"),("OTRO","Otro")]
    tipo = models.CharField(max_length=12, choices=TIPOS)
    tasa = models.DecimalField(max_digits=7, decimal_places=4)
    recuperable = models.BooleanField(default=True)
    incluido_precio = models.BooleanField(default=False)
    uso_compra = models.BooleanField(default=True)
    uso_venta = models.BooleanField(default=False)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)

    class Meta(AuditadoEmpresa.Meta):
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo", "vigente_desde"], name="cat_impuesto_vigencia_uniq"),
            models.CheckConstraint(condition=Q(tasa__gte=0, tasa__lte=100), name="cat_impuesto_tasa_rango"),
        ]


class TipoCompra(AuditadoEmpresa):
    NATURALEZAS = [("BIEN","Bien"),("SERVICIO","Servicio"),("ACTIVO","Activo fijo"),("GASTO","Gasto")]
    naturaleza = models.CharField(max_length=10, choices=NATURALEZAS)
    afecta_inventario = models.BooleanField(default=False)
    requiere_recepcion = models.BooleanField(default=True)
    requiere_inspeccion = models.BooleanField(default=False)
    requiere_centro_costo = models.BooleanField(default=True)
    requiere_activo_fijo = models.BooleanField(default=False)
    permite_descripcion_libre = models.BooleanField(default=False)

    class Meta(AuditadoEmpresa.Meta):
        constraints = [models.UniqueConstraint(fields=["empresa", "codigo"], name="cat_tipo_compra_empresa_codigo_uniq")]
        permissions = [("gestionar_catalogos", "Puede gestionar catálogos transversales")]
