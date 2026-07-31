from dataclasses import dataclass,field,replace
from decimal import Decimal
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Sum
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from core.application.numbering import obtener_siguiente_numero
from core.application.event_bus import event_bus
from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from compras.domain.expedientes_rfq_events import *
from compras.models import *

@dataclass
class ResultadoValidacionRFQ:
    errores:list=field(default_factory=list);advertencias:list=field(default_factory=list);bloqueantes:list=field(default_factory=list);recomendaciones:list=field(default_factory=list)
    @property
    def valido(self):return not self.errores and not self.bloqueantes

def _perm(c,p):
    if not c.usuario or not c.usuario.has_perm(f"compras.{p}"):raise PermissionDenied(f"Se requiere compras.{p}.")
def _lock_exp(c,pk):return ExpedienteCompra.objects.select_for_update().get(pk=pk,empresa=c.empresa)
def _lock_rfq(c,pk):return ProcesoRFQ.objects.select_for_update().get(pk=pk,empresa=c.empresa)
def _numctx(c,tipo):return replace(c,clave_idempotente=f"{c.clave_idempotente or c.identificador_solicitud}:{tipo}"[:180])
def _audit(c,o,text,before=None,after=None):registrar_evento(empresa=c.empresa,usuario=c.usuario,request=c.request,objeto=o,modulo="compras",accion=EventoAuditoria.Accion.OTRO,descripcion=text,datos_anteriores=before,datos_nuevos=after)
def _emit(c,cls,o,suffix,extra=None):
    payload={"empresa_id":c.empresa.pk,"objeto_id":o.pk,"referencia":getattr(o,"numero",str(o.pk)),"actor_id":getattr(c.usuario,"pk",None),"fecha":timezone.now().isoformat(),"schema_version":1,**(extra or {})}
    return event_bus.publish(cls(empresa_id=c.empresa.pk,usuario_id=getattr(c.usuario,"pk",None),agregado_tipo=f"compras.{o.__class__.__name__}",agregado_id=str(o.pk),referencia=payload["referencia"],clave_idempotente=f"{c.clave_idempotente or c.identificador_solicitud}:{suffix}:{o.pk}"[:180],payload=payload))

def registrar_operacion_documental_p2p(*,documento,accion,usuario=None,request=None,emitir=True):
    objeto=documento.content_object
    if not isinstance(objeto,(ExpedienteCompra,ProcesoRFQ,InvitacionProveedorRFQ)):return None
    expediente=objeto if isinstance(objeto,ExpedienteCompra) else objeto.expediente if isinstance(objeto,ProcesoRFQ) else objeto.rfq.expediente
    rfq=objeto if isinstance(objeto,ProcesoRFQ) else objeto.rfq if isinstance(objeto,InvitacionProveedorRFQ) else None
    metadata={"expediente_id":expediente.pk,"rfq_id":getattr(rfq,"pk",None),"documento_id":documento.pk,"tipo_documento":getattr(documento.tipo_documento,"codigo","") if documento.tipo_documento_id else "","accion":accion,"version_documento":documento.version}
    registrar_evento(empresa=documento.empresa,usuario=usuario,request=request,objeto=objeto,modulo="compras",accion=EventoAuditoria.Accion.OTRO,descripcion=f"Documento P2P: {accion}.",datos_nuevos=metadata)
    if not emitir or rfq is None:return None
    from core.application.operation_context import OperationContext
    ctx=OperationContext(empresa=documento.empresa,usuario=usuario,request=request,clave_idempotente=f"doc:{documento.pk}:v{documento.version}:{accion}")
    return _emit(ctx,DocumentoRFQActualizado,rfq,f"documento-{documento.pk}-{accion}",{**metadata,"timestamp":timezone.now().isoformat()})
EXP_EVENTS={"ABIERTO":ExpedienteCompraAbierto,"CANCELADA":ExpedienteCompraCancelado,"DESIERTA":ExpedienteCompraDeclaradoDesierto}
RFQ_EVENTS={"EN_REVISION":RFQEnviadaRevision,"BORRADOR":RFQDevueltaBorrador,"PUBLICADA":RFQPublicada,"ABIERTA":RFQAbierta,"EXTENDIDA":RFQPlazoExtendido,"CERRADA":RFQCerrada,"CANCELADA":RFQCancelada}
def _hist_exp(c,o,a,n,comentario=""):
    HistorialEstadoExpedienteCompra.objects.create(empresa=c.empresa,expediente=o,estado_anterior=a,estado_nuevo=n,usuario=c.usuario,comentario=comentario);_audit(c,o,f"Expediente: {a or 'INICIAL'} → {n}.",{"estado":a},{"estado":n,"motivo":comentario[:200]});cls=EXP_EVENTS.get(n)
    if cls:_emit(c,cls,o,f"estado-{n}",{"estado_anterior":a,"estado_nuevo":n})
