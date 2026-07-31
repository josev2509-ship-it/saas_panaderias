from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F

from conduces.models import Empresa


class AuditEmpresa(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE)
    creado_en=models.DateTimeField(auto_now_add=True)
    actualizado_en=models.DateTimeField(auto_now=True)
    class Meta: abstract=True


class MiembroWorkflowEmpresa(models.Model):
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE,related_name="miembros_workflow")
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="membresias_workflow")
    rol_codigo=models.CharField(max_length=80,blank=True); activo=models.BooleanField(default=True); creado_en=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["empresa","usuario"],name="wf_miembro_emp_usuario_uniq")]
        indexes=[models.Index(fields=["empresa","activo"],name="wf_miembro_emp_act_idx")]


class ReglaAprobacion(AuditEmpresa):
    ESTADOS=(("BORRADOR","Borrador"),("ACTIVA","Activa"),("INACTIVA","Inactiva"),("RETIRADA","Retirada"))
    codigo=models.CharField(max_length=40); nombre=models.CharField(max_length=160); descripcion=models.TextField(blank=True)
    dominio=models.CharField(max_length=50); tipo_documento=models.CharField(max_length=80); version=models.PositiveIntegerField(default=1)
    estado=models.CharField(max_length=12,choices=ESTADOS,default="BORRADOR"); prioridad=models.PositiveIntegerField(default=0)
    vigente_desde=models.DateField(null=True,blank=True); vigente_hasta=models.DateField(null=True,blank=True)
    es_predeterminada=models.BooleanField(default=False); requiere_presupuesto=models.BooleanField(default=False)
    permite_autoaprobacion=models.BooleanField(default=False); permite_reapertura=models.BooleanField(default=False)
    permite_devolucion=models.BooleanField(default=True); rechazo_finaliza=models.BooleanField(default=True)
    comentario_obligatorio_aprobacion=models.BooleanField(default=False); comentario_obligatorio_rechazo=models.BooleanField(default=True)
    comentario_obligatorio_devolucion=models.BooleanField(default=True); activa=models.BooleanField(default=True)
    creado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+")
    actualizado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+")
    class Meta:
        ordering=["dominio","tipo_documento","-prioridad","-version"]
        constraints=[
            models.UniqueConstraint(fields=["empresa","codigo","version"],name="wf_regla_emp_cod_ver_uniq"),
            models.UniqueConstraint(fields=["empresa","dominio","tipo_documento"],condition=Q(estado="ACTIVA",es_predeterminada=True),name="wf_regla_default_activa_uniq"),
            models.CheckConstraint(condition=Q(version__gt=0),name="wf_regla_version_pos"),
        ]
        indexes=[models.Index(fields=["empresa","dominio","tipo_documento"],name="wf_regla_scope_idx"),models.Index(fields=["empresa","estado"],name="wf_regla_estado_idx")]
        permissions=[("versionar_regla_aprobacion","Puede versionar reglas"),("activar_regla_aprobacion","Puede activar reglas"),("retirar_regla_aprobacion","Puede retirar reglas"),("validar_regla_aprobacion","Puede validar reglas"),("gestionar_asignadores_workflow","Puede gestionar asignadores"),("gestionar_suplencias_workflow","Puede gestionar suplencias"),("iniciar_workflow","Puede iniciar workflows"),("aprobar_workflow","Puede aprobar"),("rechazar_workflow","Puede rechazar"),("devolver_workflow","Puede devolver"),("cancelar_workflow","Puede cancelar"),("reabrir_workflow","Puede reabrir"),("reasignar_workflow","Puede reasignar"),("view_historial_workflow","Puede ver historial"),("view_tareas_workflow","Puede ver tareas"),("administrar_workflow","Puede administrar workflow"),("exportar_workflow","Puede exportar workflow")]
    def clean(self):
        errors={}
        if self.vigente_hasta and self.vigente_desde and self.vigente_hasta<self.vigente_desde: errors["vigente_hasta"]="La vigencia final no puede ser anterior."
        if not self.dominio.strip(): errors["dominio"]="El dominio es obligatorio."
        if not self.tipo_documento.strip(): errors["tipo_documento"]="El tipo documental es obligatorio."
        if self.pk and ReglaAprobacion.objects.filter(pk=self.pk,estado="ACTIVA").exists():
            original=ReglaAprobacion.objects.get(pk=self.pk)
            estructurales=("dominio","tipo_documento","version","permite_autoaprobacion","permite_reapertura","permite_devolucion","rechazo_finaliza")
            if any(getattr(original,x)!=getattr(self,x) for x in estructurales): errors["estado"]="Una regla activa es estructuralmente inmutable; cree una versión."
        if errors: raise ValidationError(errors)
    def __str__(self): return f"{self.codigo} v{self.version} · {self.nombre}"


