from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from conduces.models import Empresa
from inventario.models import ProductoInventario


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
    segmento = models.ForeignKey("SegmentoCliente",on_delete=models.PROTECT,null=True,blank=True,related_name="clientes")
    clasificacion = models.ForeignKey("ClasificacionCliente",on_delete=models.PROTECT,null=True,blank=True,related_name="clientes")
    canal = models.ForeignKey("CanalVenta",on_delete=models.PROTECT,null=True,blank=True,related_name="clientes")
    vendedor = models.ForeignKey("VendedorComercial",on_delete=models.PROTECT,null=True,blank=True,related_name="clientes")
    equipo = models.ForeignKey("EquipoComercial",on_delete=models.PROTECT,null=True,blank=True,related_name="clientes")
    zona = models.ForeignKey("ZonaComercial",on_delete=models.PROTECT,null=True,blank=True,related_name="clientes")
    ruta = models.ForeignKey("RutaComercial",on_delete=models.PROTECT,null=True,blank=True,related_name="clientes")
    moneda_comercial = models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT,null=True,blank=True,related_name="clientes_comerciales")
    condicion_pago_catalogo = models.ForeignKey("catalogos.CondicionPago",on_delete=models.PROTECT,null=True,blank=True,related_name="clientes_comerciales")
    credito_utilizado = models.DecimalField(max_digits=14,decimal_places=2,default=0)
    exento_impuestos = models.BooleanField(default=False)
    retenciones = models.JSONField(default=dict,blank=True)
    categoria_riesgo = models.CharField(max_length=12,default="MEDIO")
    score_riesgo = models.PositiveSmallIntegerField(default=50)
    explicacion_riesgo = models.JSONField(default=list,blank=True)
    version_formula_riesgo = models.CharField(max_length=20,default="1.0")
    fecha_calculo_riesgo = models.DateTimeField(null=True,blank=True)
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
            models.CheckConstraint(condition=Q(credito_utilizado__gte=0),name="com_cliente_credito_util_no_neg"),
            models.CheckConstraint(condition=Q(score_riesgo__gte=0,score_riesgo__lte=100),name="com_cliente_score_rango"),
            models.UniqueConstraint(fields=["empresa","rnc_cedula"],condition=~Q(rnc_cedula=""),name="com_cliente_emp_ident_uniq"),
        ]
        permissions=[("bloquear_credito_cliente","Puede bloquear crédito de clientes"),("gestionar_credito_cliente","Puede gestionar crédito de clientes"),("calcular_riesgo_cliente","Puede calcular riesgo de clientes"),("administrar_cliente_360","Puede administrar Cliente 360"),("exportar_cliente_360","Puede exportar Cliente 360")]
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

    @property
    def credito_disponible(self):return max(Decimal("0"),(self.limite_credito or 0)-(self.credito_utilizado or 0))
    def delete(self,*a,**k):raise ValidationError("Los clientes no se eliminan físicamente.")

    def __str__(self):
        return f"{self.codigo} - {self.nombre_comercial}"


class DireccionCliente(models.Model):
    class Tipo(models.TextChoices):
        FISCAL = "FISCAL", "Fiscal"
        ENTREGA = "ENTREGA", "Entrega"
        COBRO = "COBRO", "Cobro"
        OTRO = "OTRO", "Otro"
        SUCURSAL = "SUCURSAL", "Sucursal"

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
    recibe_compras = models.BooleanField(default=False)
    recibe_cobranzas = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-es_principal", "nombre"]

    def __str__(self):
        return f"{self.nombre} - {self.cliente.nombre_comercial}"


class SecuenciaDocumento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=30)
    periodo = models.PositiveIntegerField()
    ultimo_numero = models.PositiveIntegerField(default=0)
    prefijo = models.CharField(max_length=10, blank=True)
    longitud = models.PositiveSmallIntegerField(default=6)
    activo = models.BooleanField(default=True)
    reinicia_anualmente = models.BooleanField(default=True)
    fecha_ultima_emision = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    actualizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["empresa", "tipo", "periodo"], name="com_secuencia_empresa_tipo_periodo_uniq")
        ]