def _hist_rfq(c,o,a,n,comentario=""):
    HistorialEstadoRFQ.objects.create(empresa=c.empresa,rfq=o,estado_anterior=a,estado_nuevo=n,usuario=c.usuario,comentario=comentario);_audit(c,o,f"RFQ: {a or 'INICIAL'} → {n}.",{"estado":a},{"estado":n,"motivo":comentario[:200]});cls=RFQ_EVENTS.get(n)
    if cls:_emit(c,cls,o,f"estado-{n}",{"estado_anterior":a,"estado_nuevo":n})

@transaction.atomic
def crear_expediente_desde_solicitud(*,context,solicitud_id):
    _perm(context,"add_expedientecompra");s=SolicitudCompra.objects.select_for_update().get(pk=solicitud_id,empresa=context.empresa,estado="APROBADA")
    prior=SolicitudExpedienteCompra.objects.filter(empresa=context.empresa,solicitud=s,activa=True).select_related("expediente").first()
    if prior:return prior.expediente
    num=obtener_siguiente_numero(empresa=context.empresa,tipo_documento="EXP",prefijo="EXP",longitud=6,context=_numctx(context,"EXP"))
    o=ExpedienteCompra(empresa=context.empresa,numero=num,titulo=s.titulo,descripcion=s.justificacion,responsable=context.usuario,solicitante_principal=s.solicitante,centro_costo=s.centro_costo,tipo_compra=s.tipo_compra,prioridad=s.prioridad,moneda=s.moneda,presupuesto_estimado=s.total_estimado,monto_aprobado_solicitudes=s.total_estimado,creado_por=context.usuario,actualizado_por=context.usuario);o.full_clean();o.save();v=SolicitudExpedienteCompra.objects.create(empresa=context.empresa,expediente=o,solicitud=s,principal=True,monto_snapshot=s.total_estimado,moneda_snapshot=s.moneda.moneda.codigo,estado_snapshot=s.estado,vinculada_por=context.usuario);_hist_exp(context,o,"","BORRADOR","Creación desde solicitud");_emit(context,ExpedienteCompraCreado,o,"creado");_emit(context,SolicitudVinculadaAExpediente,o,f"vinculo-{v.pk}",{"solicitud_id":s.pk});return o

@transaction.atomic
def agregar_solicitud_a_expediente(*,context,expediente_id,solicitud_id,tipo_relacion="COMPLEMENTARIA"):
    _perm(context,"change_expedientecompra");e=_lock_exp(context,expediente_id);s=SolicitudCompra.objects.select_for_update().get(pk=solicitud_id,empresa=context.empresa,estado="APROBADA")
    if e.estado not in {"BORRADOR","ABIERTO","PREPARANDO_RFQ"}:raise ValidationError("El expediente no admite vínculos.")
    if s.moneda_id!=e.moneda_id:raise ValidationError("La moneda no coincide.")
    v,created=SolicitudExpedienteCompra.objects.get_or_create(empresa=context.empresa,solicitud=s,activa=True,defaults={"expediente":e,"tipo_relacion":tipo_relacion,"monto_snapshot":s.total_estimado,"moneda_snapshot":s.moneda.moneda.codigo,"estado_snapshot":s.estado,"vinculada_por":context.usuario})
    if v.expediente_id!=e.pk:raise ValidationError("La solicitud ya pertenece a otro expediente.")
    e.monto_aprobado_solicitudes=e.solicitudes_vinculadas.filter(activa=True).aggregate(v=Sum("monto_snapshot"))["v"] or 0;e.presupuesto_estimado=e.monto_aprobado_solicitudes;e.save();
    if created:_audit(context,e,"Solicitud vinculada.",after={"solicitud_id":s.pk});_emit(context,SolicitudVinculadaAExpediente,e,f"vinculo-{v.pk}",{"solicitud_id":s.pk})
    return v

