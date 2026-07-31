from copy import deepcopy
import json
from datetime import timedelta
from math import floor
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from core.application.event_bus import event_bus
from core.domain.rules import validate_safe_payload
from workflow.domain.adapters import adapter_registry
from workflow.domain.conditions import rule_matches
from workflow.domain.events import *
from workflow.domain.exceptions import *
from workflow.models import *

def _perm(ctx,code):
    if not ctx.usuario or not ctx.usuario.has_perm(f"workflow.{code}"): raise PermissionDenied(f"Se requiere workflow.{code}.")
def _audit(ctx,obj,description,before=None,after=None):
    registrar_evento(empresa=ctx.empresa,usuario=ctx.usuario,request=ctx.request,objeto=obj,modulo="workflow",accion=EventoAuditoria.Accion.OTRO,descripcion=description,datos_anteriores=before,datos_nuevos=after)
def _event(ctx,cls,obj,suffix,payload=None):
    base={"empresa_id":ctx.empresa.pk,"schema_version":1,**(payload or {})};validate_safe_payload(base)
    return event_bus.publish(cls(empresa_id=ctx.empresa.pk,usuario_id=getattr(ctx.usuario,"pk",None),agregado_tipo=f"workflow.{obj.__class__.__name__}",agregado_id=str(obj.pk),referencia=ctx.referencia,clave_idempotente=ctx.clave_idempotente or f"workflow:{suffix}:{obj.pk}:{uuid4().hex}",payload=base))

@transaction.atomic
def crear_regla(*,context,datos):
    _perm(context,"add_reglaaprobacion");obj=ReglaAprobacion(empresa=context.empresa,creado_por=context.usuario,actualizado_por=context.usuario,**datos);obj.full_clean();obj.save();_audit(context,obj,"Regla de workflow creada.",after={"codigo":obj.codigo,"version":obj.version});_event(context,ReglaWorkflowCreada,obj,"regla-creada",{"regla_id":obj.pk,"regla_version":obj.version});return obj
@transaction.atomic
def versionar_regla(*,context,regla_id):
    _perm(context,"versionar_regla_aprobacion");old=ReglaAprobacion.objects.select_for_update().get(pk=regla_id,empresa=context.empresa)
    fields=[f.name for f in ReglaAprobacion._meta.fields if f.name not in {"id","version","estado","creado_en","actualizado_en","creado_por","actualizado_por"}]
    data={f:getattr(old,f) for f in fields};data.update(version=old.version+1,estado="BORRADOR",creado_por=context.usuario,actualizado_por=context.usuario)
    new=ReglaAprobacion.objects.create(**data)
    for n in old.niveles.prefetch_related("asignadores"):
        nd={f.name:getattr(n,f.name) for f in NivelAprobacion._meta.fields if f.name not in {"id","regla","creado_en","actualizado_en"}};nn=NivelAprobacion.objects.create(regla=new,**nd)
        for a in n.asignadores.all():
            ad={f.name:getattr(a,f.name) for f in AsignadorNivel._meta.fields if f.name not in {"id","nivel","creado_en","actualizado_en"}};AsignadorNivel.objects.create(nivel=nn,**ad)
    for c in old.condiciones.all():
        cd={f.name:getattr(c,f.name) for f in CondicionReglaAprobacion._meta.fields if f.name not in {"id","regla","creado_en","actualizado_en"}};CondicionReglaAprobacion.objects.create(regla=new,**cd)
    _audit(context,new,"Nueva versión de regla creada.",after={"origen":old.pk,"version":new.version});_event(context,ReglaWorkflowVersionada,new,"versionada",{"regla_id":new.pk,"regla_version":new.version});return new

def validar_regla_objeto(regla):
    errors=[]
    if not regla.niveles.filter(activo=True).exists(): errors.append("La regla no tiene niveles activos.")
    for n in regla.niveles.filter(activo=True):
        if not n.asignadores.filter(activo=True).exists(): errors.append(f"El nivel {n.numero} no tiene asignadores.")
    return errors
@transaction.atomic
def agregar_condicion(*,context,regla_id,datos):
    _perm(context,"add_condicionreglaaprobacion");r=ReglaAprobacion.objects.get(pk=regla_id,empresa=context.empresa,estado="BORRADOR");obj=CondicionReglaAprobacion(empresa=context.empresa,regla=r,**datos);obj.full_clean();obj.save();_audit(context,obj,"Condición agregada.");return obj
