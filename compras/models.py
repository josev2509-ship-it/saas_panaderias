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


class SolicitudCompra(AuditMixin):
    class Naturaleza(models.TextChoices):
        BIEN="BIEN","Bien"; SERVICIO="SERVICIO","Servicio"; ACTIVO="ACTIVO","Activo"
        MANTENIMIENTO="MANTENIMIENTO","Mantenimiento"; MIXTA="MIXTA","Mixta"
    class Prioridad(models.TextChoices):
        BAJA="BAJA","Baja"; NORMAL="NORMAL","Normal"; ALTA="ALTA","Alta"; URGENTE="URGENTE","Urgente"
    class Estado(models.TextChoices):
        BORRADOR="BORRADOR","Borrador"; LISTA_PARA_ENVIO="LISTA_PARA_ENVIO","Lista para envío"
        EN_APROBACION="EN_APROBACION","En aprobación"; DEVUELTA="DEVUELTA","Devuelta"
        APROBADA="APROBADA","Aprobada"; RECHAZADA="RECHAZADA","Rechazada"
        CANCELADA="CANCELADA","Cancelada"; CERRADA="CERRADA","Cerrada"
    class Disponibilidad(models.TextChoices):
        NO_VALIDADA="NO_VALIDADA","No validada"; DECLARADA_DISPONIBLE="DECLARADA_DISPONIBLE","Declarada disponible"
        DECLARADA_NO_DISPONIBLE="DECLARADA_NO_DISPONIBLE","Declarada no disponible"; NO_APLICA="NO_APLICA","No aplica"

    numero=models.CharField(max_length=30)
    referencia_externa=models.CharField(max_length=100,blank=True)
    version_documento=models.PositiveIntegerField(default=1)
    titulo=models.CharField(max_length=200)
    descripcion_corta=models.CharField(max_length=300,blank=True)
    solicitante=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="solicitudes_compra")
    area_solicitante=models.CharField(max_length=100,blank=True)
    centro_costo=models.ForeignKey("catalogos.CentroCosto",on_delete=models.PROTECT,related_name="solicitudes_compra")
    responsable_centro_costo=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+")
    almacen_destino=models.ForeignKey("catalogos.Almacen",on_delete=models.PROTECT,null=True,blank=True,related_name="solicitudes_compra")
    proyecto_codigo=models.CharField(max_length=50,blank=True); proyecto_nombre=models.CharField(max_length=160,blank=True)
    tipo_compra=models.ForeignKey("catalogos.TipoCompra",on_delete=models.PROTECT,related_name="solicitudes_compra")
    naturaleza=models.CharField(max_length=20,choices=Naturaleza.choices)
    prioridad=models.CharField(max_length=12,choices=Prioridad.choices,default=Prioridad.NORMAL)
    origen_necesidad=models.CharField(max_length=160,blank=True)
    es_urgente=models.BooleanField(default=False); compra_directa_propuesta=models.BooleanField(default=False)
    motivo_compra_directa=models.TextField(blank=True); requiere_contrato=models.BooleanField(default=False)
    requiere_inspeccion=models.BooleanField(default=False); requiere_activo_fijo=models.BooleanField(default=False)
    requiere_entrega_parcial=models.BooleanField(default=False); recurrente=models.BooleanField(default=False)
    frecuencia_recurrencia=models.CharField(max_length=80,blank=True)
    fecha_solicitud=models.DateField(); fecha_necesaria=models.DateField(); fecha_limite_proceso=models.DateField(null=True,blank=True)
    periodo_presupuestario=models.CharField(max_length=30,blank=True)
    moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT,related_name="solicitudes_compra")
    subtotal_estimado=models.DecimalField(max_digits=18,decimal_places=2,default=0)
    descuento_estimado=models.DecimalField(max_digits=18,decimal_places=2,default=0)
    impuesto_estimado=models.DecimalField(max_digits=18,decimal_places=2,default=0)
    total_estimado=models.DecimalField(max_digits=18,decimal_places=2,default=0)
    disponibilidad_presupuestaria=models.CharField(max_length=30,choices=Disponibilidad.choices,default=Disponibilidad.NO_VALIDADA)
    referencia_presupuestaria=models.CharField(max_length=100,blank=True); observacion_presupuestaria=models.TextField(blank=True)
    proveedor_sugerido=models.ForeignKey(Proveedor,on_delete=models.PROTECT,null=True,blank=True,related_name="solicitudes_sugeridas")
    justificacion_proveedor_sugerido=models.TextField(blank=True); proveedor_exclusivo_declarado=models.BooleanField(default=False)
    motivo_exclusividad=models.TextField(blank=True)
    justificacion=models.TextField(); impacto_no_compra=models.TextField(); alcance=models.TextField(blank=True)
    observaciones_internas=models.TextField(blank=True); observaciones_aprobadores=models.TextField(blank=True); riesgos_identificados=models.TextField(blank=True)
    estado=models.CharField(max_length=20,choices=Estado.choices,default=Estado.BORRADOR)
    estado_workflow_snapshot=models.CharField(max_length=20,blank=True)
    workflow_instancia=models.ForeignKey("workflow.InstanciaWorkflow",on_delete=models.PROTECT,null=True,blank=True,related_name="solicitudes_compra")
    ronda_workflow_actual=models.PositiveIntegerField(null=True,blank=True)
    enviada_en=models.DateTimeField(null=True,blank=True); aprobada_en=models.DateTimeField(null=True,blank=True)
    rechazada_en=models.DateTimeField(null=True,blank=True); devuelta_en=models.DateTimeField(null=True,blank=True)
    cancelada_en=models.DateTimeField(null=True,blank=True); cerrada_en=models.DateTimeField(null=True,blank=True)
    motivo_rechazo=models.TextField(blank=True); motivo_cancelacion=models.TextField(blank=True); comentario_devolucion_actual=models.TextField(blank=True)
    enviada_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+")
    aprobada_por_sistema=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+")
    rechazada_por_sistema=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+")
    origen_duplicacion=models.ForeignKey("self",on_delete=models.PROTECT,null=True,blank=True,related_name="duplicados")

    class Meta:
        ordering=["-fecha_solicitud","-id"]
        constraints=[
            models.UniqueConstraint(fields=["empresa","numero"],name="cmp_sol_emp_num_uniq"),
            models.CheckConstraint(condition=Q(version_documento__gt=0),name="cmp_sol_version_pos"),
            models.CheckConstraint(condition=Q(subtotal_estimado__gte=0,descuento_estimado__gte=0,impuesto_estimado__gte=0,total_estimado__gte=0),name="cmp_sol_totales_no_neg"),
        ]
        indexes=[models.Index(fields=["empresa","estado"],name="cmp_sol_emp_estado_idx"),models.Index(fields=["empresa","fecha_solicitud"],name="cmp_sol_emp_fecha_idx"),models.Index(fields=["empresa","solicitante"],name="cmp_sol_emp_solic_idx"),models.Index(fields=["empresa","prioridad"],name="cmp_sol_emp_prior_idx")]
        permissions=[("enviar_solicitudcompra","Puede enviar solicitudes"),("cancelar_solicitudcompra","Puede cancelar solicitudes"),("duplicar_solicitudcompra","Puede duplicar solicitudes"),("corregir_solicitudcompra","Puede corregir solicitudes"),("view_historial_solicitudcompra","Puede ver historial"),("view_todas_solicitudescompra","Puede ver todas las solicitudes"),("exportar_solicitudescompra","Puede exportar solicitudes"),("administrar_solicitudescompra","Puede administrar solicitudes"),("gestionar_documentos_solicitudcompra","Puede gestionar documentos"),("marcar_lista_solicitudcompra","Puede marcar solicitudes listas"),("devolver_borrador_solicitudcompra","Puede devolver solicitudes a borrador")]

    def clean(self):
        errors={}
        if self.fecha_necesaria and self.fecha_solicitud and self.fecha_necesaria < self.fecha_solicitud: errors["fecha_necesaria"]="No puede ser anterior a la solicitud."
        for field in ("centro_costo","almacen_destino","tipo_compra","moneda","proveedor_sugerido"):
            obj=getattr(self,field,None)
            if obj and obj.empresa_id != self.empresa_id: errors[field]="El registro pertenece a otra empresa."
        if self.compra_directa_propuesta and not self.motivo_compra_directa.strip(): errors["motivo_compra_directa"]="Debe justificar la compra directa."
        if self.proveedor_exclusivo_declarado and not self.motivo_exclusividad.strip(): errors["motivo_exclusividad"]="Debe justificar la exclusividad."
        if self.recurrente and not self.frecuencia_recurrencia.strip(): errors["frecuencia_recurrencia"]="Indique la frecuencia."
        if errors: raise ValidationError(errors)
    def __str__(self): return f"{self.numero} · {self.titulo}"


