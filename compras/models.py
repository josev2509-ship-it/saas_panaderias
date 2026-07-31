from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from conduces.models import Empresa
from .domain.identity import normalizar_identificacion


class AuditMixin(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CategoriaProveedor(AuditMixin):
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    categoria_padre = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="subcategorias")
    nivel = models.PositiveSmallIntegerField(default=1)
    activo = models.BooleanField(default=True)
    requiere_evaluacion = models.BooleanField(default=False)
    requiere_documentos_especiales = models.BooleanField(default=False)
    es_critica = models.BooleanField(default=False)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        constraints = [models.UniqueConstraint(fields=["empresa", "codigo"], name="cmp_catprov_emp_codigo_uniq")]

    def clean(self):
        if self.categoria_padre:
            if self.categoria_padre.empresa_id != self.empresa_id:
                raise ValidationError({"categoria_padre": "La categoría padre pertenece a otra empresa."})
            actual = self.categoria_padre
            while actual:
                if actual.pk == self.pk:
                    raise ValidationError({"categoria_padre": "La jerarquía no puede contener ciclos."})
                actual = actual.categoria_padre

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class Proveedor(AuditMixin):
    class TipoPersona(models.TextChoices):
        FISICA="FISICA","Física"; JURIDICA="JURIDICA","Jurídica"; EXTRANJERA="EXTRANJERA","Extranjera"
        GUBERNAMENTAL="GUBERNAMENTAL","Gubernamental"; OTRA="OTRA","Otra"
    class Estado(models.TextChoices):
        EN_EVALUACION="EN_EVALUACION","En evaluación"; ACTIVO="ACTIVO","Activo"; SUSPENDIDO="SUSPENDIDO","Suspendido"
        BLOQUEADO="BLOQUEADO","Bloqueado"; INACTIVO="INACTIVO","Inactivo"
    class Riesgo(models.TextChoices):
        BAJO="BAJO","Bajo"; MEDIO="MEDIO","Medio"; ALTO="ALTO","Alto"; CRITICO="CRITICO","Crítico"

    codigo = models.CharField(max_length=30)
    tipo_persona = models.CharField(max_length=20, choices=TipoPersona.choices)
    razon_social = models.CharField(max_length=200)
    nombre_comercial = models.CharField(max_length=200, blank=True)
    rnc_identificacion = models.CharField(max_length=40, blank=True)
    rnc_normalizado = models.CharField(max_length=40, blank=True, editable=False)
    actividad_economica = models.CharField(max_length=200, blank=True)
    pais = models.CharField(max_length=80, default="República Dominicana")
    sitio_web = models.URLField(blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.EN_EVALUACION)
    bloqueado = models.BooleanField(default=False)
    motivo_bloqueo = models.TextField(blank=True)
    fecha_bloqueo = models.DateTimeField(null=True, blank=True)
    bloqueado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    nivel_riesgo = models.CharField(max_length=10, choices=Riesgo.choices, default=Riesgo.BAJO)
    motivo_riesgo = models.TextField(blank=True)
    requiere_aprobacion_especial = models.BooleanField(default=False)
    correo = models.EmailField(blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    moneda_habitual = models.ForeignKey("catalogos.MonedaEmpresa", on_delete=models.PROTECT, null=True, blank=True)
    condicion_pago = models.ForeignKey("catalogos.CondicionPago", on_delete=models.PROTECT, null=True, blank=True)
    dias_credito = models.PositiveIntegerField(default=0)
    limite_operativo = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    descuento_habitual = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pedido_minimo = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    plazo_entrega_estimado_dias = models.PositiveIntegerField(default=0)
    sujeto_retencion = models.BooleanField(default=False)
    tipo_retencion = models.CharField(max_length=80, blank=True)
    retencion_porcentaje_referencia = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    impuesto_predeterminado = models.ForeignKey("catalogos.Impuesto", on_delete=models.PROTECT, null=True, blank=True)
    exento = models.BooleanField(default=False)
    observaciones_fiscales = models.TextField(blank=True)
    categoria = models.ForeignKey(CategoriaProveedor, on_delete=models.PROTECT, null=True, blank=True, related_name="proveedores")
    es_proveedor_critico = models.BooleanField(default=False)
    es_preferido = models.BooleanField(default=False)
    permite_compra_directa = models.BooleanField(default=False)
    requiere_cotizacion = models.BooleanField(default=True)
    documentacion_completa = models.BooleanField(default=False)
    fecha_ultima_revision_documental = models.DateField(null=True, blank=True)
    proxima_revision_documental = models.DateField(null=True, blank=True)
    external_reference = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["razon_social"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "codigo"], name="cmp_prov_emp_codigo_uniq"),
            models.UniqueConstraint(fields=["empresa", "rnc_normalizado"], condition=~Q(rnc_normalizado=""), name="cmp_prov_emp_rnc_uniq"),
            models.CheckConstraint(condition=Q(limite_operativo__gte=0, pedido_minimo__gte=0), name="cmp_prov_importes_no_neg"),
            models.CheckConstraint(condition=Q(descuento_habitual__gte=0, descuento_habitual__lte=100), name="cmp_prov_descuento_rango"),
            models.CheckConstraint(condition=Q(retencion_porcentaje_referencia__gte=0, retencion_porcentaje_referencia__lte=100), name="cmp_prov_retencion_rango"),
        ]
        indexes = [
            models.Index(fields=["empresa", "estado"], name="cmp_prov_emp_estado_idx"),
            models.Index(fields=["empresa", "nombre_comercial"], name="cmp_prov_emp_nombre_idx"),
            models.Index(fields=["empresa", "nivel_riesgo"], name="cmp_prov_emp_riesgo_idx"),
            models.Index(fields=["empresa", "categoria"], name="cmp_prov_emp_cat_idx"),
            models.Index(fields=["empresa", "documentacion_completa"], name="cmp_prov_emp_doc_idx"),
        ]
        permissions = [
            ("activar_proveedor","Puede activar proveedores"),("suspender_proveedor","Puede suspender proveedores"),
            ("bloquear_proveedor","Puede bloquear proveedores"),("reactivar_proveedor","Puede reactivar proveedores"),
            ("inactivar_proveedor","Puede inactivar proveedores"),("exportar_proveedores","Puede exportar proveedores"),
            ("view_costos_proveedor","Puede ver costos de proveedor"),("view_riesgo_proveedor","Puede ver riesgo de proveedor"),
            ("view_documentos_proveedor","Puede ver documentos de proveedor"),
            ("gestionar_documentos_proveedor","Puede gestionar documentos de proveedor"),
            ("revisar_documentos_proveedor","Puede revisar documentos de proveedor"),
            ("view_correspondencia_proveedor","Puede ver correspondencias legado"),
            ("gestionar_correspondencia_proveedor","Puede gestionar correspondencias legado"),
            ("ejecutar_migracion_proveedor","Puede ejecutar migración de proveedores"),
        ]

    def clean(self):
        errors = {}
        self.rnc_normalizado = normalizar_identificacion(self.rnc_identificacion)
        for field in ("moneda_habitual", "condicion_pago", "impuesto_predeterminado", "categoria"):
            obj = getattr(self, field, None)
            if obj and obj.empresa_id != self.empresa_id:
                errors[field] = "El registro pertenece a otra empresa."
        if self.bloqueado and not self.motivo_bloqueo:
            errors["motivo_bloqueo"] = "El bloqueo requiere un motivo."
        if self.estado == self.Estado.BLOQUEADO and not self.bloqueado:
            errors["bloqueado"] = "El estado bloqueado requiere el indicador de bloqueo."
        if self.estado == self.Estado.INACTIVO and self.es_preferido:
            errors["es_preferido"] = "Un proveedor inactivo no puede ser preferido."
        if self.es_proveedor_critico and not self.motivo_riesgo:
            errors["motivo_riesgo"] = "La clasificación crítica debe justificarse."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.codigo} · {self.razon_social}"


