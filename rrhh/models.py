from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
class Base(models.Model):
 empresa=models.ForeignKey("conduces.Empresa",on_delete=models.CASCADE);creado_en=models.DateTimeField(auto_now_add=True)
 class Meta:abstract=True
class Departamento(Base):
 codigo=models.CharField(max_length=20);nombre=models.CharField(max_length=120);descripcion=models.TextField(blank=True);activo=models.BooleanField(default=True)
 def __str__(self):return f"{self.codigo} · {self.nombre}"
class Puesto(Base):
 codigo=models.CharField(max_length=20);nombre=models.CharField(max_length=120);descripcion=models.TextField(blank=True)
 def __str__(self):return f"{self.codigo} · {self.nombre}"
class SecuenciaEmpleado(models.Model):
 empresa=models.OneToOneField("conduces.Empresa",on_delete=models.CASCADE,related_name="secuencia_empleados");ultimo_numero=models.PositiveBigIntegerField(default=0);actualizado_en=models.DateTimeField(auto_now=True)

class DescripcionPuesto(Base):
 puesto=models.ForeignKey(Puesto,on_delete=models.PROTECT,related_name="descripciones_funciones");objetivo=models.TextField();funciones=models.TextField();responsabilidades=models.TextField(blank=True);procedimientos=models.TextField(blank=True);herramientas=models.TextField(blank=True);controles=models.TextField(blank=True);documentos_relacionados=models.TextField(blank=True);version=models.PositiveIntegerField(default=1);vigente_desde=models.DateField();activa=models.BooleanField(default=True)
 class Meta:constraints=[models.UniqueConstraint(fields=["puesto","version"],name="rrhh_desc_puesto_version_uniq")]
class CentroTrabajo(Base):
 """Canonical workplace catalog. The legacy class name is retained for DB compatibility."""
 codigo=models.CharField(max_length=20);nombre=models.CharField(max_length=120);direccion=models.TextField(blank=True);descripcion=models.TextField(blank=True);activo=models.BooleanField(default=True)
 def __str__(self):return f"{self.codigo} · {self.nombre}"
 class Meta:verbose_name="Lugar de trabajo";verbose_name_plural="Lugares de trabajo"
class EntidadFinancieraRRHH(Base):
 codigo=models.CharField(max_length=20);nombre=models.CharField(max_length=150);direccion=models.TextField(blank=True);activo=models.BooleanField(default=True)
 def __str__(self):return self.nombre
class Empleado(Base):
 codigo=models.CharField(max_length=20);nombres=models.CharField(max_length=100);apellidos=models.CharField(max_length=100);identificacion=models.CharField(max_length=30);correo=models.EmailField(blank=True);telefono=models.CharField(max_length=30,blank=True);contacto_emergencia=models.CharField(max_length=150,blank=True);puesto=models.ForeignKey(Puesto,on_delete=models.PROTECT);departamento=models.ForeignKey(Departamento,on_delete=models.PROTECT);supervisor=models.ForeignKey("self",on_delete=models.PROTECT,null=True,blank=True);centro=models.ForeignKey(CentroTrabajo,on_delete=models.PROTECT);fecha_ingreso=models.DateField();salario=models.DecimalField(max_digits=18,decimal_places=2);forma_pago=models.CharField(max_length=20,default="TRANSFERENCIA");cuenta_bancaria_cifrada=models.TextField(blank=True);estado=models.CharField(max_length=15,default="ACTIVO");foto=models.ImageField(upload_to="rrhh/empleados/",blank=True)
 sexo=models.CharField(max_length=20,blank=True);fecha_nacimiento=models.DateField(null=True,blank=True);estado_civil=models.CharField(max_length=30,blank=True);nacionalidad=models.CharField(max_length=60,blank=True);direccion=models.TextField(blank=True);tipo_contrato=models.CharField(max_length=30,blank=True);frecuencia_pago=models.CharField(max_length=20,default="MENSUAL");banco=models.CharField(max_length=100,blank=True);tipo_cuenta_bancaria=models.CharField(max_length=30,blank=True);licencia_conducir=models.CharField(max_length=40,blank=True);categoria_licencia=models.CharField(max_length=20,blank=True);vence_licencia=models.DateField(null=True,blank=True);observaciones=models.TextField(blank=True);es_supervisor=models.BooleanField(default=False)
 class Meta:constraints=[models.UniqueConstraint(fields=["empresa","codigo"],name="rrhh_emp_codigo_uniq"),models.UniqueConstraint(fields=["empresa","identificacion"],name="rrhh_emp_ident_uniq")]
 @classmethod
 def siguiente_codigo(cls,empresa):
  with transaction.atomic():
   secuencia,_=SecuenciaEmpleado.objects.select_for_update().get_or_create(empresa=empresa)
   secuencia.ultimo_numero+=1;secuencia.save(update_fields=["ultimo_numero","actualizado_en"])
   return f"EMP-{secuencia.ultimo_numero:06d}"
 def __str__(self):return f"{self.codigo} · {self.nombres} {self.apellidos}"