@transaction.atomic
def agregar_nivel(*,context,regla_id,datos):
    _perm(context,"add_nivelaprobacion");r=ReglaAprobacion.objects.get(pk=regla_id,empresa=context.empresa,estado="BORRADOR");obj=NivelAprobacion(empresa=context.empresa,regla=r,**datos);obj.full_clean();obj.save();_audit(context,obj,"Nivel agregado.");return obj
@transaction.atomic
def configurar_asignador(*,context,nivel_id,datos):
    _perm(context,"gestionar_asignadores_workflow");n=NivelAprobacion.objects.get(pk=nivel_id,empresa=context.empresa,regla__estado="BORRADOR");obj=AsignadorNivel(empresa=context.empresa,nivel=n,**datos);obj.full_clean();obj.save();_audit(context,obj,"Asignador configurado.");return obj
def validar_regla(*,context,regla_id): _perm(context,"validar_regla_aprobacion");return validar_regla_objeto(ReglaAprobacion.objects.get(pk=regla_id,empresa=context.empresa))
@transaction.atomic
def activar_regla(*,context,regla_id):
    _perm(context,"activar_regla_aprobacion");r=ReglaAprobacion.objects.select_for_update().get(pk=regla_id,empresa=context.empresa)
    errors=validar_regla_objeto(r)
    if errors: raise WorkflowConfigurationError(errors)
    r.estado="ACTIVA";r.activa=True;r.actualizado_por=context.usuario;r.full_clean();r.save();_audit(context,r,"Regla activada.",after={"estado":"ACTIVA"});_event(context,ReglaWorkflowActivada,r,"activada",{"regla_id":r.pk,"regla_version":r.version});return r
@transaction.atomic
def inactivar_regla(*,context,regla_id):
    _perm(context,"change_reglaaprobacion");r=ReglaAprobacion.objects.select_for_update().get(pk=regla_id,empresa=context.empresa);r.estado="INACTIVA";r.activa=False;r.save(update_fields=["estado","activa","actualizado_en"]);return r
@transaction.atomic
def retirar_regla(*,context,regla_id):
    _perm(context,"retirar_regla_aprobacion");r=ReglaAprobacion.objects.select_for_update().get(pk=regla_id,empresa=context.empresa);r.estado="RETIRADA";r.activa=False;r.save(update_fields=["estado","activa","actualizado_en"]);_event(context,ReglaWorkflowRetirada,r,"retirada",{"regla_id":r.pk});return r
publicar_regla=activar_regla

def seleccionar_regla_aplicable(*,empresa,dominio,tipo_documento,contexto,allowed_fields,fecha=None):
    fecha=fecha or timezone.localdate();qs=ReglaAprobacion.objects.filter(empresa=empresa,dominio=dominio,tipo_documento=tipo_documento,estado="ACTIVA",activa=True).filter(Q(vigente_desde__isnull=True)|Q(vigente_desde__lte=fecha)).filter(Q(vigente_hasta__isnull=True)|Q(vigente_hasta__gte=fecha))
    matched=[r for r in qs.prefetch_related("condiciones") if rule_matches(r,contexto,allowed_fields)]
    specific=[r for r in matched if r.condiciones.filter(activa=True).exists()]
    pool=specific or [r for r in matched if r.es_predeterminada]
    if not pool: raise WorkflowConfigurationError("No existe una regla aplicable.")
    pool.sort(key=lambda r:(r.prioridad,r.condiciones.filter(activa=True).count(),r.version),reverse=True)
    if len(pool)>1 and (pool[0].prioridad,pool[0].condiciones.count(),pool[0].version)==(pool[1].prioridad,pool[1].condiciones.count(),pool[1].version): raise WorkflowAmbiguityError("Existen reglas aplicables con igual prioridad y especificidad.")
    return pool[0]

