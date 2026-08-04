from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

class O2CBase(models.Model):
    empresa=models.ForeignKey("conduces.Empresa",on_delete=models.CASCADE);creado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+");creado_en=models.DateTimeField(auto_now_add=True);actualizado_en=models.DateTimeField(auto_now=True)
    class Meta:abstract=True
    def validar_tenant(self,*campos):
        e={}
        for f in campos:
            o=getattr(self,f,None)
            if o and getattr(o,"empresa_id",None)!=self.empresa_id:e[f]="El registro pertenece a otra empresa."
        if e:raise ValidationError(e)

class ReservaComercial(O2CBase):
    ESTADOS=[(x,x.replace("_"," ").title()) for x in ("BORRADOR","PENDIENTE","PARCIAL","COMPLETA","LIBERADA","EXPIRADA","CANCELADA","CONSUMIDA")]
    numero=models.CharField(max_length=30);pedido=models.OneToOneField("comercial.Pedido",on_delete=models.PROTECT,related_name="reserva_comercial");estado=models.CharField(max_length=12,choices=ESTADOS,default="BORRADOR");expira_en=models.DateTimeField(null=True,blank=True);motivo=models.TextField(blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="o2c_res_emp_num_uniq")];permissions=[("gestionar_reserva_comercial","Puede gestionar reservas comerciales")]
    def clean(self):self.validar_tenant("pedido")
class DetalleReservaComercial(models.Model):
    reserva=models.ForeignKey(ReservaComercial,on_delete=models.CASCADE,related_name="detalles");detalle_pedido=models.ForeignKey("comercial.DetallePedido",on_delete=models.PROTECT);producto=models.ForeignKey("inventario.ProductoInventario",on_delete=models.PROTECT);lote=models.ForeignKey("inventario.LoteInventario",on_delete=models.PROTECT,null=True,blank=True);cantidad_solicitada=models.DecimalField(max_digits=14,decimal_places=4);cantidad_reservada=models.DecimalField(max_digits=14,decimal_places=4,default=0);cantidad_consumida=models.DecimalField(max_digits=14,decimal_places=4,default=0)
    class Meta:constraints=[models.CheckConstraint(condition=Q(cantidad_solicitada__gt=0,cantidad_reservada__gte=0,cantidad_consumida__gte=0),name="o2c_detres_cant_pos")]
class HistorialReservaComercial(models.Model):
    reserva=models.ForeignKey(ReservaComercial,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=15);estado_nuevo=models.CharField(max_length=15);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);comentario=models.TextField(blank=True);fecha=models.DateTimeField(auto_now_add=True)

class PreparacionPedido(O2CBase):
    ESTADOS=[(x,x.replace("_"," ").title()) for x in ("PENDIENTE","EN_PROCESO","PREPARADA","VALIDADA","CANCELADA")]
    numero=models.CharField(max_length=30);pedido=models.OneToOneField("comercial.Pedido",on_delete=models.PROTECT,related_name="preparacion_o2c");reserva=models.OneToOneField(ReservaComercial,on_delete=models.PROTECT);estado=models.CharField(max_length=15,choices=ESTADOS,default="PENDIENTE");operador=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="preparaciones_o2c")
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="o2c_prep_emp_num_uniq")];permissions=[("gestionar_preparacion_o2c","Puede gestionar preparación O2C")]
class DetallePreparacionPedido(models.Model):
    preparacion=models.ForeignKey(PreparacionPedido,on_delete=models.CASCADE,related_name="detalles");detalle_reserva=models.OneToOneField(DetalleReservaComercial,on_delete=models.PROTECT);cantidad_preparada=models.DecimalField(max_digits=14,decimal_places=4,default=0);diferencia=models.DecimalField(max_digits=14,decimal_places=4,default=0)
class HistorialPreparacionPedido(models.Model):
    preparacion=models.ForeignKey(PreparacionPedido,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=15);estado_nuevo=models.CharField(max_length=15);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);fecha=models.DateTimeField(auto_now_add=True)