@transaction.atomic
def retirar_solicitud_de_expediente(*,context,vinculo_id):
    v=SolicitudExpedienteCompra.objects.select_for_update().select_related("expediente").get(pk=vinculo_id,empresa=context.empresa,activa=True)
    if v.expediente.rfqs.exclude(estado="BORRADOR").exists():raise ValidationError("No se puede desvincular después de preparar RFQ.")
    v.activa=False;v.save(update_fields=["activa"]);_audit(context,v.expediente,"Solicitud retirada.",after={"solicitud_id":v.solicitud_id});_emit(context,SolicitudRetiradaDeExpediente,v.expediente,f"retirar-{v.pk}",{"solicitud_id":v.solicitud_id});return v

def _trans_exp(context,e,nuevo,motivo=""):
    old=e.estado;e.estado=nuevo
    if nuevo=="ABIERTO":e.fecha_apertura=timezone.now()
    if nuevo=="CANCELADA":e.motivo_cancelacion=motivo;e.fecha_cierre=timezone.now()
    e.save();_hist_exp(context,e,old,nuevo,motivo);return e
@transaction.atomic
def abrir_expediente(*,context,expediente_id):
    _perm(context,"abrir_expedientecompra");e=_lock_exp(context,expediente_id)
    if e.estado!="BORRADOR" or not e.solicitudes_vinculadas.filter(activa=True).exists():raise ValidationError("El expediente no puede abrirse.")
    return _trans_exp(context,e,"ABIERTO")
@transaction.atomic
def preparar_rfq(*,context,expediente_id):
    e=_lock_exp(context,expediente_id)
    if e.estado not in {"ABIERTO","PREPARANDO_RFQ"}:raise ValidationError("Estado inválido.")
    return _trans_exp(context,e,"PREPARANDO_RFQ")
@transaction.atomic
def cancelar_expediente(*,context,expediente_id,motivo):
    _perm(context,"cancelar_expedientecompra");e=_lock_exp(context,expediente_id)
    if not motivo.strip() or e.estado in {"CANCELADA","CERRADA"}:raise ValidationError("Cancelación inválida.")
    return _trans_exp(context,e,"CANCELADA",motivo)
@transaction.atomic
def declarar_expediente_desierto(*,context,expediente_id,motivo):
    _perm(context,"declarar_desierto_expedientecompra");e=_lock_exp(context,expediente_id)
    if not motivo.strip():raise ValidationError("El motivo es obligatorio.")
    return _trans_exp(context,e,"DESIERTA",motivo)

def calcular_salud_expediente(*,expediente):
    rfq=expediente.rfqs.order_by("-version").first();score=100;razones=[];rec=[]
    if not expediente.solicitudes_vinculadas.filter(activa=True).exists():score-=35;razones.append("Sin solicitudes aprobadas")
    if not rfq:score-=25;razones.append("Sin RFQ");rec.append("Preparar RFQ")
    else:
        inv=rfq.invitaciones.count();conf=rfq.invitaciones.filter(estado="CONFIRMADA").count()
        if inv<rfq.minimo_proveedores:score-=25;razones.append("Competencia insuficiente");rec.append("Invitar más proveedores")
        if rfq.fecha_limite<timezone.now() and rfq.estado in {"ABIERTA","EXTENDIDA"}:score-=25;razones.append("Plazo vencido")
        if inv and conf/inv<Decimal("0.5"):score-=10;razones.append("Baja confirmación")
        if rfq.estado=="EXTENDIDA":score-=5;razones.append("Plazo extendido")
    score=max(0,min(100,score));cat="EXCELENTE" if score>=90 else "BUENA" if score>=70 else "ATENCION" if score>=40 else "CRITICA";risk="BAJO" if score>=80 else "MEDIO" if score>=60 else "ALTO" if score>=30 else "CRITICO"
    return {"puntuacion":score,"categoria":cat,"razones":razones,"recomendaciones":rec,"componentes":{"solicitudes":expediente.solicitudes_vinculadas.filter(activa=True).count()},"fecha_calculo":timezone.now(),"version_formula":"1.0","nivel_riesgo":risk}