class Pedido(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        NORMAL = "NORMAL", "Normal"
        ALTA = "ALTA", "Alta"
        URGENTE = "URGENTE", "Urgente"

    class Moneda(models.TextChoices):
        DOP = "DOP", "DOP"
        USD = "USD", "USD"

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PENDIENTE_APROBACION = "PENDIENTE_APROBACION", "Pendiente de aprobación"
        APROBADO = "APROBADO", "Aprobado"
        RECHAZADO = "RECHAZADO", "Rechazado"
        CANCELADO = "CANCELADO", "Cancelado"
        EN_PREPARACION = "EN_PREPARACION", "En preparación"
        LISTO_DESPACHO = "LISTO_DESPACHO", "Listo para despacho"
        DESPACHADO = "DESPACHADO", "Despachado"
        ENTREGADO_PARCIAL = "ENTREGADO_PARCIAL", "Entregado parcial"
        ENTREGADO = "ENTREGADO", "Entregado"
        FACTURADO = "FACTURADO", "Facturado"
        EN_PROGRAMACION = "EN_PROGRAMACION", "En programación"
        PROGRAMADO = "PROGRAMADO", "Programado"

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="pedidos")
    cotizacion_origen = models.OneToOneField("CotizacionVenta",on_delete=models.PROTECT,null=True,blank=True,related_name="pedido_convertido")
    numero = models.CharField(max_length=30)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pedidos")
    direccion_entrega = models.ForeignKey(DireccionCliente, on_delete=models.PROTECT, null=True, blank=True)
    contacto = models.ForeignKey(ContactoCliente, on_delete=models.PROTECT, null=True, blank=True)
    fecha_pedido = models.DateField()
    fecha_entrega = models.DateField()
    hora_entrega_desde = models.TimeField(null=True, blank=True)
    hora_entrega_hasta = models.TimeField(null=True, blank=True)
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.NORMAL)
    condicion_pago = models.CharField(max_length=10, choices=Cliente.CondicionPago.choices)
    dias_credito = models.PositiveIntegerField(default=0)
    lista_precio = models.CharField(max_length=100, blank=True)
    moneda = models.CharField(max_length=3, choices=Moneda.choices, default=Moneda.DOP)
    subtotal = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    descuento_total = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    impuesto_total = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    total = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    observaciones_cliente = models.TextField(blank=True)
    observaciones_internas = models.TextField(blank=True)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.BORRADOR)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos_creados")
    actualizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos_actualizados")
    aprobado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos_aprobados")
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    rechazado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos_rechazados")
    fecha_rechazo = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_pedido", "-id"]
        constraints = [models.UniqueConstraint(fields=["empresa", "numero"], name="com_pedido_empresa_numero_uniq")]
        indexes = [
            models.Index(fields=["empresa", "estado"], name="com_ped_emp_estado_idx"),
            models.Index(fields=["empresa", "fecha_entrega"], name="com_ped_emp_entrega_idx"),
        ]
        permissions = [
            ("aprobar_pedido", "Puede aprobar pedidos"),
            ("rechazar_pedido", "Puede rechazar pedidos"),
            ("cancelar_pedido", "Puede cancelar pedidos"),
        ]

    def clean(self):
        errors = {}
        if self.cliente_id and self.empresa_id and self.cliente.empresa_id != self.empresa_id:
            errors["cliente"] = "El cliente pertenece a otra empresa."
        if self.cliente_id and self.estado == self.Estado.BORRADOR and self.cliente.estado not in {
            Cliente.Estado.ACTIVO, Cliente.Estado.EN_EVALUACION
        }:
            errors["cliente"] = "El estado del cliente no permite crear o editar borradores."
        if self.direccion_entrega_id and self.direccion_entrega.cliente_id != self.cliente_id:
            errors["direccion_entrega"] = "La dirección no pertenece al cliente seleccionado."
        if self.contacto_id and self.contacto.cliente_id != self.cliente_id:
            errors["contacto"] = "El contacto no pertenece al cliente seleccionado."
        if self.fecha_pedido and self.fecha_entrega and self.fecha_entrega < self.fecha_pedido:
            errors["fecha_entrega"] = "La fecha de entrega no puede ser anterior a la fecha del pedido."
        if self.hora_entrega_desde and self.hora_entrega_hasta and self.hora_entrega_hasta <= self.hora_entrega_desde:
            errors["hora_entrega_hasta"] = "La hora final debe ser posterior a la hora inicial."
        if self.condicion_pago == Cliente.CondicionPago.CONTADO and self.dias_credito:
            errors["dias_credito"] = "Los pedidos de contado deben tener cero días de crédito."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.numero} - {self.cliente.nombre_comercial}"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(ProductoInventario, on_delete=models.PROTECT)
    descripcion = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    unidad_medida = models.CharField(max_length=30)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=4)
    porcentaje_descuento = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    monto_descuento = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    porcentaje_impuesto = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    monto_impuesto = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    subtotal = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    total = models.DecimalField(max_digits=16, decimal_places=2, default=0, editable=False)
    observaciones = models.CharField(max_length=255, blank=True)
    orden = models.PositiveIntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["orden", "id"]
        constraints = [
            models.UniqueConstraint(fields=["pedido", "producto"], name="com_detalle_pedido_producto_uniq"),
            models.CheckConstraint(condition=Q(cantidad__gt=0), name="com_detalle_cantidad_positiva"),
            models.CheckConstraint(condition=Q(precio_unitario__gte=0), name="com_detalle_precio_no_negativo"),
            models.CheckConstraint(condition=Q(porcentaje_descuento__gte=0, porcentaje_descuento__lte=100), name="com_detalle_descuento_rango"),
            models.CheckConstraint(condition=Q(porcentaje_impuesto__gte=0, porcentaje_impuesto__lte=100), name="com_detalle_impuesto_rango"),
        ]

    def clean(self):
        errors = {}
        if self.producto_id and self.pedido_id and self.producto.empresa_id != self.pedido.empresa_id:
            errors["producto"] = "El producto pertenece a otra empresa."
        if self.cantidad is not None and self.cantidad <= 0:
            errors["cantidad"] = "La cantidad debe ser mayor que cero."
        if self.precio_unitario is not None and self.precio_unitario < 0:
            errors["precio_unitario"] = "El precio no puede ser negativo."
        if not 0 <= self.porcentaje_descuento <= 100:
            errors["porcentaje_descuento"] = "El descuento debe estar entre 0 y 100."
        if not 0 <= self.porcentaje_impuesto <= 100:
            errors["porcentaje_impuesto"] = "El impuesto debe estar entre 0 y 100."
        if errors:
            raise ValidationError(errors)


class HistorialEstadoPedido(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="historial_estados")
    estado_anterior = models.CharField(max_length=30, choices=Pedido.Estado.choices)
    estado_nuevo = models.CharField(max_length=30, choices=Pedido.Estado.choices)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