class DetalleSolicitudCompra(models.Model):
    TIPOS=(("PRODUCTO","Producto"),("SERVICIO","Servicio"),("LIBRE","Libre"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE)
    solicitud=models.ForeignKey(SolicitudCompra,on_delete=models.PROTECT,related_name="lineas")
    orden=models.PositiveIntegerField(); tipo_linea=models.CharField(max_length=12,choices=TIPOS)
    producto=models.ForeignKey("inventario.ProductoInventario",on_delete=models.PROTECT,null=True,blank=True,related_name="detalles_solicitud_compra")
    codigo_producto_snapshot=models.CharField(max_length=50,blank=True); descripcion=models.CharField(max_length=300); especificacion_tecnica=models.TextField(blank=True)
    cantidad=models.DecimalField(max_digits=18,decimal_places=4); unidad_medida=models.ForeignKey("catalogos.UnidadMedida",on_delete=models.PROTECT)
    unidad_producto_snapshot=models.CharField(max_length=80,blank=True); factor_conversion=models.DecimalField(max_digits=18,decimal_places=8,default=1)
    cantidad_base=models.DecimalField(max_digits=18,decimal_places=4,null=True,blank=True); precio_unitario_estimado=models.DecimalField(max_digits=18,decimal_places=4,default=0)
    descuento_porcentaje=models.DecimalField(max_digits=7,decimal_places=4,default=0); descuento_monto=models.DecimalField(max_digits=18,decimal_places=2,default=0)
    impuesto=models.ForeignKey("catalogos.Impuesto",on_delete=models.PROTECT,null=True,blank=True); impuesto_porcentaje_snapshot=models.DecimalField(max_digits=7,decimal_places=4,default=0)
    impuesto_monto=models.DecimalField(max_digits=18,decimal_places=2,default=0); subtotal=models.DecimalField(max_digits=18,decimal_places=2,default=0); total=models.DecimalField(max_digits=18,decimal_places=2,default=0)
    fecha_necesaria_linea=models.DateField(null=True,blank=True); almacen_destino=models.ForeignKey("catalogos.Almacen",on_delete=models.PROTECT,null=True,blank=True,related_name="lineas_solicitud_compra")
    centro_costo=models.ForeignKey("catalogos.CentroCosto",on_delete=models.PROTECT,null=True,blank=True,related_name="lineas_solicitud_compra")
    proveedor_sugerido=models.ForeignKey(Proveedor,on_delete=models.PROTECT,null=True,blank=True,related_name="lineas_sugeridas")
    marca_referencia=models.CharField(max_length=100,blank=True); modelo_referencia=models.CharField(max_length=100,blank=True)
    permite_equivalente=models.BooleanField(default=True); justificacion_no_equivalente=models.TextField(blank=True); observaciones=models.TextField(blank=True)
    activo=models.BooleanField(default=True); creado_en=models.DateTimeField(auto_now_add=True); actualizado_en=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=["orden","id"]
        constraints=[models.UniqueConstraint(fields=["solicitud","orden"],name="cmp_dsol_orden_uniq"),models.CheckConstraint(condition=Q(cantidad__gt=0),name="cmp_dsol_cantidad_pos"),models.CheckConstraint(condition=Q(precio_unitario_estimado__gte=0,descuento_monto__gte=0,subtotal__gte=0,impuesto_monto__gte=0,total__gte=0),name="cmp_dsol_importes_no_neg"),models.CheckConstraint(condition=Q(descuento_porcentaje__gte=0,descuento_porcentaje__lte=100,impuesto_porcentaje_snapshot__gte=0,impuesto_porcentaje_snapshot__lte=100),name="cmp_dsol_pct_rango")]
    def clean(self):
        errors={}
        if self.solicitud_id and self.solicitud.empresa_id != self.empresa_id: errors["solicitud"]="La solicitud pertenece a otra empresa."
        for field in ("producto","unidad_medida","impuesto","almacen_destino","centro_costo","proveedor_sugerido"):
            obj=getattr(self,field,None)
            if obj and obj.empresa_id != self.empresa_id: errors[field]="El registro pertenece a otra empresa."
        if self.tipo_linea=="PRODUCTO" and not self.producto_id: errors["producto"]="Seleccione un producto."
        if self.tipo_linea!="PRODUCTO" and self.producto_id: errors["producto"]="Solo una línea de producto admite producto."
        if not self.permite_equivalente and not self.justificacion_no_equivalente.strip(): errors["justificacion_no_equivalente"]="Debe justificar por qué no admite equivalente."
        if errors: raise ValidationError(errors)


class HistorialEstadoSolicitudCompra(models.Model):
    ORIGENES=(("USUARIO","Usuario"),("WORKFLOW","Workflow"),("SISTEMA","Sistema"),("ADMINISTRADOR","Administrador"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE); solicitud=models.ForeignKey(SolicitudCompra,on_delete=models.PROTECT,related_name="historial")
    estado_anterior=models.CharField(max_length=20,blank=True); estado_nuevo=models.CharField(max_length=20)
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True); comentario=models.TextField(blank=True)
    origen=models.CharField(max_length=20,choices=ORIGENES); workflow_instancia_id=models.PositiveBigIntegerField(null=True,blank=True); ronda=models.PositiveIntegerField(null=True,blank=True)
    fecha=models.DateTimeField(auto_now_add=True); metadata_segura=models.JSONField(default=dict,blank=True)
    class Meta: ordering=["fecha","id"]; default_permissions=("view",)
    def save(self,*args,**kwargs):
        if self.pk: raise ValidationError("El historial es inmutable.")
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs): raise ValidationError("El historial no se elimina.")