@transaction.atomic
def recalcular_salud_expediente(*,context,expediente_id):
    e=_lock_exp(context,expediente_id);r=calcular_salud_expediente(expediente=e);before=str(e.indice_salud);e.indice_salud=r["puntuacion"];e.nivel_riesgo=r["nivel_riesgo"];e.save(update_fields=["indice_salud","nivel_riesgo","fecha_actualizacion"]);_audit(context,e,"Salud recalculada.",{"indice":before},{"indice":r["puntuacion"],"riesgo":r["nivel_riesgo"]});_emit(context,SaludExpedienteRecalculada,e,"salud",{"indice":r["puntuacion"],"nivel_riesgo":r["nivel_riesgo"]});return r
def obtener_timeline_expediente(*,empresa,expediente_id):
    e=ExpedienteCompra.objects.get(pk=expediente_id,empresa=empresa);return {"expediente":e.historial.all(),"rfq":HistorialEstadoRFQ.objects.filter(empresa=empresa,rfq__expediente=e),"solicitudes":HistorialEstadoSolicitudCompra.objects.filter(empresa=empresa,solicitud__vinculos_expediente__expediente=e)}

@transaction.atomic
def actualizar_expediente_borrador(*,context,expediente_id,datos):
    _perm(context,"change_expedientecompra");e=_lock_exp(context,expediente_id)
    if e.estado not in {"BORRADOR","ABIERTO","PREPARANDO_RFQ"}:raise ValidationError("El expediente ya no admite edición.")
    allowed={"titulo","descripcion","responsable","centro_costo","tipo_compra","prioridad","observaciones"}
    for k,v in datos.items():
        if k in allowed:setattr(e,k,v)
    e.actualizado_por=context.usuario;e.full_clean();e.save();_audit(context,e,"Expediente actualizado.");return e

@transaction.atomic
def crear_rfq(*,context,expediente_id,datos):
    _perm(context,"add_procesorfq");e=_lock_exp(context,expediente_id)
    if e.estado not in {"ABIERTO","PREPARANDO_RFQ"}:raise ValidationError("El expediente no admite RFQ.")
    num=obtener_siguiente_numero(empresa=context.empresa,tipo_documento="RFQ",prefijo="RFQ",longitud=6,context=_numctx(context,"RFQ"));o=ProcesoRFQ(empresa=context.empresa,expediente=e,numero=num,creado_por=context.usuario,actualizado_por=context.usuario,moneda=e.moneda,**datos);o.full_clean();o.save();_hist_rfq(context,o,"","BORRADOR");_emit(context,RFQCreada,o,"creada");_trans_exp(context,e,"PREPARANDO_RFQ");return o
@transaction.atomic
def generar_lineas_desde_solicitudes(*,context,rfq_id):
    r=_lock_rfq(context,rfq_id)
    if r.estado!="BORRADOR":raise ValidationError("RFQ no editable.")
    count=0
    for line in DetalleSolicitudCompra.objects.filter(solicitud__vinculos_expediente__expediente=r.expediente,solicitud__vinculos_expediente__activa=True,activo=True).select_related("solicitud"):
        _,created=DetalleRFQ.objects.get_or_create(empresa=context.empresa,rfq=r,linea_origen_solicitud=line,defaults={"orden":r.lineas.count()+1,"tipo_linea":line.tipo_linea,"producto":line.producto,"codigo_snapshot":line.codigo_producto_snapshot or getattr(line.producto,"codigo","") or "","descripcion":line.descripcion,"especificacion_tecnica":line.especificacion_tecnica,"cantidad":line.cantidad,"unidad_medida":line.unidad_medida,"factor_conversion":line.factor_conversion,"cantidad_base":line.cantidad_base,"fecha_entrega_requerida":line.fecha_necesaria_linea or line.solicitud.fecha_necesaria,"almacen_destino":line.almacen_destino,"permite_equivalente":line.permite_equivalente,"marca_referencia":line.marca_referencia,"modelo_referencia":line.modelo_referencia});count+=int(created)
    return count
@transaction.atomic
def actualizar_linea_rfq(*,context,linea_id,datos):
    _perm(context,"change_procesorfq")
    linea=DetalleRFQ.objects.select_for_update().select_related("rfq").get(pk=linea_id,empresa=context.empresa)
    if linea.rfq.estado!="BORRADOR":raise ValidationError("Las líneas solo se editan en borrador.")
    for k,v in datos.items():setattr(linea,k,v)
    linea.full_clean();linea.save();_audit(context,linea.rfq,"Línea RFQ actualizada.",after={"linea_id":linea.pk});_emit(context,RFQActualizada,linea.rfq,f"linea-{linea.pk}",{"linea_id":linea.pk});return linea