class TareaPicking(O2CBase):
    ESTADOS=[(x,x.replace("_"," ").title()) for x in ("PENDIENTE","ASIGNADA","EN_PROCESO","COMPLETADA","VALIDADA","CANCELADA")]
    preparacion=models.OneToOneField(PreparacionPedido,on_delete=models.PROTECT,related_name="picking");estado=models.CharField(max_length=15,choices=ESTADOS,default="PENDIENTE");operador=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="pickings_o2c")
    class Meta:permissions=[("gestionar_picking_o2c","Puede gestionar picking O2C")]
class DetallePicking(models.Model):
    picking=models.ForeignKey(TareaPicking,on_delete=models.CASCADE,related_name="detalles");detalle_preparacion=models.OneToOneField(DetallePreparacionPedido,on_delete=models.PROTECT);lote=models.ForeignKey("inventario.LoteInventario",on_delete=models.PROTECT,null=True,blank=True);cantidad=models.DecimalField(max_digits=14,decimal_places=4,default=0);diferencia=models.DecimalField(max_digits=14,decimal_places=4,default=0)
class PackingPedido(O2CBase):
    ESTADOS=[(x,x.replace("_"," ").title()) for x in ("PENDIENTE","EN_PROCESO","EMPACADO","SELLADO","CANCELADO")]
    pedido=models.OneToOneField("comercial.Pedido",on_delete=models.PROTECT,related_name="packing_o2c");picking=models.OneToOneField(TareaPicking,on_delete=models.PROTECT);estado=models.CharField(max_length=15,choices=ESTADOS,default="PENDIENTE");bultos=models.PositiveIntegerField(default=0);peso_total=models.DecimalField(max_digits=14,decimal_places=4,default=0)
    class Meta:permissions=[("gestionar_packing_o2c","Puede gestionar packing O2C")]
class PaquetePedido(models.Model):
    packing=models.ForeignKey(PackingPedido,on_delete=models.CASCADE,related_name="paquetes");codigo=models.CharField(max_length=50);peso=models.DecimalField(max_digits=14,decimal_places=4,default=0);volumen=models.DecimalField(max_digits=14,decimal_places=4,default=0);sellado=models.BooleanField(default=False)
    class Meta:constraints=[models.UniqueConstraint(fields=["packing","codigo"],name="o2c_paquete_codigo_uniq")]
class DetallePaquetePedido(models.Model):
    paquete=models.ForeignKey(PaquetePedido,on_delete=models.CASCADE,related_name="detalles");detalle_picking=models.ForeignKey(DetallePicking,on_delete=models.PROTECT);cantidad=models.DecimalField(max_digits=14,decimal_places=4)

class DespachoComercial(O2CBase):
    ESTADOS=[(x,x.replace("_"," ").title()) for x in ("BORRADOR","PREPARANDO","LISTO","DESPACHADO","EN_RUTA","PARCIALMENTE_ENTREGADO","COMPLETADO","CANCELADO")]
    numero=models.CharField(max_length=30);fecha=models.DateField();estado=models.CharField(max_length=25,choices=ESTADOS,default="BORRADOR");ruta=models.ForeignKey("comercial.RutaComercial",on_delete=models.PROTECT,null=True,blank=True);chofer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="despachos_o2c");vehiculo=models.CharField(max_length=80,blank=True);pedidos=models.ManyToManyField("comercial.Pedido",through="DetalleDespachoComercial")
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="o2c_des_emp_num_uniq")];permissions=[("gestionar_despacho_o2c","Puede gestionar despachos O2C"),("autorizar_salida_o2c","Puede autorizar salida O2C")]
class DetalleDespachoComercial(models.Model):
    despacho=models.ForeignKey(DespachoComercial,on_delete=models.CASCADE,related_name="detalles");pedido=models.OneToOneField("comercial.Pedido",on_delete=models.PROTECT);packing=models.OneToOneField(PackingPedido,on_delete=models.PROTECT)
class HistorialDespachoComercial(models.Model):
    despacho=models.ForeignKey(DespachoComercial,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=25);estado_nuevo=models.CharField(max_length=25);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);fecha=models.DateTimeField(auto_now_add=True)