class CondicionReglaAprobacion(AuditEmpresa):
    OPERADORES=tuple((x,x.replace("_"," ").title()) for x in ("IGUAL","DIFERENTE","MAYOR_QUE","MAYOR_O_IGUAL","MENOR_QUE","MENOR_O_IGUAL","EN_LISTA","NO_EN_LISTA","CONTIENE","NO_CONTIENE","ES_NULO","NO_ES_NULO"))
    TIPOS=(("TEXTO","Texto"),("DECIMAL","Decimal"),("ENTERO","Entero"),("BOOLEANO","Booleano"),("FECHA","Fecha"),("LISTA","Lista"))
    regla=models.ForeignKey(ReglaAprobacion,on_delete=models.PROTECT,related_name="condiciones")
    campo=models.CharField(max_length=80); operador=models.CharField(max_length=20,choices=OPERADORES); valor_tipo=models.CharField(max_length=10,choices=TIPOS)
    valor_texto=models.TextField(blank=True); valor_decimal=models.DecimalField(max_digits=20,decimal_places=4,null=True,blank=True)
    valor_entero=models.BigIntegerField(null=True,blank=True); valor_booleano=models.BooleanField(null=True,blank=True); valor_fecha=models.DateField(null=True,blank=True)
    agrupador=models.PositiveIntegerField(default=1); orden=models.PositiveIntegerField(default=0); activa=models.BooleanField(default=True)
    class Meta: ordering=["agrupador","orden","id"]
    def clean(self):
        if self.regla_id and self.regla.empresa_id!=self.empresa_id: raise ValidationError("La regla pertenece a otra empresa.")
        if any(x in self.campo for x in ("__",".","(",")")): raise ValidationError({"campo":"Campo no permitido."})


class NivelAprobacion(AuditEmpresa):
    ESTRATEGIAS=(("CUALQUIERA","Cualquiera"),("UNANIMIDAD","Unanimidad"),("MAYORIA_SIMPLE","Mayoría simple"),("MINIMO_VOTOS","Mínimo de votos"),("TODOS_LOS_ASIGNADOS","Todos"),("PRIMERA_RESPUESTA","Primera respuesta"))
    regla=models.ForeignKey(ReglaAprobacion,on_delete=models.PROTECT,related_name="niveles"); numero=models.PositiveIntegerField(); nombre=models.CharField(max_length=120); descripcion=models.TextField(blank=True)
    estrategia_asignacion=models.CharField(max_length=30,default="DECLARATIVA"); estrategia_decision=models.CharField(max_length=24,choices=ESTRATEGIAS)
    minimo_aprobaciones=models.PositiveIntegerField(default=1); porcentaje_mayoria=models.DecimalField(max_digits=5,decimal_places=2,default=50)
    rechazo_finaliza=models.BooleanField(default=True); permite_devolucion=models.BooleanField(default=True); permite_delegacion=models.BooleanField(default=False); permite_suplencia=models.BooleanField(default=True)
    requiere_comentario_aprobacion=models.BooleanField(default=False); requiere_comentario_rechazo=models.BooleanField(default=True); requiere_comentario_devolucion=models.BooleanField(default=True)
    dias_objetivo=models.PositiveIntegerField(null=True,blank=True); horas_objetivo=models.PositiveIntegerField(null=True,blank=True); orden=models.PositiveIntegerField(default=0); activo=models.BooleanField(default=True)
    class Meta:
        ordering=["orden","numero"]
        constraints=[models.UniqueConstraint(fields=["regla","numero"],name="wf_nivel_regla_num_uniq"),models.CheckConstraint(condition=Q(numero__gt=0),name="wf_nivel_num_pos")]
    def clean(self):
        if self.regla_id and self.regla.empresa_id!=self.empresa_id: raise ValidationError("La regla pertenece a otra empresa.")
        if self.estrategia_decision=="MINIMO_VOTOS" and self.minimo_aprobaciones<1: raise ValidationError({"minimo_aprobaciones":"Debe ser positivo."})