class Organigrama(Base):empleado=models.OneToOneField(Empleado,on_delete=models.CASCADE);padre=models.ForeignKey("self",on_delete=models.PROTECT,null=True,blank=True)
class ContratoEmpleado(Base):
 empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name="contratos");numero=models.CharField(max_length=40,blank=True);version=models.PositiveIntegerField(default=1);tipo=models.CharField(max_length=30);inicio=models.DateField();fin=models.DateField(null=True,blank=True);salario=models.DecimalField(max_digits=18,decimal_places=2);estado=models.CharField(max_length=15,default="BORRADOR");puesto=models.ForeignKey(Puesto,on_delete=models.PROTECT,null=True,blank=True);jornada=models.CharField(max_length=80,blank=True);renovacion_de=models.ForeignKey("self",on_delete=models.PROTECT,null=True,blank=True,related_name="renovaciones");objeto=models.TextField(blank=True);lugar_prestacion=models.TextField(blank=True);motivo_temporal=models.TextField(blank=True);anexos=models.TextField(blank=True);observaciones=models.TextField(blank=True)
 def __str__(self):return f"{self.numero or 'Contrato'} v{self.version} · {self.empleado}"
 def save(self,*args,**kwargs):
  if not self.numero and self.empleado_id:self.numero=f"CTR-{self.empleado.codigo}-{self.version:02d}"
  super().save(*args,**kwargs)

class SolicitudDocumentoRRHH(Base):
 TIPOS=(("LABORAL","Certificación laboral"),("BANCARIA","Carta bancaria"),("CONSULAR","Carta consular"),("CONTRATO","Contrato"),("TEMPORAL","Contrato temporal"),("ANEXO","Anexo de funciones"),("EXPEDIENTE","Expediente del empleado"))
 empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name="solicitudes_documentos");tipo=models.CharField(max_length=20,choices=TIPOS);entidad_financiera=models.ForeignKey(EntidadFinancieraRRHH,on_delete=models.PROTECT,null=True,blank=True);destinatario=models.CharField(max_length=180,blank=True);pais_destino=models.CharField(max_length=100,blank=True);proposito=models.CharField(max_length=180,blank=True);numero=models.CharField(max_length=50,blank=True);version=models.PositiveIntegerField(default=1);snapshot=models.JSONField(default=dict);estado=models.CharField(max_length=20,default="BORRADOR")
 def __str__(self):return f"{self.get_tipo_display()} · {self.empleado}"