class ExpedienteCompra(AuditMixin):
    ESTADOS=tuple((x,x.replace("_"," ").title()) for x in ("BORRADOR","ABIERTO","PREPARANDO_RFQ","RFQ_ABIERTA","RECIBIENDO_OFERTAS","EN_EVALUACION","ADJUDICADA","DESIERTA","CANCELADA","CERRADA"))
    RIESGOS=tuple((x,x.title()) for x in ("BAJO","MEDIO","ALTO","CRITICO"))
    numero=models.CharField(max_length=30);titulo=models.CharField(max_length=200);descripcion=models.TextField(blank=True)
    responsable=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="expedientes_compra_responsable");solicitante_principal=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="expedientes_compra_solicitante")
    centro_costo=models.ForeignKey("catalogos.CentroCosto",on_delete=models.PROTECT);tipo_compra=models.ForeignKey("catalogos.TipoCompra",on_delete=models.PROTECT);prioridad=models.CharField(max_length=12,choices=SolicitudCompra.Prioridad.choices);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT)
    presupuesto_estimado=models.DecimalField(max_digits=18,decimal_places=2,default=0);monto_aprobado_solicitudes=models.DecimalField(max_digits=18,decimal_places=2,default=0);monto_comprometido=models.DecimalField(max_digits=18,decimal_places=2,default=0)
    estado=models.CharField(max_length=24,choices=ESTADOS,default="BORRADOR");nivel_riesgo=models.CharField(max_length=10,choices=RIESGOS,default="BAJO");indice_salud=models.DecimalField(max_digits=5,decimal_places=2,default=0)
    fecha_apertura=models.DateTimeField(null=True,blank=True);fecha_cierre=models.DateTimeField(null=True,blank=True);motivo_cierre=models.TextField(blank=True);motivo_cancelacion=models.TextField(blank=True);observaciones=models.TextField(blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="cmp_exp_emp_num_uniq"),models.CheckConstraint(condition=Q(presupuesto_estimado__gte=0,monto_aprobado_solicitudes__gte=0,monto_comprometido__gte=0),name="cmp_exp_montos_no_neg"),models.CheckConstraint(condition=Q(indice_salud__gte=0,indice_salud__lte=100),name="cmp_exp_salud_rango")]
        indexes=[models.Index(fields=["empresa","estado"],name="cmp_exp_emp_estado_idx"),models.Index(fields=["empresa","nivel_riesgo"],name="cmp_exp_emp_riesgo_idx")]
        permissions=[("abrir_expedientecompra","Puede abrir expedientes"),("cancelar_expedientecompra","Puede cancelar expedientes"),("declarar_desierto_expedientecompra","Puede declarar expedientes desiertos"),("recalcular_salud_expedientecompra","Puede recalcular salud"),("view_historial_expedientecompra","Puede ver historial de expedientes"),("exportar_expedientecompra","Puede exportar expedientes"),("administrar_expedientecompra","Puede administrar expedientes")]
    def clean(self):
        errors={}
        for f in ("centro_costo","tipo_compra","moneda"):
            o=getattr(self,f,None)
            if o and o.empresa_id!=self.empresa_id:errors[f]="El registro pertenece a otra empresa."
        if errors:raise ValidationError(errors)
    def __str__(self):return f"{self.numero} · {self.titulo}"