class ChecklistDespacho(models.Model):
    despacho=models.ForeignKey(DespachoComercial,on_delete=models.CASCADE,related_name="checklist");item=models.CharField(max_length=150);completado=models.BooleanField(default=False);verificado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)

class ConduceComercial(O2CBase):
    ESTADOS=[(x,x.replace("_"," ").title()) for x in ("BORRADOR","EMITIDO","EN_RUTA","ENTREGADO_PARCIAL","ENTREGADO","RECHAZADO","DEVUELTO","ANULADO")]
    numero=models.CharField(max_length=30);despacho=models.OneToOneField(DespachoComercial,on_delete=models.PROTECT,related_name="conduce");estado=models.CharField(max_length=20,choices=ESTADOS,default="BORRADOR");legacy_id=models.PositiveBigIntegerField(null=True,blank=True);emitido_en=models.DateTimeField(null=True,blank=True);qr_token=models.CharField(max_length=64,blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="o2c_cond_emp_num_uniq")];permissions=[("emitir_conduce_o2c","Puede emitir conduces O2C"),("anular_conduce_o2c","Puede anular conduces O2C")]
class DetalleConduceComercial(models.Model):
    conduce=models.ForeignKey(ConduceComercial,on_delete=models.CASCADE,related_name="detalles");detalle_pedido=models.ForeignKey("comercial.DetallePedido",on_delete=models.PROTECT);descripcion=models.CharField(max_length=255);cantidad=models.DecimalField(max_digits=14,decimal_places=4);unidad=models.CharField(max_length=30)
class HistorialConduceComercial(models.Model):
    conduce=models.ForeignKey(ConduceComercial,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=20);estado_nuevo=models.CharField(max_length=20);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);fecha=models.DateTimeField(auto_now_add=True)

class EntregaComercial(O2CBase):
    ESTADOS=[(x,x.replace("_"," ").title()) for x in ("PENDIENTE","EN_RUTA","EN_SITIO","ENTREGADA_PARCIAL","ENTREGADA","RECHAZADA","DEVUELTA","CANCELADA")]
    numero=models.CharField(max_length=30);conduce=models.OneToOneField(ConduceComercial,on_delete=models.PROTECT,related_name="entrega");estado=models.CharField(max_length=20,choices=ESTADOS,default="PENDIENTE");receptor=models.CharField(max_length=180,blank=True);documento_receptor=models.CharField(max_length=50,blank=True);latitud=models.DecimalField(max_digits=10,decimal_places=7,null=True,blank=True);longitud=models.DecimalField(max_digits=10,decimal_places=7,null=True,blank=True);confirmada_en=models.DateTimeField(null=True,blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="o2c_ent_emp_num_uniq")];permissions=[("gestionar_entrega_o2c","Puede gestionar entregas O2C"),("reabrir_entrega_o2c","Puede reabrir entregas O2C")]
class DetalleEntregaComercial(models.Model):
    entrega=models.ForeignKey(EntregaComercial,on_delete=models.CASCADE,related_name="detalles");detalle_conduce=models.OneToOneField(DetalleConduceComercial,on_delete=models.PROTECT);cantidad_entregada=models.DecimalField(max_digits=14,decimal_places=4,default=0);cantidad_rechazada=models.DecimalField(max_digits=14,decimal_places=4,default=0)
class EvidenciaEntrega(models.Model):
    entrega=models.ForeignKey(EntregaComercial,on_delete=models.CASCADE,related_name="evidencias");tipo=models.CharField(max_length=20,choices=[("FIRMA","Firma"),("FOTO","Foto"),("DOCUMENTO","Documento")]);archivo=models.FileField(upload_to="comercial/entregas/");hash_archivo=models.CharField(max_length=64);creado_en=models.DateTimeField(auto_now_add=True)
class IncidenciaEntrega(models.Model):
    entrega=models.ForeignKey(EntregaComercial,on_delete=models.CASCADE,related_name="incidencias");tipo=models.CharField(max_length=30);descripcion=models.TextField();resuelta=models.BooleanField(default=False);creado_en=models.DateTimeField(auto_now_add=True)