@transaction.atomic
def actualizar_rfq_borrador(*,context,rfq_id,datos):
    _perm(context,"change_procesorfq");r=_lock_rfq(context,rfq_id)
    if r.estado!="BORRADOR":raise ValidationError("RFQ no editable.")
    for k,v in datos.items():setattr(r,k,v)
    r.full_clean();r.save();_audit(context,r,"RFQ actualizada.");_emit(context,RFQActualizada,r,"actualizada");return r
@transaction.atomic
def agregar_criterio(*,context,rfq_id,datos):
    _perm(context,"gestionar_criterios_rfq");r=_lock_rfq(context,rfq_id)
    if r.estado!="BORRADOR":raise ValidationError("RFQ no editable.")
    o=CriterioEvaluacionRFQ(empresa=context.empresa,rfq=r,**datos);o.full_clean();o.save();_audit(context,r,"Criterio agregado.",after={"criterio_id":o.pk,"codigo":o.codigo});return o
@transaction.atomic
def agregar_regla_participacion(*,context,rfq_id,datos):
    _perm(context,"gestionar_reglas_rfq");r=_lock_rfq(context,rfq_id)
    if r.estado!="BORRADOR":raise ValidationError("RFQ no editable.")
    o=ReglaParticipacionRFQ.objects.create(empresa=context.empresa,rfq=r,**datos);_audit(context,r,"Regla de participación agregada.",after={"regla_id":o.pk,"codigo":o.codigo});return o
@transaction.atomic
def agregar_proveedor_a_rfq(*,context,rfq_id,proveedor_id,contacto_id=None):
    _perm(context,"gestionar_proveedores_rfq");r=_lock_rfq(context,rfq_id);p=Proveedor.objects.get(pk=proveedor_id,empresa=context.empresa,estado="ACTIVO",bloqueado=False);contact=ContactoProveedor.objects.get(pk=contacto_id,empresa=context.empresa,proveedor=p,activo=True) if contacto_id else None;o,created=InvitacionProveedorRFQ.objects.get_or_create(empresa=context.empresa,rfq=r,proveedor=p,defaults={"contacto":contact,"creado_por":context.usuario,"actualizado_por":context.usuario});
    if created:_audit(context,r,"Proveedor invitado.",after={"proveedor_id":p.pk});_emit(context,ProveedorInvitadoRFQ,r,f"invitar-{o.pk}",{"invitacion_id":o.pk,"proveedor_id":p.pk})
    return o
@transaction.atomic
def retirar_proveedor_de_rfq(*,context,invitacion_id,motivo):
    _perm(context,"retirar_proveedor_rfq")
    i=InvitacionProveedorRFQ.objects.select_for_update().get(pk=invitacion_id,empresa=context.empresa)
    if not motivo.strip():raise ValidationError("Motivo obligatorio.")
    if i.estado not in {"BORRADOR","PENDIENTE_ENVIO","INVITADA","SIN_RESPUESTA"}:raise ValidationError("La invitación ya tiene un resultado final.")
    i.estado="RETIRADA";i.observaciones=motivo;i.save();_audit(context,i.rfq,"Proveedor retirado.",after={"invitacion_id":i.pk});_emit(context,ProveedorRetiradoRFQ,i.rfq,f"retirar-{i.pk}",{"invitacion_id":i.pk});return i

@transaction.atomic
def cambiar_contacto_invitacion_rfq(*,context,invitacion_id,contacto_id):
    _perm(context,"change_invitacionproveedorrfq");i=InvitacionProveedorRFQ.objects.select_for_update().get(pk=invitacion_id,empresa=context.empresa)
    if i.estado not in {"BORRADOR","PENDIENTE_ENVIO"}:raise ValidationError("El contacto no puede cambiarse después del envío.")
    contacto=ContactoProveedor.objects.get(pk=contacto_id,empresa=context.empresa,proveedor=i.proveedor,activo=True);before=i.contacto_id;i.contacto=contacto;i.actualizado_por=context.usuario;i.save();_audit(context,i.rfq,"Contacto de invitación actualizado.",{"contacto_id":before},{"contacto_id":contacto.pk,"invitacion_id":i.pk});_emit(context,RFQActualizada,i.rfq,f"contacto-{i.pk}",{"invitacion_id":i.pk});return i