class ConfiguracionComercialEmpresa(models.Model):
    empresa=models.OneToOneField(Empresa,on_delete=models.CASCADE,related_name="configuracion_comercial");estado=models.CharField(max_length=15,choices=(("BORRADOR","Borrador"),("ACTIVA","Activa"),("INACTIVA","Inactiva")),default="BORRADOR");version=models.PositiveIntegerField(default=1);lista_para_vender=models.BooleanField(default=False);porcentaje_preparacion=models.DecimalField(max_digits=5,decimal_places=2,default=0)
    moneda_base=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT,null=True,blank=True);decimales_moneda=models.PositiveSmallIntegerField(default=2);modo_redondeo=models.CharField(max_length=20,default="ROUND_HALF_UP");permite_credito=models.BooleanField(default=False);dias_credito_default=models.PositiveIntegerField(default=0);limite_credito_default=models.DecimalField(max_digits=18,decimal_places=2,default=0);tasa_mora_porcentaje=models.DecimalField(max_digits=5,decimal_places=2,default=0);requiere_workflow_credito=models.BooleanField(default=True)
    descuento_maximo_sin_aprobacion=models.DecimalField(max_digits=5,decimal_places=2,default=0);requiere_aprobacion_cotizacion=models.BooleanField(default=False);permite_backorder=models.BooleanField(default=False);reserva_automatica=models.BooleanField(default=False);requiere_evidencia_entrega=models.BooleanField(default=False);permite_facturacion_parcial=models.BooleanField(default=False);requiere_ncf=models.BooleanField(default=False);permite_anticipos=models.BooleanField(default=False);permite_factoring=models.BooleanField(default=False);permite_devoluciones=models.BooleanField(default=True);calcula_comisiones=models.BooleanField(default=False);usa_rutas=models.BooleanField(default=False);usa_inabie=models.BooleanField(default=False)
    ultima_validacion=models.DateTimeField(null=True,blank=True);resultado_validacion=models.JSONField(default=dict,blank=True);creado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="+");actualizado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="+");fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:permissions=[("administrar_configuracion_comercial","Puede administrar configuración comercial"),("validar_configuracion_comercial","Puede validar preparación comercial"),("exportar_configuracion_comercial","Puede exportar configuración comercial"),("gestionar_inabie_comercial","Puede gestionar vertical INABIE")]
    def clean(self):
        e={}
        if self.moneda_base_id and self.moneda_base.empresa_id!=self.empresa_id:e["moneda_base"]="Pertenece a otra empresa."
        for f in ("tasa_mora_porcentaje","descuento_maximo_sin_aprobacion"):
            if not 0<=getattr(self,f)<=100:e[f]="Debe estar entre 0 y 100."
        if self.usa_inabie and not self.empresa.modulo_inabie:e["usa_inabie"]="El módulo INABIE no está habilitado."
        if e:raise ValidationError(e)
    def delete(self,*a,**k):raise ValidationError("La configuración no se elimina.")

class CatalogoComercialBase(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=150);descripcion=models.TextField(blank=True);activo=models.BooleanField(default=True);orden=models.PositiveIntegerField(default=0);fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:abstract=True;ordering=["orden","nombre"]
    def __str__(self):return f"{self.codigo} - {self.nombre}"
class CanalVenta(CatalogoComercialBase):
    class Meta(CatalogoComercialBase.Meta):constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_canal_emp_cod_uniq")]
class SegmentoCliente(CatalogoComercialBase):
    class Meta(CatalogoComercialBase.Meta):constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_seg_emp_cod_uniq")]
class ClasificacionCliente(CatalogoComercialBase):
    class Meta(CatalogoComercialBase.Meta):constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_clas_emp_cod_uniq")]
class TipoCliente(CatalogoComercialBase):
    class Meta(CatalogoComercialBase.Meta):constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_tipo_cli_emp_cod_uniq")]
class TipoEntrega(CatalogoComercialBase):
    class Meta(CatalogoComercialBase.Meta):constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_tipo_ent_emp_cod_uniq")]
class PrioridadComercial(CatalogoComercialBase):
    class Meta(CatalogoComercialBase.Meta):constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_prio_emp_cod_uniq")]
class MotivoComercial(CatalogoComercialBase):
    categoria=models.CharField(max_length=40,default="GENERAL")
    class Meta(CatalogoComercialBase.Meta):constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_mot_emp_cod_uniq")]
class ZonaComercial(CatalogoComercialBase):
    class Meta(CatalogoComercialBase.Meta):constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_zona_emp_cod_uniq")]
class RutaComercial(CatalogoComercialBase):
    zona=models.ForeignKey(ZonaComercial,on_delete=models.PROTECT,related_name="rutas");dias_visita=models.JSONField(default=list,blank=True)
    class Meta(CatalogoComercialBase.Meta):constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_ruta_emp_cod_uniq")]
    def clean(self):
        if self.zona_id and self.zona.empresa_id!=self.empresa_id:raise ValidationError("La zona pertenece a otra empresa.")
class EquipoComercial(CatalogoComercialBase):
    supervisor=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="equipos_comerciales_supervisados")
    class Meta(CatalogoComercialBase.Meta):constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_equipo_emp_cod_uniq")]
class VendedorComercial(CatalogoComercialBase):
    usuario=models.ForeignKey(User,on_delete=models.PROTECT,related_name="perfiles_vendedor");equipo=models.ForeignKey(EquipoComercial,on_delete=models.SET_NULL,null=True,blank=True,related_name="vendedores");zona=models.ForeignKey(ZonaComercial,on_delete=models.SET_NULL,null=True,blank=True);rutas=models.ManyToManyField(RutaComercial,blank=True);meta_mensual=models.DecimalField(max_digits=18,decimal_places=2,default=0)
    class Meta(CatalogoComercialBase.Meta):constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_vend_emp_cod_uniq"),models.UniqueConstraint(fields=["empresa","usuario"],name="com_vend_emp_usr_uniq")]

class PoliticaComercialBase(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=150);version=models.PositiveIntegerField(default=1);estado=models.CharField(max_length=12,choices=(("BORRADOR","Borrador"),("ACTIVA","Activa"),("INACTIVA","Inactiva")),default="BORRADOR");vigencia_desde=models.DateField();vigencia_hasta=models.DateField(null=True,blank=True);prioridad=models.PositiveIntegerField(default=100);ambito=models.JSONField(default=dict,blank=True);reglas=models.JSONField(default=dict,blank=True);creado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="+");fecha_creacion=models.DateTimeField(auto_now_add=True)
    class Meta:abstract=True;ordering=["prioridad","-version"]
    def clean(self):
        if self.vigencia_hasta and self.vigencia_hasta<self.vigencia_desde:raise ValidationError("Vigencia inválida.")
class PoliticaCredito(PoliticaComercialBase):pass
class PoliticaDescuento(PoliticaComercialBase):pass
class PoliticaEntrega(PoliticaComercialBase):pass
class PoliticaFacturacion(PoliticaComercialBase):pass
class PoliticaDevolucion(PoliticaComercialBase):pass
class PoliticaComision(PoliticaComercialBase):pass


class VersionPoliticaComercial(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="versiones_politicas_comerciales")
    tipo_politica = models.CharField(max_length=40)
    objeto_id = models.PositiveBigIntegerField()
    codigo = models.CharField(max_length=30)
    version = models.PositiveIntegerField()
    estado = models.CharField(max_length=12)
    vigencia_desde = models.DateField()
    vigencia_hasta = models.DateField(null=True, blank=True)
    prioridad = models.PositiveIntegerField()
    contenido = models.JSONField()
    hash_contenido = models.CharField(max_length=64)
    motivo = models.CharField(max_length=250)
    version_anterior = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tipo_politica", "codigo", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "tipo_politica", "codigo", "version"],
                name="com_verpol_emp_tipo_cod_ver_uniq",
            )
        ]
        permissions = [("versionar_politica_comercial", "Puede versionar políticas comerciales")]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Los snapshots de políticas son inmutables.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Los snapshots de políticas son inmutables.")


