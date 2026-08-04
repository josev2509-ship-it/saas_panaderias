from django.db import models
class Presupuesto(models.Model):
 empresa=models.ForeignKey("conduces.Empresa",on_delete=models.CASCADE);codigo=models.CharField(max_length=30);nombre=models.CharField(max_length=150);anio=models.PositiveIntegerField();estado=models.CharField(max_length=15,default="BORRADOR");periodicidad=models.CharField(max_length=15,default="MENSUAL");creado_en=models.DateTimeField(auto_now_add=True)
class VersionPresupuesto(models.Model):
 presupuesto=models.ForeignKey(Presupuesto,on_delete=models.CASCADE,related_name="versiones");version=models.PositiveIntegerField();snapshot=models.JSONField(default=dict);fecha=models.DateTimeField(auto_now_add=True)
class EscenarioPresupuesto(models.Model):
 presupuesto=models.ForeignKey(Presupuesto,on_delete=models.CASCADE,related_name="escenarios");tipo=models.CharField(max_length=12,choices=[("BASE","Base"),("OPTIMISTA","Optimista"),("PESIMISTA","Pesimista")]);nombre=models.CharField(max_length=100)
class LineaPresupuesto(models.Model):
 escenario=models.ForeignKey(EscenarioPresupuesto,on_delete=models.CASCADE,related_name="lineas");cuenta=models.ForeignKey("contabilidad.CuentaContable",on_delete=models.PROTECT);dimensiones=models.JSONField(default=dict);monto=models.DecimalField(max_digits=18,decimal_places=2)
class DistribucionPresupuesto(models.Model):
 linea=models.ForeignKey(LineaPresupuesto,on_delete=models.CASCADE,related_name="distribuciones");periodo=models.DateField();monto=models.DecimalField(max_digits=18,decimal_places=2)
class CompromisoPresupuestario(models.Model):
 linea=models.ForeignKey(LineaPresupuesto,on_delete=models.PROTECT,related_name="compromisos");referencia=models.CharField(max_length=80);monto=models.DecimalField(max_digits=18,decimal_places=2);estado=models.CharField(max_length=15,default="ACTIVO")
class EjecucionPresupuestaria(models.Model):
 linea=models.ForeignKey(LineaPresupuesto,on_delete=models.PROTECT,related_name="ejecuciones");asiento=models.ForeignKey("contabilidad.AsientoContable",on_delete=models.PROTECT);monto=models.DecimalField(max_digits=18,decimal_places=2);fecha=models.DateField()
class HistorialPresupuesto(models.Model):
 presupuesto=models.ForeignKey(Presupuesto,on_delete=models.CASCADE,related_name="historial");estado_anterior=models.CharField(max_length=15);estado_nuevo=models.CharField(max_length=15);fecha=models.DateTimeField(auto_now_add=True)