class SolicitudExpedienteCompra(models.Model):
    TIPOS=(("ORIGEN","Origen"),("COMPLEMENTARIA","Complementaria"),("AMPLIACION","Ampliación"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);expediente=models.ForeignKey(ExpedienteCompra,on_delete=models.PROTECT,related_name="solicitudes_vinculadas");solicitud=models.ForeignKey(SolicitudCompra,on_delete=models.PROTECT,related_name="vinculos_expediente")
    tipo_relacion=models.CharField(max_length=20,choices=TIPOS,default="ORIGEN");principal=models.BooleanField(default=False);monto_snapshot=models.DecimalField(max_digits=18,decimal_places=2);moneda_snapshot=models.CharField(max_length=3);estado_snapshot=models.CharField(max_length=20)
    vinculada_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT);fecha_vinculacion=models.DateTimeField(auto_now_add=True);activa=models.BooleanField(default=True);observaciones=models.TextField(blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","solicitud"],condition=Q(activa=True),name="cmp_vexp_sol_activa_uniq"),models.UniqueConstraint(fields=["expediente"],condition=Q(principal=True,activa=True),name="cmp_vexp_principal_uniq")]

class ProcesoRFQ(AuditMixin):
    ESTADOS=tuple((x,x.replace("_"," ").title()) for x in ("BORRADOR","EN_REVISION","PUBLICADA","ABIERTA","CERRADA","EXTENDIDA","CANCELADA","DESIERTA"))
    expediente=models.ForeignKey(ExpedienteCompra,on_delete=models.PROTECT,related_name="rfqs");numero=models.CharField(max_length=30);version=models.PositiveIntegerField(default=1);titulo=models.CharField(max_length=200);objeto=models.TextField();descripcion=models.TextField();estado=models.CharField(max_length=15,choices=ESTADOS,default="BORRADOR");moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT)
    fecha_publicacion=models.DateTimeField(null=True,blank=True);fecha_inicio=models.DateTimeField();fecha_limite=models.DateTimeField();fecha_apertura_ofertas=models.DateTimeField(null=True,blank=True);fecha_cierre_real=models.DateTimeField(null=True,blank=True);entrega_requerida_desde=models.DateField();entrega_requerida_hasta=models.DateField();lugar_entrega=models.TextField();almacen_destino=models.ForeignKey("catalogos.Almacen",on_delete=models.PROTECT,null=True,blank=True)
    incoterm=models.CharField(max_length=30,blank=True);permite_oferta_parcial=models.BooleanField(default=False);permite_variantes=models.BooleanField(default=False);permite_equivalentes=models.BooleanField(default=True);requiere_garantia=models.BooleanField(default=False);requiere_muestra=models.BooleanField(default=False);requiere_visita_tecnica=models.BooleanField(default=False);confidencial=models.BooleanField(default=False);minimo_proveedores=models.PositiveIntegerField(default=3);minimo_ofertas_validas=models.PositiveIntegerField(default=2)
    condiciones_comerciales=models.TextField();instrucciones_proveedor=models.TextField(blank=True);criterios_generales=models.TextField(blank=True);motivo_extension=models.TextField(blank=True);motivo_cancelacion=models.TextField(blank=True);publicado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+");cerrado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+")
    class Meta:
        constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="cmp_rfq_emp_num_uniq"),models.UniqueConstraint(fields=["expediente","version"],name="cmp_rfq_exp_ver_uniq"),models.CheckConstraint(condition=Q(version__gt=0),name="cmp_rfq_version_pos")]
        indexes=[models.Index(fields=["empresa","estado","fecha_limite"],name="cmp_rfq_estado_fecha_idx")]
        permissions=[("enviar_revision_rfq","Puede enviar RFQ a revisión"),("devolver_borrador_rfq","Puede devolver RFQ a borrador"),("publicar_rfq","Puede publicar RFQ"),("abrir_rfq","Puede abrir RFQ"),("extender_rfq","Puede extender RFQ"),("cerrar_rfq","Puede cerrar RFQ"),("cancelar_rfq","Puede cancelar RFQ"),("versionar_rfq","Puede versionar RFQ"),("gestionar_criterios_rfq","Puede gestionar criterios RFQ"),("gestionar_reglas_rfq","Puede gestionar reglas RFQ"),("gestionar_proveedores_rfq","Puede gestionar proveedores RFQ"),("exportar_rfq","Puede exportar RFQ")]
    def clean(self):
        if self.expediente_id and self.expediente.empresa_id!=self.empresa_id:raise ValidationError("El expediente pertenece a otra empresa.")
        if self.fecha_limite<=self.fecha_inicio:raise ValidationError({"fecha_limite":"Debe ser posterior al inicio."})
        if self.entrega_requerida_hasta<self.entrega_requerida_desde:raise ValidationError({"entrega_requerida_hasta":"Rango inválido."})
    def __str__(self):return f"{self.numero} v{self.version}"