class DependienteEmpleado(models.Model):empleado=models.ForeignKey(Empleado,on_delete=models.CASCADE,related_name="dependientes");nombre=models.CharField(max_length=150);parentesco=models.CharField(max_length=30);fecha_nacimiento=models.DateField(null=True)
class HistorialLaboral(models.Model):empleado=models.ForeignKey(Empleado,on_delete=models.CASCADE,related_name="historial");accion=models.CharField(max_length=40);snapshot=models.JSONField(default=dict);fecha=models.DateTimeField(auto_now_add=True)
class BeneficioEmpleado(Base):empleado=models.ForeignKey(Empleado,on_delete=models.CASCADE,related_name="beneficios");nombre=models.CharField(max_length=100);monto=models.DecimalField(max_digits=18,decimal_places=2,default=0)
class DocumentoEmpleado(Base):
 empleado=models.ForeignKey(Empleado,on_delete=models.CASCADE,related_name="documentos_rrhh");tipo=models.CharField(max_length=30);descripcion=models.TextField(blank=True);archivo=models.FileField(upload_to="rrhh/documentos/",validators=[FileExtensionValidator(["pdf","jpg","jpeg","png","webp"])]);emitido_el=models.DateField(null=True,blank=True);vence_el=models.DateField(null=True,blank=True);cargado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True);estado=models.CharField(max_length=20,default="ACTIVO");version=models.PositiveIntegerField(default=1);documento_anterior=models.ForeignKey("self",on_delete=models.SET_NULL,null=True,blank=True,related_name="versiones")
class AccionDisciplinaria(Base):empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name="acciones_disciplinarias");tipo=models.CharField(max_length=30);fecha=models.DateField();motivo=models.TextField();descripcion=models.TextField(blank=True);gravedad=models.CharField(max_length=20,default="MEDIA");accion_tomada=models.TextField(blank=True);responsable=models.CharField(max_length=150,blank=True);estado=models.CharField(max_length=20,default="ABIERTA")
class EvaluacionDesempeno(Base):empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT);periodo=models.CharField(max_length=20);puntuacion=models.DecimalField(max_digits=5,decimal_places=2);comentarios=models.TextField(blank=True)
class Capacitacion(Base):nombre=models.CharField(max_length=150);institucion=models.CharField(max_length=150,blank=True);modalidad=models.CharField(max_length=30,blank=True);inicio=models.DateField();fin=models.DateField();horas=models.DecimalField(max_digits=7,decimal_places=2,default=0);costo=models.DecimalField(max_digits=18,decimal_places=2,default=0);vence_el=models.DateField(null=True,blank=True);observaciones=models.TextField(blank=True)
class ParticipacionCapacitacion(models.Model):capacitacion=models.ForeignKey(Capacitacion,on_delete=models.CASCADE);empleado=models.ForeignKey(Empleado,on_delete=models.CASCADE,related_name="capacitaciones");resultado=models.CharField(max_length=100,blank=True)
class SolicitudVacacion(Base):empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT);desde=models.DateField();hasta=models.DateField();dias=models.DecimalField(max_digits=6,decimal_places=2);estado=models.CharField(max_length=15,default="BORRADOR")
class SaldoVacacion(models.Model):empleado=models.OneToOneField(Empleado,on_delete=models.CASCADE);disponibles=models.DecimalField(max_digits=6,decimal_places=2);tomados=models.DecimalField(max_digits=6,decimal_places=2,default=0)
class LicenciaEmpleado(Base):empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT);tipo=models.CharField(max_length=30);desde=models.DateField();hasta=models.DateField();motivo=models.TextField(blank=True);estado=models.CharField(max_length=15,default="APROBADA")
class AusenciaEmpleado(Base):empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT);fecha=models.DateField();justificada=models.BooleanField(default=False)
class PermisoEmpleado(Base):empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT);desde=models.DateTimeField();hasta=models.DateTimeField();estado=models.CharField(max_length=15,default="BORRADOR")
class HorarioTrabajo(Base):nombre=models.CharField(max_length=100);hora_entrada=models.TimeField();hora_salida=models.TimeField();dias=models.JSONField(default=list)
class TurnoTrabajo(Base):nombre=models.CharField(max_length=100);horario=models.ForeignKey(HorarioTrabajo,on_delete=models.PROTECT);recargo=models.DecimalField(max_digits=5,decimal_places=2,default=0)
class AsignacionTurno(Base):empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT);turno=models.ForeignKey(TurnoTrabajo,on_delete=models.PROTECT);desde=models.DateField();hasta=models.DateField(null=True,blank=True)
class RegistroAsistencia(Base):empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name="ponches");fecha=models.DateField();entrada=models.DateTimeField(null=True);salida=models.DateTimeField(null=True);minutos_tardanza=models.PositiveIntegerField(default=0);horas_trabajadas=models.DecimalField(max_digits=6,decimal_places=2,default=0);origen=models.CharField(max_length=20,default="MANUAL");dispositivo=models.CharField(max_length=100,blank=True);ubicacion=models.CharField(max_length=150,blank=True);observacion=models.TextField(blank=True);estado=models.CharField(max_length=20,default="ABIERTO");corregido=models.BooleanField(default=False)
class IncidenciaAsistencia(Base):registro=models.ForeignKey(RegistroAsistencia,on_delete=models.CASCADE,related_name="incidencias");tipo=models.CharField(max_length=30);descripcion=models.TextField();minutos=models.PositiveIntegerField(default=0);motivo=models.TextField(blank=True);aprobador=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="incidencias_rrhh_aprobadas");aprobada=models.BooleanField(default=False);estado=models.CharField(max_length=20,default="PENDIENTE");observacion=models.TextField(blank=True)
class HoraExtra(Base):empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name="horas_extra");fecha=models.DateField();horas_ordinarias=models.DecimalField(max_digits=6,decimal_places=2,default=0);horas=models.DecimalField(max_digits=6,decimal_places=2);tipo=models.CharField(max_length=30,default="ORDINARIA");factor=models.DecimalField(max_digits=5,decimal_places=2,default=1);monto=models.DecimalField(max_digits=18,decimal_places=2,default=0);aprobador=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="horas_extra_aprobadas");estado=models.CharField(max_length=15,default="PENDIENTE");nomina_id=models.PositiveBigIntegerField(null=True,blank=True)
class CalendarioLaboral(Base):anio=models.PositiveIntegerField();nombre=models.CharField(max_length=100)
class DiaFeriado(models.Model):calendario=models.ForeignKey(CalendarioLaboral,on_delete=models.CASCADE,related_name="feriados");fecha=models.DateField();nombre=models.CharField(max_length=120)