def _invite_state(context,i,state,motivo=""):
    i=InvitacionProveedorRFQ.objects.select_for_update().get(pk=i,empresa=context.empresa)
    allowed={"INVITADA":{"BORRADOR","PENDIENTE_ENVIO"},"CONFIRMADA":{"INVITADA"},"DECLINADA":{"INVITADA"},"SIN_RESPUESTA":{"INVITADA"}}
    if i.estado not in allowed[state]:raise ValidationError("Transición de invitación inválida.")
    if state=="INVITADA":i.fecha_invitacion=timezone.now();i.invitada_por=context.usuario
    elif state=="CONFIRMADA":i.fecha_confirmacion=timezone.now()
    elif state=="DECLINADA":
        if not motivo.strip():raise ValidationError("Motivo obligatorio.")
        i.fecha_declinacion=timezone.now();i.motivo_declinacion=motivo
    old=i.estado;i.estado=state;i.save();_audit(context,i.rfq,f"Invitación: {old} → {state}.",{"estado":old},{"estado":state,"invitacion_id":i.pk});cls={"INVITADA":InvitacionRFQEnviada,"CONFIRMADA":ParticipacionRFQConfirmada,"DECLINADA":ParticipacionRFQDeclinada,"SIN_RESPUESTA":ParticipacionRFQSinRespuesta}[state];_emit(context,cls,i.rfq,f"invitacion-{i.pk}-{state}",{"invitacion_id":i.pk,"estado_anterior":old,"estado_nuevo":state});return i
@transaction.atomic
def marcar_invitacion_enviada(*,context,invitacion_id):_perm(context,"marcar_enviada_invitacionrfq");return _invite_state(context,invitacion_id,"INVITADA")
@transaction.atomic
def confirmar_participacion(*,context,invitacion_id):_perm(context,"confirmar_participacion_rfq");return _invite_state(context,invitacion_id,"CONFIRMADA")
@transaction.atomic
def declinar_participacion(*,context,invitacion_id,motivo):_perm(context,"registrar_declinacion_rfq");return _invite_state(context,invitacion_id,"DECLINADA",motivo)
@transaction.atomic
def marcar_sin_respuesta(*,context,invitacion_id):_perm(context,"marcar_sin_respuesta_rfq");return _invite_state(context,invitacion_id,"SIN_RESPUESTA")

def validar_rfq_para_publicacion(*,context,rfq):
    if rfq.empresa_id!=context.empresa.pk:raise PermissionDenied
    x=ResultadoValidacionRFQ();
    if rfq.expediente.estado not in {"ABIERTO","PREPARANDO_RFQ"}:x.bloqueantes.append("Expediente inactivo.")
    if not rfq.expediente.solicitudes_vinculadas.filter(activa=True,solicitud__estado="APROBADA").exists():x.bloqueantes.append("No hay solicitudes aprobadas.")
    if not rfq.lineas.filter(activo=True).exists():x.errores.append("Faltan líneas.")
    if not rfq.criterios.filter(activo=True).exists():x.errores.append("Faltan criterios.")
    if (rfq.criterios.filter(activo=True).aggregate(v=Sum("peso_porcentaje"))["v"] or 0)!=100:x.errores.append("Los pesos deben sumar 100.")
    if not rfq.reglas_participacion.filter(activo=True).exists():x.errores.append("Faltan reglas de participación.")
    if rfq.invitaciones.exclude(estado="RETIRADA").count()<rfq.minimo_proveedores:x.bloqueantes.append("Proveedores insuficientes.")
    if not rfq.lugar_entrega.strip() or not rfq.condiciones_comerciales.strip():x.errores.append("Faltan condiciones de entrega o comerciales.")
    from documentos.models import Documento
    ct=ContentType.objects.get_for_model(rfq)
    if not Documento.objects.filter(empresa=context.empresa,content_type=ct,object_id=rfq.pk,estado=Documento.Estado.ACTIVO).exists():x.errores.append("Falta documentación obligatoria de la RFQ.")
    if rfq.fecha_inicio>=rfq.fecha_limite:x.errores.append("La fecha límite debe ser posterior al inicio.")
    return x