class FuenteProspecto(CatalogoComercialBase):
    class Meta(CatalogoComercialBase.Meta):
        constraints = [models.UniqueConstraint(fields=["empresa", "codigo"], name="crm_fuente_emp_cod_uniq")]


class Prospecto(models.Model):
    class Estado(models.TextChoices):
        NUEVO="NUEVO","Nuevo";CONTACTADO="CONTACTADO","Contactado";CALIFICADO="CALIFICADO","Calificado";NO_CALIFICADO="NO_CALIFICADO","No calificado";CONVERTIDO="CONVERTIDO","Convertido";DESCARTADO="DESCARTADO","Descartado"
    class TipoPersona(models.TextChoices):
        FISICA="FISICA","Persona física";JURIDICA="JURIDICA","Persona jurídica"
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE,related_name="prospectos");numero=models.CharField(max_length=30);tipo_persona=models.CharField(max_length=10,choices=TipoPersona.choices,default=TipoPersona.JURIDICA);nombre=models.CharField(max_length=180);nombre_comercial=models.CharField(max_length=180,blank=True);identificacion_fiscal=models.CharField(max_length=30,blank=True);contacto_principal=models.CharField(max_length=150,blank=True);telefono=models.CharField(max_length=50,blank=True);telefono_alterno=models.CharField(max_length=50,blank=True);correo=models.EmailField(blank=True);sitio_web=models.URLField(blank=True);direccion=models.TextField(blank=True);provincia=models.CharField(max_length=100,blank=True);municipio=models.CharField(max_length=100,blank=True);pais=models.CharField(max_length=80,default="República Dominicana")
    fuente=models.ForeignKey(FuenteProspecto,on_delete=models.PROTECT,null=True,blank=True);canal=models.ForeignKey(CanalVenta,on_delete=models.PROTECT,null=True,blank=True);segmento=models.ForeignKey(SegmentoCliente,on_delete=models.PROTECT,null=True,blank=True);clasificacion=models.ForeignKey(ClasificacionCliente,on_delete=models.PROTECT,null=True,blank=True);vendedor=models.ForeignKey(VendedorComercial,on_delete=models.PROTECT,null=True,blank=True,related_name="prospectos");equipo=models.ForeignKey(EquipoComercial,on_delete=models.PROTECT,null=True,blank=True);zona=models.ForeignKey(ZonaComercial,on_delete=models.PROTECT,null=True,blank=True);ruta=models.ForeignKey(RutaComercial,on_delete=models.PROTECT,null=True,blank=True);interes_principal=models.CharField(max_length=250,blank=True);productos_interes=models.ManyToManyField(ProductoInventario,blank=True,related_name="prospectos_interesados");presupuesto_estimado=models.DecimalField(max_digits=18,decimal_places=2,default=0);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT,null=True,blank=True);probabilidad_inicial=models.DecimalField(max_digits=5,decimal_places=2,default=0);fecha_primer_contacto=models.DateField(null=True,blank=True);fecha_proxima_accion=models.DateTimeField(null=True,blank=True);estado=models.CharField(max_length=15,choices=Estado.choices,default=Estado.NUEVO);motivo_no_calificacion=models.TextField(blank=True);motivo_descarte=models.TextField(blank=True);observaciones=models.TextField(blank=True);creado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="prospectos_creados");actualizado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="prospectos_actualizados");convertido_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="prospectos_convertidos");fecha_conversion=models.DateTimeField(null=True,blank=True);cliente_convertido=models.ForeignKey(Cliente,on_delete=models.PROTECT,null=True,blank=True,related_name="prospectos_origen");fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=["-fecha_creacion"];constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="crm_pros_emp_num_uniq"),models.CheckConstraint(condition=Q(presupuesto_estimado__gte=0),name="crm_pros_pres_no_neg"),models.CheckConstraint(condition=Q(probabilidad_inicial__gte=0,probabilidad_inicial__lte=100),name="crm_pros_prob_rango")];indexes=[models.Index(fields=["empresa","estado"],name="crm_pros_emp_est_idx"),models.Index(fields=["empresa","vendedor"],name="crm_pros_emp_vend_idx"),models.Index(fields=["empresa","fecha_proxima_accion"],name="crm_pros_emp_acc_idx")];permissions=[("calificar_prospecto","Puede calificar prospectos"),("descartar_prospecto","Puede descartar prospectos"),("convertir_prospecto","Puede convertir prospectos"),("reasignar_prospecto","Puede reasignar prospectos"),("exportar_prospecto","Puede exportar prospectos"),("administrar_prospecto","Puede administrar prospectos")]
    def clean(self):
        e={}
        for f in ("fuente","canal","segmento","clasificacion","vendedor","equipo","zona","ruta","moneda","cliente_convertido"):
            o=getattr(self,f,None)
            if o and getattr(o,"empresa_id",None)!=self.empresa_id:e[f]="El registro pertenece a otra empresa."
        if not 0<=self.probabilidad_inicial<=100:e["probabilidad_inicial"]="Debe estar entre 0 y 100."
        if e:raise ValidationError(e)
    def delete(self,*a,**k):raise ValidationError("Los prospectos no se eliminan físicamente.")
    def __str__(self):return f"{self.numero} - {self.nombre_comercial or self.nombre}"


