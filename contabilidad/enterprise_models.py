from django.conf import settings
from django.db import models
from django.db.models import Q

class EmpresaBase(models.Model):
    empresa=models.ForeignKey("conduces.Empresa",on_delete=models.CASCADE);creado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+");creado_en=models.DateTimeField(auto_now_add=True)
    class Meta:abstract=True
class PlanCuenta(EmpresaBase):
    codigo=models.CharField(max_length=20);nombre=models.CharField(max_length=150);version=models.PositiveIntegerField(default=1);activo=models.BooleanField(default=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","codigo","version"],name="fin_plan_emp_cod_ver_uniq")]
class CuentaContable(EmpresaBase):
    TIPOS=[(x,x.title()) for x in ("ACTIVO","PASIVO","PATRIMONIO","INGRESO","COSTO","GASTO","ORDEN")]
    plan=models.ForeignKey(PlanCuenta,on_delete=models.PROTECT,related_name="cuentas");padre=models.ForeignKey("self",on_delete=models.PROTECT,null=True,blank=True,related_name="hijas");codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=180);tipo=models.CharField(max_length=12,choices=TIPOS);naturaleza=models.CharField(max_length=7,choices=[("DEBITO","Débito"),("CREDITO","Crédito")]);acepta_movimientos=models.BooleanField(default=True);es_control=models.BooleanField(default=False);requiere_centro_costo=models.BooleanField(default=False);requiere_proyecto=models.BooleanField(default=False);activa=models.BooleanField(default=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","plan","codigo"],name="fin_cuenta_emp_plan_cod_uniq")]
class PeriodoContable(EmpresaBase):
    anio=models.PositiveIntegerField();mes=models.PositiveSmallIntegerField();fecha_inicio=models.DateField();fecha_fin=models.DateField();estado=models.CharField(max_length=10,choices=[("ABIERTO","Abierto"),("CERRADO","Cerrado")],default="ABIERTO")
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","anio","mes"],name="fin_periodo_emp_anio_mes_uniq")]
class DiarioContable(EmpresaBase):
    codigo=models.CharField(max_length=20);nombre=models.CharField(max_length=120);tipo=models.CharField(max_length=20,default="GENERAL");activo=models.BooleanField(default=True)
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="fin_diario_emp_cod_uniq")]
class LoteContable(EmpresaBase):
    numero=models.CharField(max_length=30);origen=models.CharField(max_length=40);estado=models.CharField(max_length=15,default="BORRADOR")
class AsientoContable(EmpresaBase):
    numero=models.CharField(max_length=30);periodo=models.ForeignKey(PeriodoContable,on_delete=models.PROTECT);diario=models.ForeignKey(DiarioContable,on_delete=models.PROTECT);lote=models.ForeignKey(LoteContable,on_delete=models.PROTECT,null=True,blank=True);fecha=models.DateField();concepto=models.CharField(max_length=255);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT,null=True,blank=True);tasa_cambio=models.DecimalField(max_digits=18,decimal_places=6,default=1);estado=models.CharField(max_length=15,choices=[("BORRADOR","Borrador"),("CONTABILIZADO","Contabilizado"),("REVERSADO","Reversado")],default="BORRADOR");origen_tipo=models.CharField(max_length=50,blank=True);origen_id=models.CharField(max_length=50,blank=True);clave_idempotencia=models.CharField(max_length=180,unique=True);total_debito=models.DecimalField(max_digits=18,decimal_places=2,default=0);total_credito=models.DecimalField(max_digits=18,decimal_places=2,default=0)
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","numero"],name="fin_asiento_emp_num_uniq")];permissions=[("contabilizar_asiento","Puede contabilizar asientos"),("cerrar_periodo_contable","Puede cerrar períodos")]
class DimensionContable(EmpresaBase):
    codigo=models.CharField(max_length=20);nombre=models.CharField(max_length=100);activa=models.BooleanField(default=True)
class ValorDimensionContable(EmpresaBase):
    dimension=models.ForeignKey(DimensionContable,on_delete=models.CASCADE,related_name="valores");codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=150);activo=models.BooleanField(default=True)
class LineaAsientoContable(models.Model):
    asiento=models.ForeignKey(AsientoContable,on_delete=models.CASCADE,related_name="lineas");cuenta=models.ForeignKey(CuentaContable,on_delete=models.PROTECT);descripcion=models.CharField(max_length=255,blank=True);debito=models.DecimalField(max_digits=18,decimal_places=2,default=0);credito=models.DecimalField(max_digits=18,decimal_places=2,default=0);dimensiones=models.JSONField(default=dict,blank=True)
    class Meta:constraints=[models.CheckConstraint(condition=(Q(debito__gt=0,credito=0)|Q(credito__gt=0,debito=0)),name="fin_linea_un_lado")]
class PlantillaAsiento(EmpresaBase):
    codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=150);lineas=models.JSONField(default=list);activa=models.BooleanField(default=True)
class ReglaContabilizacion(EmpresaBase):
    evento=models.CharField(max_length=60);version=models.PositiveIntegerField(default=1);configuracion=models.JSONField(default=dict);activa=models.BooleanField(default=True)