class SalidaEmpleado(Base):
 empleado=models.OneToOneField(Empleado,on_delete=models.PROTECT,related_name="salida");fecha_salida=models.DateField();tipo=models.CharField(max_length=30);motivo=models.TextField();ultima_fecha_laborada=models.DateField();responsable=models.CharField(max_length=150);comentarios=models.TextField(blank=True);checklist=models.JSONField(default=dict);activos_pendientes=models.BooleanField(default=False);vacaciones_pendientes=models.DecimalField(max_digits=7,decimal_places=2,default=0);estado=models.CharField(max_length=20,default="BORRADOR")

class CierreAsistencia(Base):
 desde=models.DateField();hasta=models.DateField();estado=models.CharField(max_length=20,default="ABIERTO");cerrado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True);cerrado_en=models.DateTimeField(null=True,blank=True)
 class Meta:constraints=[models.UniqueConstraint(fields=["empresa","desde","hasta"],name="rrhh_cierre_asistencia_uniq")]

class NovedadTSS(Base):
 empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name="novedades_tss");periodo=models.CharField(max_length=7);tipo=models.CharField(max_length=30);fecha_efectiva=models.DateField();salario_reportable=models.DecimalField(max_digits=18,decimal_places=2,default=0);estado=models.CharField(max_length=20,default="BORRADOR");observacion=models.TextField(blank=True)

class ReingresoEmpleado(Base):
 empleado=models.ForeignKey(Empleado,on_delete=models.PROTECT,related_name="reingresos");fecha_reingreso=models.DateField();puesto=models.ForeignKey(Puesto,on_delete=models.PROTECT);departamento=models.ForeignKey(Departamento,on_delete=models.PROTECT);centro=models.ForeignKey(CentroTrabajo,on_delete=models.PROTECT);salario=models.DecimalField(max_digits=18,decimal_places=2);tipo_contrato=models.CharField(max_length=30);observaciones=models.TextField(blank=True)