class OportunidadComercial(models.Model):
    class Etapa(models.TextChoices):
        IDENTIFICADA="IDENTIFICADA","Identificada";CALIFICADA="CALIFICADA","Calificada";PROPUESTA="PROPUESTA","Propuesta";NEGOCIACION="NEGOCIACION","Negociación";GANADA="GANADA","Ganada";PERDIDA="PERDIDA","Perdida";CANCELADA="CANCELADA","Cancelada"
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE,related_name="oportunidades_comerciales");numero=models.CharField(max_length=30);prospecto=models.ForeignKey(Prospecto,on_delete=models.PROTECT,null=True,blank=True,related_name="oportunidades");cliente=models.ForeignKey(Cliente,on_delete=models.PROTECT,null=True,blank=True,related_name="oportunidades");titulo=models.CharField(max_length=200);descripcion=models.TextField(blank=True);vendedor=models.ForeignKey(VendedorComercial,on_delete=models.PROTECT,null=True,blank=True,related_name="oportunidades");equipo=models.ForeignKey(EquipoComercial,on_delete=models.PROTECT,null=True,blank=True);canal=models.ForeignKey(CanalVenta,on_delete=models.PROTECT,null=True,blank=True);segmento=models.ForeignKey(SegmentoCliente,on_delete=models.PROTECT,null=True,blank=True);zona=models.ForeignKey(ZonaComercial,on_delete=models.PROTECT,null=True,blank=True);ruta=models.ForeignKey(RutaComercial,on_delete=models.PROTECT,null=True,blank=True);etapa=models.CharField(max_length=15,choices=Etapa.choices,default=Etapa.IDENTIFICADA);monto_estimado=models.DecimalField(max_digits=18,decimal_places=2,default=0);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT,null=True,blank=True);probabilidad=models.DecimalField(max_digits=5,decimal_places=2,default=0);monto_ponderado=models.DecimalField(max_digits=18,decimal_places=2,default=0,editable=False);fecha_apertura=models.DateField();fecha_estimada_cierre=models.DateField(null=True,blank=True);fecha_cierre_real=models.DateField(null=True,blank=True);proxima_accion=models.CharField(max_length=250,blank=True);fecha_proxima_accion=models.DateTimeField(null=True,blank=True);competidor=models.CharField(max_length=180,blank=True);motivo_perdida=models.TextField(blank=True);motivo_cancelacion=models.TextField(blank=True);observaciones=models.TextField(blank=True);creado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="oportunidades_creadas");actualizado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="oportunidades_actualizadas");cerrado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="oportunidades_cerradas");fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=["-fecha_apertura","-id"];constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="crm_opo_emp_num_uniq"),models.CheckConstraint(condition=Q(prospecto__isnull=False)|Q(cliente__isnull=False),name="crm_opo_relacion_req"),models.CheckConstraint(condition=Q(monto_estimado__gte=0),name="crm_opo_monto_no_neg"),models.CheckConstraint(condition=Q(probabilidad__gte=0,probabilidad__lte=100),name="crm_opo_prob_rango")];indexes=[models.Index(fields=["empresa","etapa"],name="crm_opo_emp_etapa_idx"),models.Index(fields=["empresa","vendedor"],name="crm_opo_emp_vend_idx"),models.Index(fields=["empresa","fecha_estimada_cierre"],name="crm_opo_emp_cierre_idx")];permissions=[("cambiar_etapa_oportunidad","Puede cambiar etapa de oportunidad"),("ganar_oportunidad","Puede marcar oportunidades ganadas"),("perder_oportunidad","Puede marcar oportunidades perdidas"),("cancelar_oportunidad","Puede cancelar oportunidades"),("reasignar_oportunidad","Puede reasignar oportunidades"),("exportar_oportunidad","Puede exportar oportunidades"),("administrar_oportunidad","Puede administrar oportunidades")]
    def clean(self):
        e={}
        if not self.prospecto_id and not self.cliente_id:e["prospecto"]="Debe indicar un prospecto o cliente."
        for f in ("prospecto","cliente","vendedor","equipo","canal","segmento","zona","ruta","moneda"):
            o=getattr(self,f,None)
            if o and getattr(o,"empresa_id",None)!=self.empresa_id:e[f]="El registro pertenece a otra empresa."
        if not 0<=self.probabilidad<=100:e["probabilidad"]="Debe estar entre 0 y 100."
        if self.fecha_estimada_cierre and self.fecha_estimada_cierre<self.fecha_apertura:e["fecha_estimada_cierre"]="No puede ser anterior a la apertura."
        if e:raise ValidationError(e)
    def save(self,*a,**k):self.monto_ponderado=(self.monto_estimado or 0)*(self.probabilidad or 0)/Decimal("100");return super().save(*a,**k)
    def delete(self,*a,**k):raise ValidationError("Las oportunidades no se eliminan físicamente.")
    def __str__(self):return f"{self.numero} - {self.titulo}"