def _trans_rfq(context,r,allowed,new,motivo=""):
    if r.estado not in allowed:raise ValidationError("Transición inválida.")
    old=r.estado;r.estado=new;r.save();_hist_rfq(context,r,old,new,motivo);return r
@transaction.atomic
def enviar_rfq_revision(*,context,rfq_id):_perm(context,"enviar_revision_rfq");return _trans_rfq(context,_lock_rfq(context,rfq_id),{"BORRADOR"},"EN_REVISION")
@transaction.atomic
def devolver_rfq_borrador(*,context,rfq_id,motivo):
    _perm(context,"devolver_borrador_rfq")
    if not motivo.strip():raise ValidationError("Motivo obligatorio.")
    return _trans_rfq(context,_lock_rfq(context,rfq_id),{"EN_REVISION"},"BORRADOR",motivo)
@transaction.atomic
def publicar_rfq(*,context,rfq_id):
    _perm(context,"publicar_rfq");r=_lock_rfq(context,rfq_id);v=validar_rfq_para_publicacion(context=context,rfq=r)
    if not v.valido:raise ValidationError(v.errores+v.bloqueantes)
    r.publicado_por=context.usuario;r.fecha_publicacion=timezone.now();_trans_rfq(context,r,{"EN_REVISION"},"PUBLICADA");return r
@transaction.atomic
def abrir_rfq(*,context,rfq_id):
    _perm(context,"abrir_rfq");r=_trans_rfq(context,_lock_rfq(context,rfq_id),{"PUBLICADA"},"ABIERTA");_trans_exp(context,r.expediente,"RFQ_ABIERTA");return r
@transaction.atomic
def extender_plazo_rfq(*,context,rfq_id,nueva_fecha,motivo):
    _perm(context,"extender_rfq");r=_lock_rfq(context,rfq_id)
    if not motivo.strip() or nueva_fecha<=r.fecha_limite:raise ValidationError("Extensión inválida.")
    r.fecha_limite=nueva_fecha;r.motivo_extension=motivo;r.save();return _trans_rfq(context,r,{"ABIERTA","EXTENDIDA"},"EXTENDIDA",motivo)
@transaction.atomic
def cerrar_rfq(*,context,rfq_id):
    _perm(context,"cerrar_rfq");r=_lock_rfq(context,rfq_id)
    if r.invitaciones.filter(estado__in={"BORRADOR","PENDIENTE_ENVIO","INVITADA"}).exists():raise ValidationError("Existen invitaciones pendientes de resolución.")
    r.fecha_cierre_real=timezone.now();r.cerrado_por=context.usuario;return _trans_rfq(context,r,{"ABIERTA","EXTENDIDA"},"CERRADA")
@transaction.atomic
def cancelar_rfq(*,context,rfq_id,motivo):
    _perm(context,"cancelar_rfq");r=_lock_rfq(context,rfq_id)
    if not motivo.strip():raise ValidationError("Motivo obligatorio.")
    r.motivo_cancelacion=motivo;return _trans_rfq(context,r,{"BORRADOR","EN_REVISION","PUBLICADA","ABIERTA","EXTENDIDA"},"CANCELADA",motivo)
@transaction.atomic
def crear_nueva_version_rfq(*,context,rfq_id):
    _perm(context,"versionar_rfq");old=_lock_rfq(context,rfq_id)
    if old.estado not in {"CERRADA","CANCELADA","DESIERTA"}:raise ValidationError("Solo procesos finalizados se versionan.")
    vals={f.name:getattr(old,f.name) for f in ProcesoRFQ._meta.fields if f.name not in {"id","numero","version","estado","fecha_publicacion","fecha_cierre_real","publicado_por","cerrado_por","creado_por","actualizado_por","fecha_creacion","fecha_actualizacion"}};new=ProcesoRFQ.objects.create(numero=old.numero+f"-V{old.version+1}",version=old.version+1,estado="BORRADOR",creado_por=context.usuario,actualizado_por=context.usuario,**vals)
    for l in old.lineas.filter(activo=True):
        data={f.name:getattr(l,f.name) for f in DetalleRFQ._meta.fields if f.name not in {"id","rfq","creado_en","actualizado_en"}};DetalleRFQ.objects.create(rfq=new,**data)
    _audit(context,new,"Nueva versión RFQ creada.",after={"origen_id":old.pk,"version":new.version});_emit(context,RFQVersionada,new,"versionada",{"origen_id":old.pk,"version":new.version});return new