def _users_empresa(empresa): return get_user_model().objects.filter(Q(empresa_principal=empresa)|Q(membresias_workflow__empresa=empresa,membresias_workflow__activo=True),is_active=True).distinct()
def resolver_asignaciones(*,nivel,document,adapter,context):
    users=[]
    for source in NivelAprobacion.objects.get(pk=nivel.numero if False else nivel._source_id).asignadores.filter(activo=True):
        candidates=[]
        if source.tipo=="USUARIO" and source.usuario: candidates=[source.usuario]
        elif source.tipo=="GRUPO" and source.grupo: candidates=list(_users_empresa(context.empresa).filter(groups=source.grupo))
        elif source.tipo=="PERMISO": candidates=[u for u in _users_empresa(context.empresa) if u.has_perm(source.permiso_codename if "." in source.permiso_codename else f"workflow.{source.permiso_codename}")]
        elif source.tipo=="DINAMICO_ADAPTADOR": candidates=list(adapter.resolve_dynamic_assignees(document,source.parametro))
        else: candidates=list(adapter.resolve_dynamic_assignees(document,source.tipo))
        valid_ids=set(_users_empresa(context.empresa).values_list("pk",flat=True));candidates=[u for u in candidates if u.pk in valid_ids]
        if source.obligatorio and not candidates: raise WorkflowAssignmentError(f"El asignador {source.pk} no resolvió usuarios.")
        users.extend((u,source) for u in candidates)
    seen=set();created=[]
    for user,source in users:
        if user.pk in seen: continue
        seen.add(user.pk);created.append(AsignacionAprobacion.objects.create(empresa=context.empresa,instancia=nivel.instancia,nivel_instancia=nivel,usuario=user,origen_tipo=source.tipo,origen_referencia=str(source.pk),asignado_por=context.usuario))
    if not created: raise WorkflowAssignmentError("El nivel no tiene aprobadores efectivos.")
    for item in created:
        _audit(context,item,"Aprobador asignado.",after={"instancia_id":nivel.instancia_id,"nivel":nivel.numero,"usuario_id":item.usuario_id,"origen":item.origen_tipo})
        _event(context,AprobadorAsignado,nivel.instancia,f"asignado:{item.pk}",{"instancia_id":nivel.instancia_id,"regla_id":nivel.instancia.regla_id,"regla_version":nivel.instancia.regla_version,"nivel":nivel.numero,"usuario_id":item.usuario_id})
    return created

@transaction.atomic
def iniciar_workflow(*,document,adapter_key,context,idempotency_key,dominio,tipo_documento,proposito="APROBACION"):
    _perm(context,"iniciar_workflow")
    if not idempotency_key: raise WorkflowError("La clave idempotente es obligatoria.")
    adapter=adapter_registry.get(adapter_key);empresa=adapter.get_empresa(document)
    if empresa.pk!=context.empresa.pk: raise WorkflowError("El documento pertenece a otra empresa.")
    existing=InstanciaWorkflow.objects.filter(empresa=empresa,idempotency_key=idempotency_key).first()
    if existing:return existing
    if not adapter.can_start(document): raise WorkflowStateError("El documento no puede iniciar aprobación.")
    data=adapter.build_context(document);data_json=json.loads(json.dumps(data,cls=DjangoJSONEncoder));validate_safe_payload(data_json);rule=seleccionar_regla_aplicable(empresa=empresa,dominio=dominio,tipo_documento=tipo_documento,contexto=data,allowed_fields=adapter.allowed_context_fields)
    ct=ContentType.objects.get_for_model(document);snap=adapter.snapshot(document);snap["adapter_key"]=adapter_key;snap_json=json.loads(json.dumps(snap,cls=DjangoJSONEncoder));validate_safe_payload(snap_json)
    inst=InstanciaWorkflow.objects.create(empresa=empresa,regla=rule,regla_version=rule.version,content_type=ct,object_id=document.pk,referencia_externa=str(snap.get("referencia","")),proposito=proposito,dominio=dominio,tipo_documento=tipo_documento,estado="INICIADA",solicitante=adapter.get_solicitante(document),iniciada_por=context.usuario,contexto_snapshot=data_json,documento_snapshot=snap_json,idempotency_key=idempotency_key)
    ronda=RondaWorkflow.objects.create(empresa=empresa,instancia=inst,numero=1,motivo="Inicio",iniciada_por=context.usuario)
    sources={n.numero:n.pk for n in rule.niveles.filter(activo=True).order_by("orden","numero")}
    levels=[]
    for n in rule.niveles.filter(activo=True).order_by("orden","numero"):
        due=None
        if n.dias_objetivo is not None or n.horas_objetivo is not None: due=timezone.now()+timedelta(days=n.dias_objetivo or 0,hours=n.horas_objetivo or 0)
        level=NivelInstanciaWorkflow.objects.create(empresa=empresa,instancia=inst,ronda=ronda,numero=n.numero,nombre_snapshot=n.nombre,estrategia_decision=n.estrategia_decision,minimo_aprobaciones=n.minimo_aprobaciones,porcentaje_mayoria=n.porcentaje_mayoria,rechazo_finaliza=n.rechazo_finaliza,permite_devolucion=n.permite_devolucion,requiere_comentario_aprobacion=n.requiere_comentario_aprobacion,requiere_comentario_rechazo=n.requiere_comentario_rechazo,requiere_comentario_devolucion=n.requiere_comentario_devolucion,orden=n.orden,vencimiento_objetivo=due)
        level._source_id=n.pk;levels.append(level)
    if not levels: raise WorkflowConfigurationError("La regla no tiene niveles.")
    first=levels[0];first.estado="ACTIVO";first.activado_en=timezone.now();first.save(update_fields=["estado","activado_en","actualizado_en"]);inst.estado="EN_APROBACION";inst.nivel_actual=first.numero;inst.save(update_fields=["estado","nivel_actual","actualizado_en"]);resolver_asignaciones(nivel=first,document=document,adapter=adapter,context=context)
    _audit(context,inst,"Workflow iniciado.",after={"regla_id":rule.pk,"version":rule.version,"referencia":inst.referencia_externa});_event(context,WorkflowIniciado,inst,"iniciado",{"instancia_id":inst.pk,"regla_id":rule.pk,"regla_version":rule.version,"dominio":dominio,"tipo_documento":tipo_documento});_event(context,NivelWorkflowActivado,inst,f"nivel:{first.pk}",{"instancia_id":inst.pk,"regla_id":rule.pk,"regla_version":rule.version,"nivel":first.numero,"estado_nuevo":"ACTIVO"});adapter.on_state_change(document,"EN_APROBACION");return inst