class ContactoProveedor(AuditMixin):
    CANALES = (("CORREO","Correo"),("TELEFONO","Teléfono"),("WHATSAPP","WhatsApp"),("OTRO","Otro"))
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="contactos")
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    departamento = models.CharField(max_length=100, blank=True)
    correo = models.EmailField(blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    telefono_alterno = models.CharField(max_length=50, blank=True)
    extension = models.CharField(max_length=15, blank=True)
    canal_preferido = models.CharField(max_length=15, choices=CANALES, default="CORREO")
    principal = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    recibe_cotizaciones = models.BooleanField(default=False)
    recibe_ordenes = models.BooleanField(default=False)
    recibe_reclamos_calidad = models.BooleanField(default=False)
    recibe_pagos = models.BooleanField(default=False)
    recibe_documentos_fiscales = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["proveedor"], condition=Q(principal=True, activo=True), name="cmp_contacto_principal_uniq")]
    def clean(self):
        if self.proveedor_id and self.proveedor.empresa_id != self.empresa_id:
            raise ValidationError("El proveedor pertenece a otra empresa.")


class DireccionProveedor(AuditMixin):
    TIPOS = tuple((x, x.replace("_"," ").title()) for x in ("FISCAL","DESPACHO","CORRESPONDENCIA","ALMACEN","DEVOLUCION","OTRA"))
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="direcciones")
    tipo = models.CharField(max_length=20, choices=TIPOS)
    nombre_referencia = models.CharField(max_length=100, blank=True)
    direccion_linea_1 = models.CharField(max_length=200)
    direccion_linea_2 = models.CharField(max_length=200, blank=True)
    sector = models.CharField(max_length=100, blank=True); ciudad = models.CharField(max_length=100, blank=True)
    municipio = models.CharField(max_length=100, blank=True); provincia = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=80, default="República Dominicana"); codigo_postal = models.CharField(max_length=20, blank=True)
    referencia = models.TextField(blank=True)
    latitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    principal = models.BooleanField(default=False); activa = models.BooleanField(default=True)
    instrucciones = models.TextField(blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["proveedor","tipo"], condition=Q(principal=True, activa=True), name="cmp_direccion_principal_uniq"),
            models.CheckConstraint(condition=Q(latitud__isnull=True)|Q(latitud__gte=-90,latitud__lte=90), name="cmp_dir_latitud_rango"),
            models.CheckConstraint(condition=Q(longitud__isnull=True)|Q(longitud__gte=-180,longitud__lte=180), name="cmp_dir_longitud_rango"),
        ]
    def clean(self):
        if self.proveedor_id and self.proveedor.empresa_id != self.empresa_id:
            raise ValidationError("El proveedor pertenece a otra empresa.")