class CierreContable(EmpresaBase):
    periodo=models.OneToOneField(PeriodoContable,on_delete=models.PROTECT);fecha=models.DateTimeField(auto_now_add=True);motivo=models.TextField(blank=True)
class ReversionContable(EmpresaBase):
    asiento_origen=models.OneToOneField(AsientoContable,on_delete=models.PROTECT,related_name="reversion");asiento_reversion=models.OneToOneField(AsientoContable,on_delete=models.PROTECT,related_name="reversa_de");motivo=models.TextField()
class HistorialAsiento(models.Model):
    asiento=models.ForeignKey(AsientoContable,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=15);estado_nuevo=models.CharField(max_length=15);usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True);fecha=models.DateTimeField(auto_now_add=True)
class FacturaProveedor(EmpresaBase):
    proveedor=models.ForeignKey("compras.Proveedor",on_delete=models.PROTECT);numero=models.CharField(max_length=50);ncf=models.CharField(max_length=30,blank=True);fecha=models.DateField();vence_el=models.DateField();moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);subtotal=models.DecimalField(max_digits=18,decimal_places=2);impuesto=models.DecimalField(max_digits=18,decimal_places=2,default=0);retenciones=models.DecimalField(max_digits=18,decimal_places=2,default=0);total=models.DecimalField(max_digits=18,decimal_places=2);estado=models.CharField(max_length=15,default="PENDIENTE")
    class Meta:constraints=[models.UniqueConstraint(fields=["empresa","proveedor","numero"],name="fin_facprov_uniq")]
class DetalleFacturaProveedor(models.Model):
    factura=models.ForeignKey(FacturaProveedor,on_delete=models.CASCADE,related_name="detalles");descripcion=models.CharField(max_length=255);cantidad=models.DecimalField(max_digits=14,decimal_places=4);precio=models.DecimalField(max_digits=18,decimal_places=4);total=models.DecimalField(max_digits=18,decimal_places=2)
class CuentaPorPagarEnterprise(EmpresaBase):
    factura=models.OneToOneField(FacturaProveedor,on_delete=models.PROTECT,related_name="cuenta_pagar");proveedor=models.ForeignKey("compras.Proveedor",on_delete=models.PROTECT);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);monto_original=models.DecimalField(max_digits=18,decimal_places=2);saldo=models.DecimalField(max_digits=18,decimal_places=2);vence_el=models.DateField();estado=models.CharField(max_length=15,default="PENDIENTE");bucket_aging=models.CharField(max_length=12,default="CORRIENTE")
class MovimientoCxP(models.Model):
    cuenta=models.ForeignKey(CuentaPorPagarEnterprise,on_delete=models.CASCADE,related_name="movimientos");tipo=models.CharField(max_length=20);monto=models.DecimalField(max_digits=18,decimal_places=2);saldo_anterior=models.DecimalField(max_digits=18,decimal_places=2);saldo_posterior=models.DecimalField(max_digits=18,decimal_places=2);fecha=models.DateTimeField(auto_now_add=True)
class CuotaCxP(models.Model):
    cuenta=models.ForeignKey(CuentaPorPagarEnterprise,on_delete=models.CASCADE,related_name="cuotas");numero=models.PositiveIntegerField();vence_el=models.DateField();monto=models.DecimalField(max_digits=18,decimal_places=2);saldo=models.DecimalField(max_digits=18,decimal_places=2)
class NotaCreditoProveedor(EmpresaBase):
    factura=models.ForeignKey(FacturaProveedor,on_delete=models.PROTECT);numero=models.CharField(max_length=30);monto=models.DecimalField(max_digits=18,decimal_places=2);motivo=models.TextField()
class AnticipoProveedor(EmpresaBase):
    proveedor=models.ForeignKey("compras.Proveedor",on_delete=models.PROTECT);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);monto=models.DecimalField(max_digits=18,decimal_places=2);saldo=models.DecimalField(max_digits=18,decimal_places=2)
class SolicitudPago(EmpresaBase):
    cuenta=models.ForeignKey(CuentaPorPagarEnterprise,on_delete=models.PROTECT);monto=models.DecimalField(max_digits=18,decimal_places=2);estado=models.CharField(max_length=15,default="BORRADOR")
class OrdenPago(EmpresaBase):
    numero=models.CharField(max_length=30);solicitud=models.OneToOneField(SolicitudPago,on_delete=models.PROTECT);estado=models.CharField(max_length=15,default="BORRADOR")
class AplicacionPago(models.Model):
    orden=models.ForeignKey(OrdenPago,on_delete=models.PROTECT,related_name="aplicaciones");cuenta=models.ForeignKey(CuentaPorPagarEnterprise,on_delete=models.PROTECT);monto=models.DecimalField(max_digits=18,decimal_places=2)
class HistorialCxP(models.Model):
    cuenta=models.ForeignKey(CuentaPorPagarEnterprise,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=15);estado_nuevo=models.CharField(max_length=15);fecha=models.DateTimeField(auto_now_add=True)