class ActividadComercial(models.Model):
    TIPOS=(("LLAMADA","Llamada"),("REUNION","Reunión"),("CORREO","Correo"),("VISITA","Visita"),("TAREA","Tarea"),("SEGUIMIENTO","Seguimiento"),("DEMOSTRACION","Demostración"),("PROPUESTA","Propuesta"),("OTRO","Otro"));ESTADOS=(("PENDIENTE","Pendiente"),("EN_PROGRESO","En progreso"),("COMPLETADA","Completada"),("CANCELADA","Cancelada"),("VENCIDA","Vencida"));PRIORIDADES=(("BAJA","Baja"),("NORMAL","Normal"),("ALTA","Alta"),("URGENTE","Urgente"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE,related_name="actividades_comerciales");prospecto=models.ForeignKey(Prospecto,on_delete=models.PROTECT,null=True,blank=True,related_name="actividades");cliente=models.ForeignKey(Cliente,on_delete=models.PROTECT,null=True,blank=True,related_name="actividades_crm");oportunidad=models.ForeignKey(OportunidadComercial,on_delete=models.PROTECT,null=True,blank=True,related_name="actividades");cotizacion_referencia=models.CharField(max_length=80,blank=True);tipo=models.CharField(max_length=20,choices=TIPOS);asunto=models.CharField(max_length=200);descripcion=models.TextField(blank=True);responsable=models.ForeignKey(User,on_delete=models.PROTECT,related_name="actividades_crm");fecha_inicio=models.DateTimeField();fecha_fin=models.DateTimeField(null=True,blank=True);todo_el_dia=models.BooleanField(default=False);recordatorio=models.BooleanField(default=False);fecha_recordatorio=models.DateTimeField(null=True,blank=True);prioridad=models.CharField(max_length=10,choices=PRIORIDADES,default="NORMAL");estado=models.CharField(max_length=15,choices=ESTADOS,default="PENDIENTE");resultado=models.TextField(blank=True);siguiente_accion=models.CharField(max_length=250,blank=True);fecha_siguiente_accion=models.DateTimeField(null=True,blank=True);ubicacion=models.CharField(max_length=250,blank=True);latitud=models.DecimalField(max_digits=10,decimal_places=7,null=True,blank=True);longitud=models.DecimalField(max_digits=10,decimal_places=7,null=True,blank=True);creado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="actividades_crm_creadas");actualizado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="actividades_crm_actualizadas");completado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="actividades_crm_completadas");fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=["fecha_inicio","id"];constraints=[models.CheckConstraint(condition=Q(prospecto__isnull=False)|Q(cliente__isnull=False)|Q(oportunidad__isnull=False),name="crm_act_relacion_req")];indexes=[models.Index(fields=["empresa","estado","fecha_inicio"],name="crm_act_emp_est_ini_idx"),models.Index(fields=["empresa","responsable"],name="crm_act_emp_resp_idx")];permissions=[("completar_actividad_comercial","Puede completar actividades"),("cancelar_actividad_comercial","Puede cancelar actividades"),("reprogramar_actividad_comercial","Puede reprogramar actividades"),("administrar_actividad_comercial","Puede administrar actividades")]
    def clean(self):
        e={}
        if not any((self.prospecto_id,self.cliente_id,self.oportunidad_id)):e["prospecto"]="Debe asociar una relación comercial."
        for f in ("prospecto","cliente","oportunidad"):
            o=getattr(self,f,None)
            if o and o.empresa_id!=self.empresa_id:e[f]="El registro pertenece a otra empresa."
        if self.responsable_id and self.empresa_id and not Empresa.objects.filter(pk=self.empresa_id,usuario=self.responsable).exists() and not VendedorComercial.objects.filter(empresa_id=self.empresa_id,usuario=self.responsable,activo=True).exists():e["responsable"]="El responsable no pertenece a la empresa."
        if self.fecha_fin and self.fecha_fin<self.fecha_inicio:e["fecha_fin"]="No puede ser anterior al inicio."
        if self.estado=="COMPLETADA" and not self.resultado.strip():e["resultado"]="El resultado es obligatorio."
        if e:raise ValidationError(e)
    def delete(self,*a,**k):raise ValidationError("Las actividades no se eliminan físicamente.")


class HistorialCRMBase(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);usuario=models.ForeignKey(User,on_delete=models.SET_NULL,null=True);comentario=models.TextField(blank=True);fecha=models.DateTimeField(auto_now_add=True)
    class Meta:abstract=True;ordering=["-fecha"]
    def save(self,*a,**k):
        if self.pk:raise ValidationError("El historial es inmutable.")
        return super().save(*a,**k)
    def delete(self,*a,**k):raise ValidationError("El historial es inmutable.")
class HistorialEstadoProspecto(HistorialCRMBase):
    prospecto=models.ForeignKey(Prospecto,on_delete=models.CASCADE,related_name="historial_estados");estado_anterior=models.CharField(max_length=15);estado_nuevo=models.CharField(max_length=15)
class HistorialEtapaOportunidad(HistorialCRMBase):
    oportunidad=models.ForeignKey(OportunidadComercial,on_delete=models.CASCADE,related_name="historial_etapas");etapa_anterior=models.CharField(max_length=15);etapa_nueva=models.CharField(max_length=15);dias_en_etapa=models.PositiveIntegerField(default=0)
class HistorialActividadComercial(HistorialCRMBase):
    actividad=models.ForeignKey(ActividadComercial,on_delete=models.CASCADE,related_name="historial");accion=models.CharField(max_length=30);estado_anterior=models.CharField(max_length=15,blank=True);estado_nuevo=models.CharField(max_length=15,blank=True);snapshot=models.JSONField(default=dict)


class ProductoComercial(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE,related_name="productos_comerciales");producto_inventario=models.OneToOneField(ProductoInventario,on_delete=models.PROTECT,related_name="producto_comercial");codigo=models.CharField(max_length=40);nombre=models.CharField(max_length=180);descripcion_venta=models.TextField(blank=True);marca=models.CharField(max_length=100,blank=True);categoria=models.CharField(max_length=100,blank=True);presentacion=models.CharField(max_length=100,blank=True);unidad_venta=models.CharField(max_length=30);factor_conversion=models.DecimalField(max_digits=14,decimal_places=4,default=1);venta_minima=models.DecimalField(max_digits=14,decimal_places=4,default=1);multiplo_venta=models.DecimalField(max_digits=14,decimal_places=4,default=1);permite_descuento=models.BooleanField(default=True);impuesto=models.ForeignKey("catalogos.Impuesto",on_delete=models.PROTECT,null=True,blank=True);precio_base=models.DecimalField(max_digits=18,decimal_places=4,default=0);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);imagen=models.ImageField(upload_to="comercial/productos/",blank=True);ficha=models.TextField(blank=True);canal=models.ForeignKey(CanalVenta,on_delete=models.PROTECT,null=True,blank=True);activo=models.BooleanField(default=True);disponible_venta=models.BooleanField(default=True);fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:ordering=["nombre"];constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_prodcom_emp_cod_uniq"),models.CheckConstraint(condition=Q(factor_conversion__gt=0,venta_minima__gt=0,multiplo_venta__gt=0),name="com_prodcom_factores_pos"),models.CheckConstraint(condition=Q(precio_base__gte=0),name="com_prodcom_precio_no_neg")];permissions=[("administrar_producto_comercial","Puede administrar productos comerciales"),("exportar_producto_comercial","Puede exportar productos comerciales")]
    def clean(self):
        e={}
        for f in ("producto_inventario","impuesto","moneda","canal"):
            o=getattr(self,f,None)
            if o and getattr(o,"empresa_id",None)!=self.empresa_id:e[f]="El registro pertenece a otra empresa."
        if e:raise ValidationError(e)
    def delete(self,*a,**k):raise ValidationError("El producto comercial no se elimina físicamente.")
    def __str__(self):return f"{self.codigo} - {self.nombre}"