def _level_approved(level):
    assignments=level.asignaciones.filter(activa=True,revocada=False).count();approvals=level.decisiones.filter(decision="APROBAR").count();votes=level.decisiones.exclude(decision="ABSTENERSE").count()
    return {"CUALQUIERA":approvals>=1,"UNANIMIDAD":assignments>0 and approvals==assignments,"TODOS_LOS_ASIGNADOS":assignments>0 and approvals==assignments,"MINIMO_VOTOS":approvals>=level.minimo_aprobaciones,"MAYORIA_SIMPLE":assignments>0 and approvals>assignments/2,"PRIMERA_RESPUESTA":votes>=1 and approvals>=1}[level.estrategia_decision]

@transaction.atomic
def registrar_decision(*,context,instancia_id,decision,comentario,idempotency_key):
    perm={"APROBAR":"aprobar_workflow","RECHAZAR":"rechazar_workflow","DEVOLVER":"devolver_workflow","ABSTENERSE":"aprobar_workflow"}[decision];_perm(context,perm)
    if not idempotency_key: raise WorkflowError("La clave idempotente es obligatoria.")
    existing=DecisionAprobacion.objects.filter(empresa=context.empresa,idempotency_key=idempotency_key).first()
    if existing:return existing
    inst=InstanciaWorkflow.objects.select_for_update().get(pk=instancia_id,empresa=context.empresa);level=NivelInstanciaWorkflow.objects.select_for_update().get(instancia=inst,estado="ACTIVO");ronda=RondaWorkflow.objects.select_for_update().get(instancia=inst,estado="ACTIVA")
    assignment=AsignacionAprobacion.objects.select_for_update().filter(nivel_instancia=level,usuario=context.usuario,activa=True,revocada=False).first()
    represented=None
    if not assignment:
        assignment=AsignacionAprobacion.objects.select_for_update().filter(nivel_instancia=level,usuario_titular=context.usuario,activa=True,revocada=False).first()
    if not assignment: raise WorkflowAssignmentError("El usuario no está asignado al nivel activo.")
    if context.usuario.pk==inst.solicitante_id and not inst.regla.permite_autoaprobacion: raise WorkflowAssignmentError("La autoaprobación no está permitida.")
    required=(decision=="APROBAR" and level.requiere_comentario_aprobacion) or (decision=="RECHAZAR" and level.requiere_comentario_rechazo) or (decision=="DEVOLVER" and level.requiere_comentario_devolucion)
    if required and not comentario.strip(): raise WorkflowError("El comentario es obligatorio.")
    if decision=="DEVOLVER" and not level.permite_devolucion: raise WorkflowStateError("El nivel no permite devolución.")
    d=DecisionAprobacion(empresa=context.empresa,instancia=inst,ronda=ronda,nivel_instancia=level,asignacion=assignment,usuario_efectivo=context.usuario,usuario_representado=represented,decision=decision,comentario=comentario,idempotency_key=idempotency_key,ip_address=context.ip,user_agent=context.user_agent);d.save()
    if decision=="RECHAZAR" and level.rechazo_finaliza: level.estado="RECHAZADO";inst.estado="RECHAZADA";inst.resultado="RECHAZADA";inst.motivo_final=comentario;inst.finalizada_en=timezone.now()
    elif decision=="DEVOLVER": level.estado="DEVUELTO";inst.estado="DEVUELTA";SolicitudCorreccionWorkflow.objects.create(empresa=context.empresa,instancia=inst,nivel_instancia=level,solicitada_por=context.usuario,comentario=comentario)
    elif decision in {"APROBAR","ABSTENERSE"} and _level_approved(level):
        level.estado="APROBADO";next_level=inst.niveles_instancia.filter(ronda=ronda,estado="PENDIENTE").order_by("orden","numero").first()
        if next_level:
            next_level.estado="ACTIVO";next_level.activado_en=timezone.now();next_level.save(update_fields=["estado","activado_en","actualizado_en"]);inst.nivel_actual=next_level.numero
            adapter=adapter_registry.get(inst.documento_snapshot.get("adapter_key","")) if inst.documento_snapshot.get("adapter_key") else None
            if adapter:
                document=inst.content_type.get_object_for_this_type(pk=inst.object_id);next_level._source_id=inst.regla.niveles.get(numero=next_level.numero).pk;resolver_asignaciones(nivel=next_level,document=document,adapter=adapter,context=context)
        else: inst.estado="APROBADA";inst.resultado="APROBADA";inst.finalizada_en=timezone.now();ronda.estado="FINALIZADA";ronda.finalizada_en=timezone.now();ronda.save(update_fields=["estado","finalizada_en"])
    level.completado_en=timezone.now() if level.estado!="ACTIVO" else None;level.resultado=level.estado;level.save(update_fields=["estado","completado_en","resultado","actualizado_en"]);inst.save();_audit(context,d,"Decisión de workflow registrada.",after={"decision":decision,"instancia_id":inst.pk,"nivel":level.numero});_event(context,DecisionWorkflowRegistrada,inst,f"decision:{d.pk}",{"instancia_id":inst.pk,"regla_id":inst.regla_id,"regla_version":inst.regla_version,"nivel":level.numero,"estado_nuevo":inst.estado})
    key=inst.documento_snapshot.get("adapter_key")
    if key:
        adapter=adapter_registry.get(key);document=inst.content_type.get_object_for_this_type(pk=inst.object_id);adapter.on_state_change(document,inst.estado)
        if inst.estado in {"APROBADA","RECHAZADA"}:adapter.on_final_result(document,inst.resultado)
    event_cls={"APROBADA":WorkflowAprobado,"RECHAZADA":WorkflowRechazado,"DEVUELTA":WorkflowDevuelto}.get(inst.estado)
    if event_cls:_event(context,event_cls,inst,f"resultado:{d.pk}",{"instancia_id":inst.pk,"regla_id":inst.regla_id,"regla_version":inst.regla_version,"nivel":level.numero,"estado_nuevo":inst.estado})
    elif level.estado=="APROBADO":_event(context,NivelWorkflowAprobado,inst,f"nivel-aprobado:{level.pk}",{"instancia_id":inst.pk,"regla_id":inst.regla_id,"regla_version":inst.regla_version,"nivel":level.numero})
    return d