class AsignadorNivel(AuditEmpresa):
    TIPOS=tuple((x,x.replace("_"," ").title()) for x in ("USUARIO","GRUPO","PERMISO","ROL_EMPRESA","SUPERVISOR_SOLICITANTE","RESPONSABLE_CENTRO_COSTO","RESPONSABLE_AREA","DINAMICO_ADAPTADOR"))
    nivel=models.ForeignKey(NivelAprobacion,on_delete=models.PROTECT,related_name="asignadores"); tipo=models.CharField(max_length=30,choices=TIPOS)
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name="+"); grupo=models.ForeignKey(Group,on_delete=models.PROTECT,null=True,blank=True)
    permiso_codename=models.CharField(max_length=100,blank=True); rol_codigo=models.CharField(max_length=80,blank=True); parametro=models.CharField(max_length=160,blank=True)
    obligatorio=models.BooleanField(default=True); orden=models.PositiveIntegerField(default=0); activo=models.BooleanField(default=True)
    class Meta: ordering=["orden","id"]
    def clean(self):
        if self.nivel_id and self.nivel.empresa_id!=self.empresa_id: raise ValidationError("El nivel pertenece a otra empresa.")
        if self.tipo=="USUARIO" and not self.usuario_id: raise ValidationError({"usuario":"Seleccione un usuario."})
        if self.tipo=="GRUPO" and not self.grupo_id: raise ValidationError({"grupo":"Seleccione un grupo."})
        if self.usuario_id and not (getattr(self.usuario,"empresa_principal",None) and self.usuario.empresa_principal.pk==self.empresa_id) and not MiembroWorkflowEmpresa.objects.filter(empresa_id=self.empresa_id,usuario=self.usuario,activo=True).exists(): raise ValidationError({"usuario":"El usuario no pertenece a la empresa."})


class SuplenciaAprobador(AuditEmpresa):
    ALCANCES=(("GLOBAL","Global"),("DOMINIO","Dominio"),("TIPO_DOCUMENTO","Tipo documental"),("REGLA","Regla"))
    titular=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="suplencias_titular"); suplente=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="suplencias_suplente")
    vigente_desde=models.DateTimeField(); vigente_hasta=models.DateTimeField(); alcance=models.CharField(max_length=20,choices=ALCANCES)
    dominio=models.CharField(max_length=50,blank=True); tipo_documento=models.CharField(max_length=80,blank=True); regla=models.ForeignKey(ReglaAprobacion,on_delete=models.PROTECT,null=True,blank=True)
    motivo=models.TextField(); activa=models.BooleanField(default=True); creada_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+"); aprobada_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+")
    class Meta:
        constraints=[models.CheckConstraint(condition=~Q(titular=F("suplente")),name="wf_suplencia_distintos"),models.CheckConstraint(condition=Q(vigente_hasta__gt=F("vigente_desde")),name="wf_suplencia_vigencia")]
        indexes=[models.Index(fields=["empresa","titular","activa"],name="wf_suplencia_vig_idx")]
    def clean(self):
        if self.titular_id==self.suplente_id: raise ValidationError("Titular y suplente deben ser distintos.")
        for field in ("titular","suplente"):
            u=getattr(self,field,None)
            if u and not (getattr(u,"empresa_principal",None) and u.empresa_principal.pk==self.empresa_id) and not MiembroWorkflowEmpresa.objects.filter(empresa_id=self.empresa_id,usuario=u,activo=True).exists(): raise ValidationError({field:"El usuario no pertenece a la empresa."})
        if SuplenciaAprobador.objects.filter(empresa_id=self.empresa_id,titular_id=self.suplente_id,suplente_id=self.titular_id,activa=True).exclude(pk=self.pk).exists(): raise ValidationError("La suplencia produciría un ciclo directo.")