class HistorialEntregaComercial(models.Model):
    entrega=models.ForeignKey(EntregaComercial,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=20);estado_nuevo=models.CharField(max_length=20);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);fecha=models.DateTimeField(auto_now_add=True)

class FacturaVenta(O2CBase):
    ESTADOS=[(x,x.replace("_"," ").title()) for x in ("BORRADOR","EMITIDA","PARCIALMENTE_COBRADA","COBRADA","VENCIDA","CEDIDA_FACTORING","ANULADA","NOTA_CREDITO_PARCIAL","NOTA_CREDITO_TOTAL")]
    numero=models.CharField(max_length=30);cliente=models.ForeignKey("comercial.Cliente",on_delete=models.PROTECT,related_name="facturas_venta");pedido=models.ForeignKey("comercial.Pedido",on_delete=models.PROTECT,null=True,blank=True,related_name="facturas_venta");entrega=models.ForeignKey(EntregaComercial,on_delete=models.PROTECT,null=True,blank=True,related_name="facturas");moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);tasa_cambio=models.DecimalField(max_digits=18,decimal_places=6,default=1);dimensiones=models.JSONField(default=dict,blank=True);fecha=models.DateField();vence_el=models.DateField();ncf=models.CharField(max_length=30,blank=True);estado=models.CharField(max_length=25,choices=ESTADOS,default="BORRADOR");subtotal=models.DecimalField(max_digits=18,decimal_places=2,default=0);descuento=models.DecimalField(max_digits=18,decimal_places=2,default=0);impuesto=models.DecimalField(max_digits=18,decimal_places=2,default=0);total=models.DecimalField(max_digits=18,decimal_places=2,default=0);legacy_id=models.PositiveBigIntegerField(null=True,blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="o2c_fac_emp_num_uniq"),models.UniqueConstraint(fields=["empresa","ncf"],condition=~Q(ncf=""),name="o2c_fac_emp_ncf_uniq")];permissions=[("emitir_factura_venta","Puede emitir facturas de venta"),("anular_factura_venta","Puede anular facturas de venta")]
class DetalleFacturaVenta(models.Model):
    factura=models.ForeignKey(FacturaVenta,on_delete=models.CASCADE,related_name="detalles");detalle_pedido=models.ForeignKey("comercial.DetallePedido",on_delete=models.PROTECT,null=True,blank=True);descripcion=models.CharField(max_length=255);cantidad=models.DecimalField(max_digits=14,decimal_places=4);precio=models.DecimalField(max_digits=18,decimal_places=4);descuento=models.DecimalField(max_digits=18,decimal_places=2,default=0);impuesto=models.DecimalField(max_digits=18,decimal_places=2,default=0);total=models.DecimalField(max_digits=18,decimal_places=2);snapshot=models.JSONField(default=dict)
class HistorialFacturaVenta(models.Model):
    factura=models.ForeignKey(FacturaVenta,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=25);estado_nuevo=models.CharField(max_length=25);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);fecha=models.DateTimeField(auto_now_add=True)
class VersionFacturaVenta(models.Model):
    factura=models.ForeignKey(FacturaVenta,on_delete=models.CASCADE,related_name="versiones");version=models.PositiveIntegerField();snapshot=models.JSONField();hash_contenido=models.CharField(max_length=64);fecha=models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["factura","version"],name="o2c_verfac_uniq")]

class NotaVentaBase(O2CBase):
    numero=models.CharField(max_length=30);factura=models.ForeignKey(FacturaVenta,on_delete=models.PROTECT);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT,null=True,blank=True);tasa_cambio=models.DecimalField(max_digits=18,decimal_places=6,default=1);dimensiones=models.JSONField(default=dict,blank=True);motivo=models.TextField();ncf=models.CharField(max_length=30,blank=True);estado=models.CharField(max_length=15,choices=[("BORRADOR","Borrador"),("APROBADA","Aprobada"),("EMITIDA","Emitida"),("ANULADA","Anulada")],default="BORRADOR");total=models.DecimalField(max_digits=18,decimal_places=2,default=0)
    class Meta:abstract=True