def aprobar(**kwargs): return registrar_decision(decision="APROBAR",**kwargs)
def rechazar(**kwargs): return registrar_decision(decision="RECHAZAR",**kwargs)
def devolver(**kwargs): return registrar_decision(decision="DEVOLVER",**kwargs)
def abstenerse(**kwargs): return registrar_decision(decision="ABSTENERSE",**kwargs)

@transaction.atomic
def cancelar_workflow(*,context,instancia_id,motivo):
    _perm(context,"cancelar_workflow");inst=InstanciaWorkflow.objects.select_for_update().get(pk=instancia_id,empresa=context.empresa)
    if inst.estado=="APROBADA": raise WorkflowStateError("Un workflow aprobado no puede cancelarse.")
    if not motivo.strip(): raise WorkflowError("El motivo es obligatorio.")
    inst.estado="CANCELADA";inst.motivo_final=motivo;inst.finalizada_en=timezone.now();inst.save();inst.niveles_instancia.filter(estado__in=["ACTIVO","PENDIENTE"]).update(estado="CANCELADO");_event(context,WorkflowCancelado,inst,"cancelado",{"instancia_id":inst.pk,"motivo":motivo});return inst

@transaction.atomic
def marcar_correccion_atendida(*,context,solicitud_id,respuesta,version_nueva):
    s=SolicitudCorreccionWorkflow.objects.select_for_update().get(pk=solicitud_id,empresa=context.empresa,instancia__solicitante=context.usuario,estado="ABIERTA");s.estado="ATENDIDA";s.respuesta=respuesta;s.version_documento_nueva=version_nueva;s.atendida_por=context.usuario;s.atendida_en=timezone.now();s.save();return s