class DetalleRFQ(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);rfq=models.ForeignKey(ProcesoRFQ,on_delete=models.PROTECT,related_name="lineas");linea_origen_solicitud=models.ForeignKey(DetalleSolicitudCompra,on_delete=models.PROTECT,null=True,blank=True);orden=models.PositiveIntegerField();tipo_linea=models.CharField(max_length=12,choices=DetalleSolicitudCompra.TIPOS);producto=models.ForeignKey("inventario.ProductoInventario",on_delete=models.PROTECT,null=True,blank=True);codigo_snapshot=models.CharField(max_length=50,blank=True);descripcion=models.CharField(max_length=300);especificacion_tecnica=models.TextField(blank=True);cantidad=models.DecimalField(max_digits=18,decimal_places=4);unidad_medida=models.ForeignKey("catalogos.UnidadMedida",on_delete=models.PROTECT);factor_conversion=models.DecimalField(max_digits=18,decimal_places=8,default=1);cantidad_base=models.DecimalField(max_digits=18,decimal_places=4,null=True,blank=True);fecha_entrega_requerida=models.DateField();almacen_destino=models.ForeignKey("catalogos.Almacen",on_delete=models.PROTECT,null=True,blank=True);permite_equivalente=models.BooleanField(default=True);marca_referencia=models.CharField(max_length=100,blank=True);modelo_referencia=models.CharField(max_length=100,blank=True);requisitos_documentales=models.TextField(blank=True);observaciones=models.TextField(blank=True);activo=models.BooleanField(default=True);creado_en=models.DateTimeField(auto_now_add=True);actualizado_en=models.DateTimeField(auto_now=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["rfq","orden"],name="cmp_drfq_orden_uniq"),models.UniqueConstraint(fields=["rfq","linea_origen_solicitud"],condition=Q(linea_origen_solicitud__isnull=False,activo=True),name="cmp_drfq_origen_uniq"),models.CheckConstraint(condition=Q(cantidad__gt=0),name="cmp_drfq_cantidad_pos")]