class ProductoProveedor(AuditMixin):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="productos")
    producto = models.ForeignKey("inventario.ProductoInventario", on_delete=models.PROTECT, related_name="proveedores_enterprise")
    codigo_producto_proveedor = models.CharField(max_length=80, blank=True)
    descripcion_proveedor = models.CharField(max_length=200, blank=True)
    unidad_compra = models.ForeignKey("catalogos.UnidadMedida", on_delete=models.PROTECT, related_name="+")
    unidad_base_producto = models.ForeignKey("catalogos.UnidadMedida", on_delete=models.PROTECT, related_name="+")
    factor_conversion = models.DecimalField(max_digits=18, decimal_places=8, default=1)
    precio_referencia = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    moneda = models.ForeignKey("catalogos.MonedaEmpresa", on_delete=models.PROTECT)
    pedido_minimo = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    multiplo_compra = models.DecimalField(max_digits=16, decimal_places=4, default=1)
    plazo_entrega_dias = models.PositiveIntegerField(default=0)
    vigencia_desde = models.DateField(null=True, blank=True); vigencia_hasta = models.DateField(null=True, blank=True)
    preferido = models.BooleanField(default=False); aprobado = models.BooleanField(default=False); activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa","proveedor","producto"], condition=Q(activo=True), name="cmp_prodprov_activo_uniq"),
            models.UniqueConstraint(fields=["empresa","producto"], condition=Q(preferido=True,activo=True), name="cmp_prodprov_preferido_uniq"),
            models.CheckConstraint(condition=Q(factor_conversion__gt=0,multiplo_compra__gt=0,precio_referencia__gte=0,pedido_minimo__gte=0), name="cmp_prodprov_valores_validos"),
        ]
        permissions = [("establecer_proveedor_preferido","Puede establecer proveedor preferido")]
    def clean(self):
        errors = {}
        for field in ("proveedor","producto","unidad_compra","unidad_base_producto","moneda"):
            obj=getattr(self,field,None)
            if obj and obj.empresa_id != self.empresa_id: errors[field]="El registro pertenece a otra empresa."
        if self.vigencia_hasta and self.vigencia_desde and self.vigencia_hasta < self.vigencia_desde: errors["vigencia_hasta"]="Vigencia inválida."
        if errors: raise ValidationError(errors)