class ListaPrecio(models.Model):
    ESTADOS=(("BORRADOR","Borrador"),("ACTIVA","Activa"),("VENCIDA","Vencida"),("INACTIVA","Inactiva"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE,related_name="listas_precio_comerciales");codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=150);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);cliente=models.ForeignKey(Cliente,on_delete=models.PROTECT,null=True,blank=True);segmento=models.ForeignKey(SegmentoCliente,on_delete=models.PROTECT,null=True,blank=True);canal=models.ForeignKey(CanalVenta,on_delete=models.PROTECT,null=True,blank=True);zona=models.ForeignKey(ZonaComercial,on_delete=models.PROTECT,null=True,blank=True);vigencia_desde=models.DateField();vigencia_hasta=models.DateField(null=True,blank=True);prioridad=models.PositiveIntegerField(default=100);version=models.PositiveIntegerField(default=1);estado=models.CharField(max_length=10,choices=ESTADOS,default="BORRADOR");predeterminada=models.BooleanField(default=False);version_anterior=models.ForeignKey("self",on_delete=models.PROTECT,null=True,blank=True);creado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="+");fecha_creacion=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=["prioridad","nombre"];constraints=[models.UniqueConstraint(fields=["empresa","codigo","version"],name="com_lista_emp_cod_ver_uniq")];indexes=[models.Index(fields=["empresa","estado","vigencia_desde"],name="com_lista_emp_est_vig_idx")];permissions=[("activar_lista_precio","Puede activar listas de precio"),("versionar_lista_precio","Puede versionar listas de precio"),("simular_precio_comercial","Puede simular precios"),("administrar_pricing","Puede administrar pricing")]
    def clean(self):
        e={}
        if self.vigencia_hasta and self.vigencia_hasta<self.vigencia_desde:e["vigencia_hasta"]="Vigencia inválida."
        for f in ("moneda","cliente","segmento","canal","zona"):
            o=getattr(self,f,None)
            if o and getattr(o,"empresa_id",None)!=self.empresa_id:e[f]="El registro pertenece a otra empresa."
        if e:raise ValidationError(e)
class DetalleListaPrecio(models.Model):
    lista=models.ForeignKey(ListaPrecio,on_delete=models.CASCADE,related_name="detalles");producto=models.ForeignKey(ProductoComercial,on_delete=models.PROTECT);presentacion=models.CharField(max_length=100,blank=True);cantidad_minima=models.DecimalField(max_digits=14,decimal_places=4,default=1);cantidad_maxima=models.DecimalField(max_digits=14,decimal_places=4,null=True,blank=True);precio=models.DecimalField(max_digits=18,decimal_places=4);fecha_creacion=models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["lista","producto","presentacion","cantidad_minima"],name="com_detlista_unico"),models.CheckConstraint(condition=Q(precio__gte=0,cantidad_minima__gt=0),name="com_detlista_valores_pos")]
class ReglaPrecio(models.Model):
    TIPOS=(("FIJO","Precio fijo"),("VOLUMEN","Precio por volumen"),("RECARGO","Recargo"),("DESCUENTO","Descuento"),("ESPECIAL","Precio especial"),("BONIFICACION","Bonificación futura"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=150);tipo=models.CharField(max_length=15,choices=TIPOS);prioridad=models.PositiveIntegerField(default=100);condiciones=models.JSONField(default=dict);accion=models.JSONField(default=dict);vigencia_desde=models.DateField();vigencia_hasta=models.DateField(null=True,blank=True);activa=models.BooleanField(default=True);fecha_creacion=models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_regprecio_emp_cod_uniq")];permissions=[("administrar_regla_precio","Puede administrar reglas de precio")]
class PoliticaDescuentoComercial(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);nombre=models.CharField(max_length=150);porcentaje_maximo=models.DecimalField(max_digits=5,decimal_places=2,default=0);requiere_aprobacion_desde=models.DecimalField(max_digits=5,decimal_places=2,default=0);activa=models.BooleanField(default=True);version=models.PositiveIntegerField(default=1);fecha_creacion=models.DateTimeField(auto_now_add=True)
class PromocionComercial(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=150);vigencia_desde=models.DateField();vigencia_hasta=models.DateField();prioridad=models.PositiveIntegerField(default=100);activa=models.BooleanField(default=True);fecha_creacion=models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="com_promo_emp_cod_uniq")];permissions=[("administrar_promocion_comercial","Puede administrar promociones")]
class ReglaPromocion(models.Model):
    promocion=models.ForeignKey(PromocionComercial,on_delete=models.CASCADE,related_name="reglas");producto=models.ForeignKey(ProductoComercial,on_delete=models.PROTECT,null=True,blank=True);cantidad_minima=models.DecimalField(max_digits=14,decimal_places=4,default=1);porcentaje_descuento=models.DecimalField(max_digits=5,decimal_places=2,default=0);precio_especial=models.DecimalField(max_digits=18,decimal_places=4,null=True,blank=True)


class CotizacionVenta(models.Model):
    ESTADOS=(("BORRADOR","Borrador"),("EN_REVISION","En revisión"),("APROBADA_INTERNA","Aprobada interna"),("ENVIADA","Enviada"),("ACEPTADA","Aceptada"),("RECHAZADA","Rechazada"),("VENCIDA","Vencida"),("CANCELADA","Cancelada"),("CONVERTIDA","Convertida"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE,related_name="cotizaciones_venta");numero=models.CharField(max_length=30);cliente=models.ForeignKey(Cliente,on_delete=models.PROTECT,related_name="cotizaciones");oportunidad=models.ForeignKey(OportunidadComercial,on_delete=models.PROTECT,null=True,blank=True,related_name="cotizaciones");version=models.PositiveIntegerField(default=1);estado=models.CharField(max_length=20,choices=ESTADOS,default="BORRADOR");fecha=models.DateField();valida_hasta=models.DateField();moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);condicion_pago=models.CharField(max_length=100,blank=True);dias_credito=models.PositiveIntegerField(default=0);subtotal=models.DecimalField(max_digits=18,decimal_places=2,default=0);descuento_total=models.DecimalField(max_digits=18,decimal_places=2,default=0);impuesto_total=models.DecimalField(max_digits=18,decimal_places=2,default=0);total=models.DecimalField(max_digits=18,decimal_places=2,default=0);observaciones=models.TextField(blank=True);creado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="cotizaciones_creadas");actualizado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="cotizaciones_actualizadas");aprobado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="cotizaciones_aprobadas");fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:ordering=["-fecha","-id"];constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="com_cot_emp_num_uniq")];indexes=[models.Index(fields=["empresa","estado"],name="com_cot_emp_estado_idx")];permissions=[("aprobar_cotizacion_venta","Puede aprobar cotizaciones"),("versionar_cotizacion_venta","Puede versionar cotizaciones"),("convertir_cotizacion_venta","Puede convertir cotizaciones"),("exportar_cotizacion_venta","Puede exportar cotizaciones"),("administrar_cotizacion_venta","Puede administrar cotizaciones")]
    def clean(self):
        e={}
        for f in ("cliente","oportunidad","moneda"):
            o=getattr(self,f,None)
            if o and getattr(o,"empresa_id",None)!=self.empresa_id:e[f]="El registro pertenece a otra empresa."
        if self.fecha and self.valida_hasta and self.valida_hasta<self.fecha:e["valida_hasta"]="La vigencia no puede terminar antes de la fecha."
        if e:raise ValidationError(e)
    def delete(self,*a,**k):raise ValidationError("Las cotizaciones no se eliminan físicamente.")