class InstanciaWorkflow(models.Model):
    ESTADOS=tuple((x,x.replace("_"," ").title()) for x in ("BORRADOR","INICIADA","EN_APROBACION","APROBADA","RECHAZADA","DEVUELTA","CANCELADA","ERROR"))
    ACTIVOS=("BORRADOR","INICIADA","EN_APROBACION","DEVUELTA")
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE); regla=models.ForeignKey(ReglaAprobacion,on_delete=models.PROTECT,related_name="instancias")
    regla_version=models.PositiveIntegerField(); content_type=models.ForeignKey("contenttypes.ContentType",on_delete=models.PROTECT); object_id=models.PositiveBigIntegerField()
    referencia_externa=models.CharField(max_length=160,blank=True); proposito=models.CharField(max_length=80,default="APROBACION")
    dominio=models.CharField(max_length=50); tipo_documento=models.CharField(max_length=80); estado=models.CharField(max_length=20,choices=ESTADOS,default="BORRADOR")
    nivel_actual=models.PositiveIntegerField(null=True,blank=True); solicitante=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="workflows_solicitados")
    iniciada_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="workflows_iniciados"); iniciada_en=models.DateTimeField(auto_now_add=True); finalizada_en=models.DateTimeField(null=True,blank=True)
    resultado=models.CharField(max_length=30,blank=True); motivo_final=models.TextField(blank=True); contexto_snapshot=models.JSONField(default=dict); documento_snapshot=models.JSONField(default=dict)
    idempotency_key=models.CharField(max_length=180); creado_en=models.DateTimeField(auto_now_add=True); actualizado_en=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["empresa","idempotency_key"],name="wf_inst_idem_uniq"),models.UniqueConstraint(fields=["empresa","content_type","object_id","proposito"],condition=Q(estado__in=("BORRADOR","INICIADA","EN_APROBACION","DEVUELTA")),name="wf_inst_doc_activa_uniq")]
        indexes=[models.Index(fields=["empresa","estado"],name="wf_inst_emp_estado_idx"),models.Index(fields=["content_type","object_id"],name="wf_inst_obj_idx")]


class RondaWorkflow(models.Model):
    ESTADOS=(("ACTIVA","Activa"),("FINALIZADA","Finalizada"),("CANCELADA","Cancelada"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE); instancia=models.ForeignKey(InstanciaWorkflow,on_delete=models.PROTECT,related_name="rondas")
    numero=models.PositiveIntegerField(); motivo=models.TextField(blank=True); iniciada_en=models.DateTimeField(auto_now_add=True); finalizada_en=models.DateTimeField(null=True,blank=True)
    iniciada_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT); estado=models.CharField(max_length=12,choices=ESTADOS,default="ACTIVA")
    class Meta:
        constraints=[models.UniqueConstraint(fields=["instancia","numero"],name="wf_ronda_inst_num_uniq"),models.UniqueConstraint(fields=["instancia"],condition=Q(estado="ACTIVA"),name="wf_ronda_activa_uniq")]


class NivelInstanciaWorkflow(AuditEmpresa):
    ESTADOS=tuple((x,x.title()) for x in ("PENDIENTE","ACTIVO","APROBADO","RECHAZADO","DEVUELTO","OMITIDO","CANCELADO"))
    instancia=models.ForeignKey(InstanciaWorkflow,on_delete=models.PROTECT,related_name="niveles_instancia"); ronda=models.ForeignKey(RondaWorkflow,on_delete=models.PROTECT,related_name="niveles")
    numero=models.PositiveIntegerField(); nombre_snapshot=models.CharField(max_length=120); estrategia_decision=models.CharField(max_length=24,choices=NivelAprobacion.ESTRATEGIAS)
    minimo_aprobaciones=models.PositiveIntegerField(default=1); porcentaje_mayoria=models.DecimalField(max_digits=5,decimal_places=2,default=50)
    rechazo_finaliza=models.BooleanField(default=True); permite_devolucion=models.BooleanField(default=True)
    requiere_comentario_aprobacion=models.BooleanField(default=False); requiere_comentario_rechazo=models.BooleanField(default=True); requiere_comentario_devolucion=models.BooleanField(default=True)
    estado=models.CharField(max_length=12,choices=ESTADOS,default="PENDIENTE"); activado_en=models.DateTimeField(null=True,blank=True); completado_en=models.DateTimeField(null=True,blank=True)
    vencimiento_objetivo=models.DateTimeField(null=True,blank=True); resultado=models.CharField(max_length=30,blank=True); motivo=models.TextField(blank=True); orden=models.PositiveIntegerField(default=0)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["ronda","numero"],name="wf_nivinst_ronda_num_uniq"),models.UniqueConstraint(fields=["instancia"],condition=Q(estado="ACTIVO"),name="wf_nivinst_activo_uniq")]
        indexes=[models.Index(fields=["empresa","estado"],name="wf_nivinst_estado_idx")]