class CuentaBancariaProveedor(AuditMixin):
    ESTADOS=(("PENDIENTE","Pendiente"),("VERIFICADA","Verificada"),("RECHAZADA","Rechazada"),("INACTIVA","Inactiva"))
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="cuentas_bancarias")
    banco = models.CharField(max_length=120); tipo_cuenta = models.CharField(max_length=60)
    moneda = models.ForeignKey("catalogos.MonedaEmpresa", on_delete=models.PROTECT)
    numero_cuenta = models.CharField(max_length=100)
    numero_enmascarado = models.CharField(max_length=100, editable=False)
    titular = models.CharField(max_length=160); identificacion_titular = models.CharField(max_length=40)
    swift_bic = models.CharField(max_length=20, blank=True); iban = models.CharField(max_length=50, blank=True)
    principal = models.BooleanField(default=False); verificada = models.BooleanField(default=False)
    fecha_verificacion = models.DateTimeField(null=True, blank=True)
    verificada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    estado = models.CharField(max_length=12, choices=ESTADOS, default="PENDIENTE")
    motivo_rechazo = models.TextField(blank=True)
    documento_soporte = models.ForeignKey("documentos.Documento", on_delete=models.PROTECT, null=True, blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["proveedor"],condition=Q(principal=True)&~Q(estado="INACTIVA"),name="cmp_cuenta_principal_uniq")]
        permissions=[("verificar_cuenta_bancaria","Puede verificar cuentas bancarias"),("view_datos_bancarios_completos","Puede ver datos bancarios completos")]
    def clean(self):
        if self.proveedor_id and self.proveedor.empresa_id != self.empresa_id: raise ValidationError("El proveedor pertenece a otra empresa.")
        if self.moneda_id and self.moneda.empresa_id != self.empresa_id: raise ValidationError("La moneda pertenece a otra empresa.")
    def set_numero(self, numero):
        self.numero_cuenta = numero.strip()
        limpio = normalizar_identificacion(numero)
        self.numero_enmascarado = f"•••• {limpio[-4:]}" if limpio else "Sin número"


class RequisitoDocumentoProveedor(AuditMixin):
    categoria = models.ForeignKey(CategoriaProveedor, on_delete=models.PROTECT, related_name="requisitos_documentales")
    tipo_documento = models.ForeignKey("documentos.TipoDocumento", on_delete=models.PROTECT)
    obligatorio = models.BooleanField(default=True); requiere_vencimiento = models.BooleanField(default=False)
    vigencia_dias = models.PositiveIntegerField(null=True, blank=True); bloquea_compra_si_vence = models.BooleanField(default=False)
    aplica_desde = models.DateField(null=True, blank=True); aplica_hasta = models.DateField(null=True, blank=True); activo = models.BooleanField(default=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["empresa","categoria","tipo_documento"],condition=Q(activo=True),name="cmp_reqdoc_activo_uniq")]


class RevisionDocumentoProveedor(AuditMixin):
    RESULTADOS=(("PENDIENTE","Pendiente"),("APROBADO","Aprobado"),("RECHAZADO","Rechazado"))
    documento = models.ForeignKey("documentos.Documento", on_delete=models.PROTECT, related_name="revisiones_proveedor")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="revisiones_documentales")
    resultado = models.CharField(max_length=12, choices=RESULTADOS)
    comentario = models.TextField(blank=True)
    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    fecha = models.DateTimeField(auto_now_add=True)


class ProveedorLegadoMap(AuditMixin):
    ESTADOS=(("PROPUESTO","Propuesto"),("CONFIRMADO","Confirmado"),("CONFLICTO","Conflicto"),("IGNORADO","Ignorado"))
    METODOS=tuple((x,x.replace("_"," ").title()) for x in ("RNC_EXACTO","RNC_NORMALIZADO","NOMBRE_EXACTO","NOMBRE_SIMILAR","MANUAL","IMPORTACION","OTRO"))
    proveedor_nuevo = models.ForeignKey(Proveedor,on_delete=models.PROTECT,related_name="correspondencias_legado")
    proveedor_legacy = models.ForeignKey("contabilidad.Proveedor",on_delete=models.PROTECT,related_name="correspondencias_enterprise")
    origen=models.CharField(max_length=80,default="LEGADO_CONTABILIDAD")
    metodo_correspondencia=models.CharField(max_length=20,choices=METODOS)
    confianza=models.DecimalField(max_digits=5,decimal_places=2,default=Decimal("100"))
    estado=models.CharField(max_length=12,choices=ESTADOS,default="PROPUESTO")
    observaciones=models.TextField(blank=True)
    confirmado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+")
    class Meta:
        constraints=[models.UniqueConstraint(fields=["empresa","proveedor_legacy"],name="cmp_legado_empresa_uniq")]


class HistorialEstadoProveedor(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE)
    proveedor=models.ForeignKey(Proveedor,on_delete=models.PROTECT,related_name="historial_estados")
    estado_anterior=models.CharField(max_length=20,choices=Proveedor.Estado.choices)
    estado_nuevo=models.CharField(max_length=20,choices=Proveedor.Estado.choices)
    motivo=models.TextField()
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    fecha=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-fecha"]