class CriterioEvaluacionRFQ(models.Model):
    CATEGORIAS=tuple((x,x.title()) for x in ("ECONOMICO","TECNICO","ENTREGA","CALIDAD","DOCUMENTAL","GARANTIA","EXPERIENCIA","RIESGO","OTRO"));METODOS=tuple((x,x.replace("_"," ").title()) for x in ("PUNTAJE","CUMPLE_NO_CUMPLE","MENOR_ES_MEJOR","MAYOR_ES_MEJOR","MANUAL"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);rfq=models.ForeignKey(ProcesoRFQ,on_delete=models.PROTECT,related_name="criterios");codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=120);categoria=models.CharField(max_length=15,choices=CATEGORIAS);descripcion=models.TextField(blank=True);peso_porcentaje=models.DecimalField(max_digits=5,decimal_places=2);obligatorio=models.BooleanField(default=True);excluyente=models.BooleanField(default=False);metodo_evaluacion=models.CharField(max_length=20,choices=METODOS);orden=models.PositiveIntegerField(default=0);activo=models.BooleanField(default=True);creado_en=models.DateTimeField(auto_now_add=True);actualizado_en=models.DateTimeField(auto_now=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["rfq","codigo"],name="cmp_crfq_codigo_uniq"),models.CheckConstraint(condition=Q(peso_porcentaje__gte=0,peso_porcentaje__lte=100),name="cmp_crfq_peso_rango")]