class DetalleCotizacionVenta(models.Model):
    cotizacion=models.ForeignKey(CotizacionVenta,on_delete=models.CASCADE,related_name="detalles");producto=models.ForeignKey(ProductoComercial,on_delete=models.PROTECT);descripcion=models.CharField(max_length=255);cantidad=models.DecimalField(max_digits=14,decimal_places=4);precio_unitario=models.DecimalField(max_digits=18,decimal_places=4);porcentaje_descuento=models.DecimalField(max_digits=5,decimal_places=2,default=0);porcentaje_impuesto=models.DecimalField(max_digits=5,decimal_places=2,default=0);subtotal=models.DecimalField(max_digits=18,decimal_places=2,default=0);descuento=models.DecimalField(max_digits=18,decimal_places=2,default=0);impuesto=models.DecimalField(max_digits=18,decimal_places=2,default=0);total=models.DecimalField(max_digits=18,decimal_places=2,default=0);snapshot=models.JSONField(default=dict);hash_precio=models.CharField(max_length=64,blank=True);orden=models.PositiveIntegerField(default=0)
    class Meta:ordering=["orden","id"];constraints=[models.CheckConstraint(condition=Q(cantidad__gt=0,precio_unitario__gte=0),name="com_detcot_valores_pos")]
    def clean(self):
        e={}
        if self.producto_id and self.cotizacion_id and self.producto.empresa_id!=self.cotizacion.empresa_id:e["producto"]="El producto pertenece a otra empresa."
        if self.cantidad is not None and self.cantidad<=0:e["cantidad"]="Debe ser mayor que cero."
        if self.porcentaje_descuento is not None and not 0<=self.porcentaje_descuento<=100:e["porcentaje_descuento"]="Debe estar entre 0 y 100."
        if e:raise ValidationError(e)
class VersionCotizacionVenta(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);cotizacion=models.ForeignKey(CotizacionVenta,on_delete=models.CASCADE,related_name="versiones");version=models.PositiveIntegerField();snapshot=models.JSONField();hash_contenido=models.CharField(max_length=64);motivo=models.CharField(max_length=250);creado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True);fecha=models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["cotizacion","version"],name="com_vercot_cot_ver_uniq")]
    def save(self,*a,**k):
        if self.pk:raise ValidationError("La versión es inmutable.")
        return super().save(*a,**k)
class HistorialCotizacionVenta(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE);cotizacion=models.ForeignKey(CotizacionVenta,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=20);estado_nuevo=models.CharField(max_length=20);usuario=models.ForeignKey(User,on_delete=models.SET_NULL,null=True);comentario=models.TextField(blank=True);fecha=models.DateTimeField(auto_now_add=True)
    class Meta:ordering=["-fecha"]
    def save(self,*a,**k):
        if self.pk:raise ValidationError("El historial es inmutable.")
        return super().save(*a,**k)


class ProgramacionPedido(models.Model):
    ESTADOS=(("PENDIENTE","Pendiente"),("PROGRAMADA","Programada"),("REPROGRAMADA","Reprogramada"),("CANCELADA","Cancelada"),("ENVIADA_A_PREPARACION","Enviada a preparación"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE,related_name="programaciones_comerciales");pedido=models.OneToOneField(Pedido,on_delete=models.PROTECT,related_name="programacion_comercial");fecha_programada=models.DateField();hora_desde=models.TimeField(null=True,blank=True);hora_hasta=models.TimeField(null=True,blank=True);ruta=models.ForeignKey(RutaComercial,on_delete=models.PROTECT,null=True,blank=True);zona=models.ForeignKey(ZonaComercial,on_delete=models.PROTECT,null=True,blank=True);vendedor=models.ForeignKey(VendedorComercial,on_delete=models.PROTECT,null=True,blank=True);estado=models.CharField(max_length=25,choices=ESTADOS,default="PENDIENTE");motivo=models.TextField(blank=True);creado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="+");actualizado_por=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name="+");fecha_creacion=models.DateTimeField(auto_now_add=True);fecha_actualizacion=models.DateTimeField(auto_now=True)
    class Meta:ordering=["fecha_programada","pedido__numero"];indexes=[models.Index(fields=["empresa","fecha_programada","estado"],name="com_prog_emp_fecha_est_idx")];permissions=[("programar_pedido_comercial","Puede programar pedidos"),("reprogramar_pedido_comercial","Puede reprogramar pedidos")]
    def clean(self):
        e={}
        for f in ("pedido","ruta","zona","vendedor"):
            o=getattr(self,f,None)
            if o and getattr(o,"empresa_id",None)!=self.empresa_id:e[f]="El registro pertenece a otra empresa."
        if self.hora_desde and self.hora_hasta and self.hora_hasta<=self.hora_desde:e["hora_hasta"]="Debe ser posterior a la hora inicial."
        if e:raise ValidationError(e)

# Los agregados del ciclo logístico/financiero se mantienen en un módulo
# aislado para facilitar la coexistencia con Conduce y Factura legacy.
from .models_o2c4 import *  # noqa: E402,F401,F403