@transaction.atomic
def reabrir_workflow(*,context,instancia_id,motivo,modo="CONTINUAR_DESDE_NIVEL"):
    _perm(context,"reabrir_workflow");inst=InstanciaWorkflow.objects.select_for_update().get(pk=instancia_id,empresa=context.empresa)
    if not inst.regla.permite_reapertura or inst.estado not in {"DEVUELTA","RECHAZADA"}: raise WorkflowStateError("La instancia no admite reapertura.")
    old=RondaWorkflow.objects.select_for_update().get(instancia=inst,estado="ACTIVA");old.estado="FINALIZADA";old.finalizada_en=timezone.now();old.save()
    ronda=RondaWorkflow.objects.create(empresa=context.empresa,instancia=inst,numero=old.numero+1,motivo=motivo,iniciada_por=context.usuario)
    source=list(inst.regla.niveles.filter(activo=True).order_by("orden","numero"));start=source[0].numero if modo=="REINICIAR_DESDE_PRIMERO" else inst.nivel_actual
    for n in source:
        NivelInstanciaWorkflow.objects.create(empresa=context.empresa,instancia=inst,ronda=ronda,numero=n.numero,nombre_snapshot=n.nombre,estrategia_decision=n.estrategia_decision,minimo_aprobaciones=n.minimo_aprobaciones,porcentaje_mayoria=n.porcentaje_mayoria,rechazo_finaliza=n.rechazo_finaliza,permite_devolucion=n.permite_devolucion,requiere_comentario_aprobacion=n.requiere_comentario_aprobacion,requiere_comentario_rechazo=n.requiere_comentario_rechazo,requiere_comentario_devolucion=n.requiere_comentario_devolucion,estado="ACTIVO" if n.numero==start else ("OMITIDO" if n.numero<start else "PENDIENTE"),activado_en=timezone.now() if n.numero==start else None,orden=n.orden)
    inst.estado="EN_APROBACION";inst.nivel_actual=start;inst.finalizada_en=None;inst.save()
    active=NivelInstanciaWorkflow.objects.get(instancia=inst,ronda=ronda,estado="ACTIVO");key=inst.documento_snapshot.get("adapter_key")
    if not key: raise WorkflowConfigurationError("La instancia no conserva un adaptador registrado.")
    adapter=adapter_registry.get(key);document=inst.content_type.get_object_for_this_type(pk=inst.object_id);active._source_id=inst.regla.niveles.get(numero=start).pk;resolver_asignaciones(nivel=active,document=document,adapter=adapter,context=context);adapter.on_state_change(document,"EN_APROBACION")
    _event(context,WorkflowReabierto,inst,"reabierto",{"instancia_id":inst.pk,"ronda":ronda.numero});return inst

