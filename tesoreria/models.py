from django.conf import settings
from django.db import models
class Base(models.Model):
 empresa=models.ForeignKey("conduces.Empresa",on_delete=models.CASCADE);creado_en=models.DateTimeField(auto_now_add=True)
 class Meta:abstract=True
class CuentaBancariaEmpresa(Base):
 banco=models.CharField(max_length=120);numero_enmascarado=models.CharField(max_length=40);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);saldo=models.DecimalField(max_digits=18,decimal_places=2,default=0);activa=models.BooleanField(default=True)
class Caja(Base):
 codigo=models.CharField(max_length=20);nombre=models.CharField(max_length=100);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);saldo=models.DecimalField(max_digits=18,decimal_places=2,default=0)
class MovimientoTesoreria(Base):
 cuenta=models.ForeignKey(CuentaBancariaEmpresa,on_delete=models.PROTECT,null=True,blank=True);caja=models.ForeignKey(Caja,on_delete=models.PROTECT,null=True,blank=True);tipo=models.CharField(max_length=15);fecha=models.DateField();monto=models.DecimalField(max_digits=18,decimal_places=2);referencia=models.CharField(max_length=100);conciliado=models.BooleanField(default=False)
class TransferenciaBancaria(Base):
 origen=models.ForeignKey(CuentaBancariaEmpresa,on_delete=models.PROTECT,related_name="transferencias_salida");destino=models.ForeignKey(CuentaBancariaEmpresa,on_delete=models.PROTECT,related_name="transferencias_entrada");monto=models.DecimalField(max_digits=18,decimal_places=2);fecha=models.DateField();estado=models.CharField(max_length=15,default="BORRADOR")
class Cheque(Base):
 cuenta=models.ForeignKey(CuentaBancariaEmpresa,on_delete=models.PROTECT);numero=models.CharField(max_length=30);beneficiario=models.CharField(max_length=180);monto=models.DecimalField(max_digits=18,decimal_places=2);fecha=models.DateField();estado=models.CharField(max_length=15,default="EMITIDO")
class Deposito(Base):
 cuenta=models.ForeignKey(CuentaBancariaEmpresa,on_delete=models.PROTECT);referencia=models.CharField(max_length=60);monto=models.DecimalField(max_digits=18,decimal_places=2);fecha=models.DateField()
class ConciliacionBancaria(Base):
 cuenta=models.ForeignKey(CuentaBancariaEmpresa,on_delete=models.PROTECT);desde=models.DateField();hasta=models.DateField();saldo_banco=models.DecimalField(max_digits=18,decimal_places=2);saldo_libros=models.DecimalField(max_digits=18,decimal_places=2);estado=models.CharField(max_length=15,default="BORRADOR")
class LineaConciliacion(models.Model):
 conciliacion=models.ForeignKey(ConciliacionBancaria,on_delete=models.CASCADE,related_name="lineas");movimiento=models.ForeignKey(MovimientoTesoreria,on_delete=models.PROTECT,null=True,blank=True);descripcion=models.CharField(max_length=255);monto_banco=models.DecimalField(max_digits=18,decimal_places=2);monto_libros=models.DecimalField(max_digits=18,decimal_places=2);coincide=models.BooleanField(default=False)
class PosicionTesoreria(Base):
 fecha=models.DateField();moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);disponible=models.DecimalField(max_digits=18,decimal_places=2);comprometido=models.DecimalField(max_digits=18,decimal_places=2);neto=models.DecimalField(max_digits=18,decimal_places=2)
class FlujoCajaProyectado(Base):
 fecha=models.DateField();moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);tipo=models.CharField(max_length=10);origen=models.CharField(max_length=30);monto=models.DecimalField(max_digits=18,decimal_places=2)
class PrestamoFinanciero(Base):
 entidad=models.CharField(max_length=180);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);principal=models.DecimalField(max_digits=18,decimal_places=2);saldo=models.DecimalField(max_digits=18,decimal_places=2);tasa=models.DecimalField(max_digits=8,decimal_places=4)
class CuotaPrestamo(models.Model):
 prestamo=models.ForeignKey(PrestamoFinanciero,on_delete=models.CASCADE,related_name="cuotas");numero=models.PositiveIntegerField();vence_el=models.DateField();capital=models.DecimalField(max_digits=18,decimal_places=2);interes=models.DecimalField(max_digits=18,decimal_places=2);pagada=models.BooleanField(default=False)
class LineaCredito(Base):
 entidad=models.CharField(max_length=180);moneda=models.ForeignKey("catalogos.MonedaEmpresa",on_delete=models.PROTECT);limite=models.DecimalField(max_digits=18,decimal_places=2);utilizado=models.DecimalField(max_digits=18,decimal_places=2,default=0)
class InversionFinanciera(Base):
 entidad=models.CharField(max_length=180);instrumento=models.CharField(max_length=80);monto=models.DecimalField(max_digits=18,decimal_places=2);tasa=models.DecimalField(max_digits=8,decimal_places=4);vence_el=models.DateField()

class ImportacionExtractoBancario(Base):
 cuenta=models.ForeignKey(CuentaBancariaEmpresa,on_delete=models.PROTECT,related_name="extractos_importados");nombre_archivo=models.CharField(max_length=180);formato=models.CharField(max_length=8);huella=models.CharField(max_length=64);estado=models.CharField(max_length=15,default="PREVISTA");mapeo=models.JSONField(default=dict);confirmado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+");confirmado_en=models.DateTimeField(null=True,blank=True)
 class Meta:constraints=[models.UniqueConstraint(fields=["empresa","cuenta","huella"],name="tes_extracto_emp_cta_hash_uniq")]

class LineaExtractoBancario(models.Model):
 importacion=models.ForeignKey(ImportacionExtractoBancario,on_delete=models.CASCADE,related_name="lineas");numero=models.PositiveIntegerField();fecha=models.DateField();descripcion=models.CharField(max_length=255);referencia=models.CharField(max_length=100,blank=True);monto=models.DecimalField(max_digits=18,decimal_places=2);saldo=models.DecimalField(max_digits=18,decimal_places=2,null=True,blank=True);huella=models.CharField(max_length=64);movimiento=models.ForeignKey(MovimientoTesoreria,on_delete=models.PROTECT,null=True,blank=True,related_name="lineas_extracto");estado=models.CharField(max_length=15,default="PENDIENTE");tipo_coincidencia=models.CharField(max_length=20,blank=True)
 class Meta:constraints=[models.UniqueConstraint(fields=["importacion","huella"],name="tes_linea_extracto_hash_uniq")];indexes=[models.Index(fields=["importacion","estado"],name="tes_linext_imp_estado_idx")]