class NotaCreditoVenta(NotaVentaBase):pass
class DetalleNotaCreditoVenta(models.Model):
    nota=models.ForeignKey(NotaCreditoVenta,on_delete=models.CASCADE,related_name="detalles");descripcion=models.CharField(max_length=255);cantidad=models.DecimalField(max_digits=14,decimal_places=4);monto=models.DecimalField(max_digits=18,decimal_places=2)
class NotaDebitoVenta(NotaVentaBase):pass
class DetalleNotaDebitoVenta(models.Model):
    nota=models.ForeignKey(NotaDebitoVenta,on_delete=models.CASCADE,related_name="detalles");descripcion=models.CharField(max_length=255);cantidad=models.DecimalField(max_digits=14,decimal_places=4);monto=models.DecimalField(max_digits=18,decimal_places=2)

class CuentaPorCobrar(O2CBase):
    ESTADOS=[(x,x.replace("_"," ").title()) for x in ("PENDIENTE","PARCIAL","COBRADA","VENCIDA","EN_MORA","CEDIDA_FACTORING","EN_DISPUTA","CANCELADA")]
    factura=models.OneToOneField(FacturaVenta,on_delete=models.PROTECT,related_name="cuenta_cobrar");cliente=models.ForeignKey("comercial.Cliente",on_delete=models.PROTECT,related_name="cuentas_cobrar");moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);fecha_emision=models.DateField();fecha_vencimiento=models.DateField();monto_original=models.DecimalField(max_digits=18,decimal_places=2);saldo=models.DecimalField(max_digits=18,decimal_places=2);estado=models.CharField(max_length=20,choices=ESTADOS,default="PENDIENTE");bucket_aging=models.CharField(max_length=12,default="CORRIENTE")
    class Meta:permissions=[("gestionar_cxc","Puede gestionar cuentas por cobrar"),("exportar_cxc","Puede exportar CxC")]
class MovimientoCxC(models.Model):
    cuenta=models.ForeignKey(CuentaPorCobrar,on_delete=models.CASCADE,related_name="movimientos");tipo=models.CharField(max_length=20,choices=[("CARGO","Cargo"),("COBRO","Cobro"),("NOTA_CREDITO","Nota crédito"),("NOTA_DEBITO","Nota débito"),("REVERSO","Reverso")]);monto=models.DecimalField(max_digits=18,decimal_places=2);saldo_anterior=models.DecimalField(max_digits=18,decimal_places=2);saldo_posterior=models.DecimalField(max_digits=18,decimal_places=2);referencia=models.CharField(max_length=80);fecha=models.DateTimeField(auto_now_add=True)
class CuotaCxC(models.Model):
    cuenta=models.ForeignKey(CuentaPorCobrar,on_delete=models.CASCADE,related_name="cuotas");numero=models.PositiveIntegerField();vence_el=models.DateField();monto=models.DecimalField(max_digits=18,decimal_places=2);saldo=models.DecimalField(max_digits=18,decimal_places=2)
class PromesaPago(models.Model):
    cuenta=models.ForeignKey(CuentaPorCobrar,on_delete=models.CASCADE,related_name="promesas");fecha_prometida=models.DateField();monto=models.DecimalField(max_digits=18,decimal_places=2);estado=models.CharField(max_length=12,choices=[("PENDIENTE","Pendiente"),("CUMPLIDA","Cumplida"),("INCUMPLIDA","Incumplida")],default="PENDIENTE");observaciones=models.TextField(blank=True)
class HistorialCxC(models.Model):
    cuenta=models.ForeignKey(CuentaPorCobrar,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=20);estado_nuevo=models.CharField(max_length=20);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);fecha=models.DateTimeField(auto_now_add=True)