class InvitacionProveedorRFQ(AuditMixin):
    ESTADOS=tuple((x,x.replace("_"," ").title()) for x in ("BORRADOR","PENDIENTE_ENVIO","INVITADA","CONFIRMADA","DECLINADA","SIN_RESPUESTA","RETIRADA"));CANALES=(("INTERNO","Interno"),("CORREO","Correo"),("PORTAL","Portal"),("MANUAL","Manual"))
    rfq=models.ForeignKey(ProcesoRFQ,on_delete=models.PROTECT,related_name="invitaciones");proveedor=models.ForeignKey(Proveedor,on_delete=models.PROTECT,related_name="invitaciones_rfq");contacto=models.ForeignKey(ContactoProveedor,on_delete=models.PROTECT,null=True,blank=True);estado=models.CharField(max_length=20,choices=ESTADOS,default="BORRADOR");fecha_invitacion=models.DateTimeField(null=True,blank=True);fecha_limite_respuesta=models.DateTimeField(null=True,blank=True);fecha_confirmacion=models.DateTimeField(null=True,blank=True);fecha_declinacion=models.DateTimeField(null=True,blank=True);motivo_declinacion=models.TextField(blank=True);canal=models.CharField(max_length=10,choices=CANALES,default="INTERNO");observaciones=models.TextField(blank=True);invitada_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+")
    class Meta:constraints=[models.UniqueConstraint(fields=["rfq","proveedor"],name="cmp_inv_rfq_prov_uniq")];permissions=[("gestionar_invitacionrfq","Puede gestionar invitaciones RFQ"),("marcar_enviada_invitacionrfq","Puede marcar invitación enviada"),("confirmar_participacion_rfq","Puede confirmar participación"),("registrar_declinacion_rfq","Puede registrar declinación"),("marcar_sin_respuesta_rfq","Puede marcar sin respuesta"),("retirar_proveedor_rfq","Puede retirar proveedor RFQ")]

class ReglaParticipacionRFQ(models.Model):
    TIPOS=tuple((x,x.replace("_"," ").title()) for x in ("DOCUMENTO_OBLIGATORIO","CERTIFICACION_VIGENTE","EXPERIENCIA_MINIMA","GARANTIA","MUESTRA","VISITA_TECNICA","DECLARACION","OTRO"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);rfq=models.ForeignKey(ProcesoRFQ,on_delete=models.PROTECT,related_name="reglas_participacion");codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=120);descripcion=models.TextField(blank=True);tipo=models.CharField(max_length=30,choices=TIPOS);obligatorio=models.BooleanField(default=True);excluyente=models.BooleanField(default=False);parametro_texto=models.TextField(blank=True);parametro_decimal=models.DecimalField(max_digits=18,decimal_places=4,null=True,blank=True);parametro_entero=models.BigIntegerField(null=True,blank=True);fecha_limite=models.DateTimeField(null=True,blank=True);orden=models.PositiveIntegerField(default=0);activo=models.BooleanField(default=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["rfq","codigo"],name="cmp_rrfq_codigo_uniq")]

class HistorialEstadoExpedienteCompra(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);expediente=models.ForeignKey(ExpedienteCompra,on_delete=models.PROTECT,related_name="historial");estado_anterior=models.CharField(max_length=24,blank=True);estado_nuevo=models.CharField(max_length=24);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);comentario=models.TextField(blank=True);fecha=models.DateTimeField(auto_now_add=True);metadata_segura=models.JSONField(default=dict,blank=True)
    class Meta:default_permissions=("view",);ordering=["fecha"]
    def save(self,*a,**k):
        if self.pk:raise ValidationError("El historial es inmutable.")
        super().save(*a,**k)
    def delete(self,*a,**k):raise ValidationError("El historial no se elimina.")

class HistorialEstadoRFQ(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);rfq=models.ForeignKey(ProcesoRFQ,on_delete=models.PROTECT,related_name="historial");estado_anterior=models.CharField(max_length=15,blank=True);estado_nuevo=models.CharField(max_length=15);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);comentario=models.TextField(blank=True);fecha=models.DateTimeField(auto_now_add=True);metadata_segura=models.JSONField(default=dict,blank=True)
    class Meta:default_permissions=("view",);ordering=["fecha"]
    def save(self,*a,**k):
        if self.pk:raise ValidationError("El historial es inmutable.")
        super().save(*a,**k)
    def delete(self,*a,**k):raise ValidationError("El historial no se elimina.")
