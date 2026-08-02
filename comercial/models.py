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
        ]
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

    def __str__(self):
        return f"{self.codigo} - {self.nombre_comercial}"


class DireccionCliente(models.Model):
    class Tipo(models.TextChoices):
        FISCAL = "FISCAL", "Fiscal"
        ENTREGA = "ENTREGA", "Entrega"
        COBRO = "COBRO", "Cobro"
        OTRO = "OTRO", "Otro"

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

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="pedidos")
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