class ReciboCobro(O2CBase):
    METODOS=[(x,x.title()) for x in ("EFECTIVO","TRANSFERENCIA","CHEQUE","TARJETA","DEPOSITO","RETENCION","COMPENSACION","FACTORING","OTRO")];ESTADOS=[(x,x.replace("_"," ").title()) for x in ("BORRADOR","REGISTRADO","PARCIALMENTE_APLICADO","APLICADO","ANULADO","REVERTIDO")]
    numero=models.CharField(max_length=30);cliente=models.ForeignKey("comercial.Cliente",on_delete=models.PROTECT,related_name="recibos_cobro");moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);tasa_cambio=models.DecimalField(max_digits=18,decimal_places=6,default=1);dimensiones=models.JSONField(default=dict,blank=True);fecha=models.DateField();metodo=models.CharField(max_length=20,choices=METODOS);monto=models.DecimalField(max_digits=18,decimal_places=2);monto_aplicado=models.DecimalField(max_digits=18,decimal_places=2,default=0);referencia=models.CharField(max_length=100,blank=True);estado=models.CharField(max_length=25,choices=ESTADOS,default="BORRADOR")
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="o2c_rec_emp_num_uniq")];permissions=[("registrar_cobro","Puede registrar cobros"),("revertir_cobro","Puede revertir cobros")]
class AplicacionCobro(models.Model):
    recibo=models.ForeignKey(ReciboCobro,on_delete=models.PROTECT,related_name="aplicaciones");cuenta=models.ForeignKey(CuentaPorCobrar,on_delete=models.PROTECT,related_name="aplicaciones");monto=models.DecimalField(max_digits=18,decimal_places=2);monto_moneda_cobro=models.DecimalField(max_digits=18,decimal_places=2,default=0);tasa_factura=models.DecimalField(max_digits=18,decimal_places=6,default=1);tasa_cobro=models.DecimalField(max_digits=18,decimal_places=6,default=1);diferencia_cambiaria=models.DecimalField(max_digits=18,decimal_places=2,default=0);revertida=models.BooleanField(default=False);fecha=models.DateTimeField(auto_now_add=True)
    class Meta:constraints=[models.CheckConstraint(condition=Q(monto__gt=0),name="o2c_aplic_monto_pos")]
class HistorialCobro(models.Model):
    recibo=models.ForeignKey(ReciboCobro,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=25);estado_nuevo=models.CharField(max_length=25);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);fecha=models.DateTimeField(auto_now_add=True)

class CesionFactoring(O2CBase):
    ESTADOS=[(x,x.title()) for x in ("BORRADOR","SOLICITADA","APROBADA","CEDIDA","PAGADA","RECHAZADA","CANCELADA")]
    numero=models.CharField(max_length=30);cuenta=models.OneToOneField(CuentaPorCobrar,on_delete=models.PROTECT,related_name="cesion_factoring");factor=models.CharField(max_length=180);porcentaje_anticipo=models.DecimalField(max_digits=5,decimal_places=2);monto_cedido=models.DecimalField(max_digits=18,decimal_places=2);estado=models.CharField(max_length=12,choices=ESTADOS,default="BORRADOR")
    comision=models.DecimalField(max_digits=18,decimal_places=2,default=0);costo_financiero=models.DecimalField(max_digits=18,decimal_places=2,default=0);retencion=models.DecimalField(max_digits=18,decimal_places=2,default=0);neto_recibido=models.DecimalField(max_digits=18,decimal_places=2,default=0);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT,null=True,blank=True);tasa_cambio=models.DecimalField(max_digits=18,decimal_places=6,default=1);dimensiones=models.JSONField(default=dict,blank=True);vence_el=models.DateField(null=True,blank=True);desembolsado_en=models.DateTimeField(null=True,blank=True);referencia_desembolso=models.CharField(max_length=100,blank=True)
    class Meta:permissions=[("gestionar_factoring_o2c","Puede gestionar factoring O2C")]
class MovimientoFactoring(models.Model):
    cesion=models.ForeignKey(CesionFactoring,on_delete=models.CASCADE,related_name="movimientos");tipo=models.CharField(max_length=20);monto=models.DecimalField(max_digits=18,decimal_places=2);fecha=models.DateTimeField(auto_now_add=True)
class HistorialFactoring(models.Model):
    cesion=models.ForeignKey(CesionFactoring,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=12);estado_nuevo=models.CharField(max_length=12);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);fecha=models.DateTimeField(auto_now_add=True)