@transaction.atomic
def reasignar_aprobador(*,context,asignacion_id,nuevo_usuario,motivo):
    _perm(context,"reasignar_workflow");old=AsignacionAprobacion.objects.select_for_update().get(pk=asignacion_id,empresa=context.empresa,activa=True,revocada=False)
    if nuevo_usuario.pk not in set(_users_empresa(context.empresa).values_list("pk",flat=True)): raise WorkflowAssignmentError("El nuevo aprobador no pertenece a la empresa o está inactivo.")
    old.activa=False;old.revocada=True;old.motivo_revocacion=motivo;old.save();new=AsignacionAprobacion.objects.create(empresa=context.empresa,instancia=old.instancia,nivel_instancia=old.nivel_instancia,usuario=nuevo_usuario,origen_tipo="REASIGNACION",origen_referencia=str(old.pk),asignado_por=context.usuario);_event(context,AprobadorReasignado,old.instancia,f"reasignar:{new.pk}",{"instancia_id":old.instancia_id,"nivel":old.nivel_instancia.numero});return new

@transaction.atomic
def aplicar_suplencia(*,context,asignacion_id):
    assignment=AsignacionAprobacion.objects.select_for_update().get(pk=asignacion_id,empresa=context.empresa,activa=True,revocada=False);now=timezone.now();inst=assignment.instancia
    sub=SuplenciaAprobador.objects.filter(empresa=context.empresa,titular=assignment.usuario,activa=True,vigente_desde__lte=now,vigente_hasta__gte=now).filter(Q(alcance="GLOBAL")|Q(alcance="DOMINIO",dominio=inst.dominio)|Q(alcance="TIPO_DOCUMENTO",tipo_documento=inst.tipo_documento)|Q(alcance="REGLA",regla=inst.regla)).first()
    if not sub:return None
    assignment.activa=False;assignment.save(update_fields=["activa","actualizado_en"])
    obj,_=AsignacionAprobacion.objects.get_or_create(empresa=context.empresa,instancia=inst,nivel_instancia=assignment.nivel_instancia,usuario=sub.suplente,defaults={"usuario_titular":assignment.usuario,"origen_tipo":"SUPLENCIA","origen_referencia":str(sub.pk),"es_titular":False,"es_suplente":True,"asignado_por":context.usuario})
    return obj

@transaction.atomic
def crear_suplencia(*,context,datos):
    _perm(context,"gestionar_suplencias_workflow");obj=SuplenciaAprobador(empresa=context.empresa,creada_por=context.usuario,**datos);obj.full_clean();obj.save();_audit(context,obj,"Suplencia creada.",after={"titular_id":obj.titular_id,"suplente_id":obj.suplente_id,"alcance":obj.alcance});_event(context,SuplenciaWorkflowCreada,obj,"suplencia-creada",{"titular_id":obj.titular_id,"suplente_id":obj.suplente_id});return obj
@transaction.atomic
def revocar_suplencia(*,context,suplencia_id,motivo):
    _perm(context,"gestionar_suplencias_workflow");obj=SuplenciaAprobador.objects.select_for_update().get(pk=suplencia_id,empresa=context.empresa,activa=True);obj.activa=False;obj.save(update_fields=["activa","actualizado_en"]);_audit(context,obj,"Suplencia revocada.",after={"motivo":motivo});_event(context,SuplenciaWorkflowRevocada,obj,"suplencia-revocada",{"motivo":motivo});return obj

devolver_para_correccion=devolver

def obtener_tareas_usuario(*,empresa,usuario): return AsignacionAprobacion.objects.filter(empresa=empresa,usuario=usuario,activa=True,revocada=False,nivel_instancia__estado="ACTIVO",instancia__estado="EN_APROBACION").select_related("instancia","nivel_instancia")
def obtener_historial(*,empresa,instancia_id): return DecisionAprobacion.objects.filter(empresa=empresa,instancia_id=instancia_id).select_related("usuario_efectivo","usuario_representado","nivel_instancia").order_by("creada_en")
def obtener_estado_workflow(*,empresa,content_type,object_id,proposito="APROBACION"): return InstanciaWorkflow.objects.filter(empresa=empresa,content_type=content_type,object_id=object_id,proposito=proposito).order_by("-creado_en").first()
def obtener_pendientes_documento(*,empresa,content_type,object_id): return InstanciaWorkflow.objects.filter(empresa=empresa,content_type=content_type,object_id=object_id,estado__in=InstanciaWorkflow.ACTIVOS)
def obtener_mis_aprobaciones(*,empresa,usuario): return obtener_tareas_usuario(empresa=empresa,usuario=usuario)