class AsignacionAprobacion(AuditEmpresa):
    instancia=models.ForeignKey(InstanciaWorkflow,on_delete=models.PROTECT,related_name="asignaciones"); nivel_instancia=models.ForeignKey(NivelInstanciaWorkflow,on_delete=models.PROTECT,related_name="asignaciones")
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="asignaciones_workflow"); usuario_titular=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name="asignaciones_representadas")
    origen_tipo=models.CharField(max_length=30); origen_referencia=models.CharField(max_length=160,blank=True); es_titular=models.BooleanField(default=True); es_suplente=models.BooleanField(default=False)
    asignado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="+"); asignado_en=models.DateTimeField(auto_now_add=True)
    activa=models.BooleanField(default=True); revocada=models.BooleanField(default=False); motivo_revocacion=models.TextField(blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["nivel_instancia","usuario"],condition=Q(activa=True,revocada=False),name="wf_asig_usuario_activa_uniq")]
        indexes=[models.Index(fields=["empresa","usuario","activa"],name="wf_asig_tarea_idx")]


class DecisionAprobacion(models.Model):
    DECISIONES=(("APROBAR","Aprobar"),("RECHAZAR","Rechazar"),("DEVOLVER","Devolver"),("ABSTENERSE","Abstenerse"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE); instancia=models.ForeignKey(InstanciaWorkflow,on_delete=models.PROTECT,related_name="decisiones")
    ronda=models.ForeignKey(RondaWorkflow,on_delete=models.PROTECT,related_name="decisiones"); nivel_instancia=models.ForeignKey(NivelInstanciaWorkflow,on_delete=models.PROTECT,related_name="decisiones")
    asignacion=models.ForeignKey(AsignacionAprobacion,on_delete=models.PROTECT,related_name="decisiones"); usuario_efectivo=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="decisiones_workflow")
    usuario_representado=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name="decisiones_representadas")
    decision=models.CharField(max_length=12,choices=DECISIONES); comentario=models.TextField(blank=True); metadata_segura=models.JSONField(default=dict,blank=True)
    idempotency_key=models.CharField(max_length=180); creada_en=models.DateTimeField(auto_now_add=True); ip_address=models.GenericIPAddressField(null=True,blank=True); user_agent=models.CharField(max_length=300,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["empresa","idempotency_key"],name="wf_decision_idem_uniq"),models.UniqueConstraint(fields=["asignacion","ronda"],name="wf_decision_asig_ronda_uniq")]
        indexes=[models.Index(fields=["nivel_instancia","decision"],name="wf_decision_nivel_idx")]
        default_permissions=("view",)
    def save(self,*args,**kwargs):
        if self.pk: raise ValidationError("Las decisiones son inmutables.")
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs): raise ValidationError("Las decisiones no se eliminan.")


class SolicitudCorreccionWorkflow(models.Model):
    ESTADOS=(("ABIERTA","Abierta"),("ATENDIDA","Atendida"),("CANCELADA","Cancelada"))
    empresa=models.ForeignKey(Empresa,on_delete=models.CASCADE); instancia=models.ForeignKey(InstanciaWorkflow,on_delete=models.PROTECT,related_name="correcciones")
    nivel_instancia=models.ForeignKey(NivelInstanciaWorkflow,on_delete=models.PROTECT); solicitada_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="correcciones_solicitadas")
    comentario=models.TextField(); estado=models.CharField(max_length=12,choices=ESTADOS,default="ABIERTA"); creada_en=models.DateTimeField(auto_now_add=True); atendida_en=models.DateTimeField(null=True,blank=True)
    atendida_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True,related_name="correcciones_atendidas"); respuesta=models.TextField(blank=True)
    version_documento_anterior=models.CharField(max_length=80,blank=True); version_documento_nueva=models.CharField(max_length=80,blank=True)
