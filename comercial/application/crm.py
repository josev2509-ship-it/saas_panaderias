from datetime import date
from dataclasses import replace
import re

from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.domain.crm_events import *
from comercial.models import *
from core.application.event_bus import event_bus
from core.application.numbering import obtener_siguiente_numero

TERMINALES={OportunidadComercial.Etapa.GANADA,OportunidadComercial.Etapa.PERDIDA,OportunidadComercial.Etapa.CANCELADA}
TRANSICIONES={"IDENTIFICADA":{"CALIFICADA","CANCELADA"},"CALIFICADA":{"PROPUESTA","PERDIDA","CANCELADA"},"PROPUESTA":{"NEGOCIACION","GANADA","PERDIDA","CANCELADA"},"NEGOCIACION":{"GANADA","PERDIDA","CANCELADA"}}

def _perm(c,codename):
    if not c.usuario or not c.usuario.has_perm(f"comercial.{codename}"):raise PermissionDenied
def _norm(value):return re.sub(r"[^0-9A-Za-z]","",value or "").upper()
def _audit(c,o,text,before=None,after=None):registrar_evento(empresa=c.empresa,usuario=c.usuario,request=c.request,objeto=o,modulo="crm",accion=EventoAuditoria.Accion.OTRO,descripcion=text,datos_anteriores=before,datos_nuevos=after)
def _emit(c,cls,o,suffix,extra=None):
    payload={"schema_version":1,"empresa_id":c.empresa.pk,"aggregate_type":o.__class__.__name__,"aggregate_id":o.pk,"actor_id":getattr(c.usuario,"pk",None),**(extra or {})}
    event_bus.publish(cls(empresa_id=c.empresa.pk,usuario_id=getattr(c.usuario,"pk",None),agregado_tipo=f"comercial.{o.__class__.__name__}",agregado_id=str(o.pk),referencia=getattr(o,"numero",str(o.pk)),clave_idempotente=f"{c.identificador_solicitud}:{suffix}:{o.pk}"[:180],payload=payload))
def _hist_prospecto(c,o,anterior,nuevo,comentario=""):HistorialEstadoProspecto.objects.create(empresa=c.empresa,prospecto=o,estado_anterior=anterior,estado_nuevo=nuevo,usuario=c.usuario,comentario=comentario)
def _hist_opo(c,o,anterior,nuevo,comentario=""):HistorialEtapaOportunidad.objects.create(empresa=c.empresa,oportunidad=o,etapa_anterior=anterior,etapa_nueva=nuevo,usuario=c.usuario,comentario=comentario)
def _hist_act(c,o,accion,anterior="",nuevo=""):HistorialActividadComercial.objects.create(empresa=c.empresa,actividad=o,accion=accion,estado_anterior=anterior,estado_nuevo=nuevo,usuario=c.usuario,snapshot={"asunto":o.asunto,"fecha_inicio":o.fecha_inicio.isoformat()})
def _number_context(context,tipo):return replace(context,clave_idempotente=context.clave_idempotente or f"crm-{tipo.lower()}-{context.identificador_solicitud}")

@transaction.atomic
def crear_prospecto(*,context,datos):
    _perm(context,"add_prospecto");ident=_norm(datos.get("identificacion_fiscal"));correo=(datos.get("correo") or "").strip().lower();telefono=_norm(datos.get("telefono"));duplicados=Prospecto.objects.filter(empresa=context.empresa).exclude(estado__in=["CONVERTIDO","DESCARTADO"])
    criterio=Q()
    if ident:criterio|=Q(identificacion_fiscal=ident)
    if correo:criterio|=Q(correo__iexact=correo)
    if telefono:criterio|=Q(telefono=telefono)
    if criterio and duplicados.filter(criterio).exists():raise ValidationError("Existe un prospecto activo con identificación, correo o teléfono coincidente.")
    productos=datos.pop("productos_interes",[]);datos={**datos,"identificacion_fiscal":ident,"correo":correo,"telefono":telefono};numero=obtener_siguiente_numero(empresa=context.empresa,tipo_documento="PROS",usuario=context.usuario,context=_number_context(context,"PROS"));o=Prospecto(empresa=context.empresa,numero=numero,creado_por=context.usuario,actualizado_por=context.usuario,**datos);o.full_clean();o.save();o.productos_interes.set([p for p in productos if p.empresa_id==context.empresa.pk]);_hist_prospecto(context,o,"",o.estado);_audit(context,o,"Prospecto creado.",after={"numero":o.numero,"estado":o.estado});_emit(context,ProspectoCreado,o,"creado");return o
@transaction.atomic
def actualizar_prospecto(*,context,pk,datos):
    _perm(context,"change_prospecto");o=Prospecto.objects.select_for_update().get(pk=pk,empresa=context.empresa)
    if o.estado in ("CONVERTIDO","DESCARTADO"):raise ValidationError("El prospecto está en estado terminal.")
    productos=datos.pop("productos_interes",None)
    for k,v in datos.items():setattr(o,k,_norm(v) if k in ("identificacion_fiscal","telefono") else v)
    o.actualizado_por=context.usuario;o.full_clean();o.save();
    if productos is not None:o.productos_interes.set([p for p in productos if p.empresa_id==context.empresa.pk])
    _audit(context,o,"Prospecto actualizado.");_emit(context,ProspectoActualizado,o,"actualizado");return o
@transaction.atomic
def _estado_prospecto(context,pk,nuevo,motivo=""):
    o=Prospecto.objects.select_for_update().get(pk=pk,empresa=context.empresa);anterior=o.estado
    if anterior in ("CONVERTIDO","DESCARTADO"):raise ValidationError("El prospecto está en estado terminal.")
    o.estado=nuevo
    if nuevo=="NO_CALIFICADO":o.motivo_no_calificacion=motivo
    if nuevo=="DESCARTADO":o.motivo_descarte=motivo
    o.actualizado_por=context.usuario;o.full_clean();o.save();_hist_prospecto(context,o,anterior,nuevo,motivo);_audit(context,o,f"Prospecto: {anterior} → {nuevo}.");return o
def contactar_prospecto(*,context,pk):
    _perm(context,"change_prospecto");o=_estado_prospecto(context,pk,"CONTACTADO");_emit(context,ProspectoContactado,o,"contactado");return o
def calificar_prospecto(*,context,pk):
    _perm(context,"calificar_prospecto");o=_estado_prospecto(context,pk,"CALIFICADO");_emit(context,ProspectoCalificado,o,"calificado");return o
def no_calificar_prospecto(*,context,pk,motivo):
    _perm(context,"calificar_prospecto");
    if not motivo.strip():raise ValidationError("El motivo es obligatorio.")
    o=_estado_prospecto(context,pk,"NO_CALIFICADO",motivo);_emit(context,ProspectoNoCalificado,o,"no-calificado");return o
def descartar_prospecto(*,context,pk,motivo):
    _perm(context,"descartar_prospecto");
    if not motivo.strip():raise ValidationError("El motivo es obligatorio.")
    o=_estado_prospecto(context,pk,"DESCARTADO",motivo);_emit(context,ProspectoDescartado,o,"descartado");return o
@transaction.atomic
def convertir_prospecto_a_cliente(*,context,pk):
    _perm(context,"convertir_prospecto");o=Prospecto.objects.select_for_update().get(pk=pk,empresa=context.empresa)
    if o.estado=="CONVERTIDO" and o.cliente_convertido_id:return o.cliente_convertido
    if o.estado!="CALIFICADO":raise ValidationError("Solo se convierte un prospecto calificado.")
    existente=Cliente.objects.filter(empresa=context.empresa).filter(Q(rnc_cedula=o.identificacion_fiscal)&~Q(rnc_cedula="")|Q(correo__iexact=o.correo)&~Q(correo="")).first()
    cliente=existente or Cliente.objects.create(empresa=context.empresa,codigo=("CRM-"+o.numero)[-30:],tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,nombre_comercial=o.nombre_comercial or o.nombre,razon_social=o.nombre,rnc_cedula=o.identificacion_fiscal,telefono=o.telefono,correo=o.correo,direccion_fiscal=o.direccion,provincia=o.provincia,municipio=o.municipio,creado_por=context.usuario)
    if o.direccion and not cliente.direcciones.exists():DireccionCliente.objects.create(cliente=cliente,nombre="Principal",tipo=DireccionCliente.Tipo.FISCAL,direccion=o.direccion,provincia=o.provincia,municipio=o.municipio,es_principal=True)
    if o.contacto_principal and not cliente.contactos.exists():ContactoCliente.objects.create(cliente=cliente,nombre=o.contacto_principal,telefono=o.telefono,correo=o.correo,es_principal=True)
    anterior=o.estado;o.estado="CONVERTIDO";o.cliente_convertido=cliente;o.convertido_por=context.usuario;o.fecha_conversion=timezone.now();o.save(update_fields=["estado","cliente_convertido","convertido_por","fecha_conversion","fecha_actualizacion"]);OportunidadComercial.objects.filter(empresa=context.empresa,prospecto=o).exclude(etapa__in=TERMINALES).update(cliente=cliente);_hist_prospecto(context,o,anterior,o.estado);_audit(context,o,"Prospecto convertido a cliente.",after={"cliente_id":cliente.pk});_emit(context,ProspectoConvertido,o,"convertido",{"cliente_id":cliente.pk});return cliente
@transaction.atomic
def reasignar_prospecto(*,context,pk,vendedor):
    _perm(context,"reasignar_prospecto");o=Prospecto.objects.select_for_update().get(pk=pk,empresa=context.empresa)
    if vendedor.empresa_id!=context.empresa.pk:raise ValidationError("El vendedor pertenece a otra empresa.")
    anterior=o.vendedor_id;o.vendedor=vendedor;o.equipo=vendedor.equipo;o.actualizado_por=context.usuario;o.save();_audit(context,o,"Prospecto reasignado.",{"vendedor_id":anterior},{"vendedor_id":vendedor.pk});_emit(context,ProspectoReasignado,o,"reasignado");return o
def duplicar_prospecto(*,context,pk):
    o=Prospecto.objects.get(pk=pk,empresa=context.empresa);datos={f.name:getattr(o,f.name) for f in Prospecto._meta.fields if f.name not in {"id","empresa","numero","estado","creado_por","actualizado_por","convertido_por","fecha_conversion","cliente_convertido","fecha_creacion","fecha_actualizacion","identificacion_fiscal","correo","telefono"}};datos["nombre"]=f"{o.nombre} (copia)";return crear_prospecto(context=context,datos=datos)

@transaction.atomic
def crear_oportunidad(*,context,datos):
    _perm(context,"add_oportunidadcomercial");numero=obtener_siguiente_numero(empresa=context.empresa,tipo_documento="OPO",usuario=context.usuario,context=_number_context(context,"OPO"));o=OportunidadComercial(empresa=context.empresa,numero=numero,creado_por=context.usuario,actualizado_por=context.usuario,**datos);o.full_clean();o.save();_hist_opo(context,o,"",o.etapa);_audit(context,o,"Oportunidad creada.");_emit(context,OportunidadCreada,o,"creada");return o
@transaction.atomic
def actualizar_oportunidad(*,context,pk,datos):
    _perm(context,"change_oportunidadcomercial");o=OportunidadComercial.objects.select_for_update().get(pk=pk,empresa=context.empresa)
    if o.etapa in TERMINALES:raise ValidationError("La oportunidad está cerrada.")
    for k,v in datos.items():setattr(o,k,v)
    o.actualizado_por=context.usuario;o.full_clean();o.save();_audit(context,o,"Oportunidad actualizada.");_emit(context,OportunidadActualizada,o,"actualizada");return o
@transaction.atomic
def cambiar_etapa_oportunidad(*,context,pk,etapa,motivo=""):
    _perm(context,"cambiar_etapa_oportunidad");o=OportunidadComercial.objects.select_for_update().get(pk=pk,empresa=context.empresa);anterior=o.etapa
    if anterior in TERMINALES or etapa not in TRANSICIONES.get(anterior,set()):raise ValidationError("Transición de etapa no permitida.")
    if etapa=="PERDIDA" and not motivo.strip():raise ValidationError("El motivo de pérdida es obligatorio.")
    if etapa=="CANCELADA" and not motivo.strip():raise ValidationError("El motivo de cancelación es obligatorio.")
    o.etapa=etapa;o.motivo_perdida=motivo if etapa=="PERDIDA" else o.motivo_perdida;o.motivo_cancelacion=motivo if etapa=="CANCELADA" else o.motivo_cancelacion
    if etapa in TERMINALES:o.fecha_cierre_real=timezone.localdate();o.cerrado_por=context.usuario;o.probabilidad=100 if etapa=="GANADA" else 0
    o.save();_hist_opo(context,o,anterior,etapa,motivo);_audit(context,o,f"Oportunidad: {anterior} → {etapa}.");evento={"GANADA":OportunidadGanada,"PERDIDA":OportunidadPerdida,"CANCELADA":OportunidadCancelada}.get(etapa,OportunidadEtapaCambiada);_emit(context,evento,o,f"etapa-{etapa}");return o
def marcar_oportunidad_ganada(*,context,pk):_perm(context,"ganar_oportunidad");return cambiar_etapa_oportunidad(context=context,pk=pk,etapa="GANADA")
def marcar_oportunidad_perdida(*,context,pk,motivo):_perm(context,"perder_oportunidad");return cambiar_etapa_oportunidad(context=context,pk=pk,etapa="PERDIDA",motivo=motivo)
def cancelar_oportunidad(*,context,pk,motivo):_perm(context,"cancelar_oportunidad");return cambiar_etapa_oportunidad(context=context,pk=pk,etapa="CANCELADA",motivo=motivo)
def recalcular_monto_ponderado(o):o.monto_ponderado=o.monto_estimado*o.probabilidad/Decimal("100");o.save(update_fields=["monto_ponderado"]);return o
def duplicar_oportunidad(*,context,pk):
    o=OportunidadComercial.objects.get(pk=pk,empresa=context.empresa);datos={f.name:getattr(o,f.name) for f in OportunidadComercial._meta.fields if f.name not in {"id","empresa","numero","etapa","monto_ponderado","creado_por","actualizado_por","cerrado_por","fecha_cierre_real","fecha_creacion","fecha_actualizacion"}};datos["titulo"]+= " (copia)";return crear_oportunidad(context=context,datos=datos)
@transaction.atomic
def reasignar_oportunidad(*,context,pk,vendedor):
    _perm(context,"reasignar_oportunidad");o=OportunidadComercial.objects.select_for_update().get(pk=pk,empresa=context.empresa)
    if vendedor.empresa_id!=context.empresa.pk:raise ValidationError("El vendedor pertenece a otra empresa.")
    o.vendedor=vendedor;o.equipo=vendedor.equipo;o.save();_audit(context,o,"Oportunidad reasignada.");_emit(context,OportunidadReasignada,o,"reasignada");return o

@transaction.atomic
def crear_actividad(*,context,datos):
    _perm(context,"add_actividadcomercial");o=ActividadComercial(empresa=context.empresa,creado_por=context.usuario,actualizado_por=context.usuario,**datos);o.full_clean();o.save();_hist_act(context,o,"CREADA","",o.estado);_audit(context,o,"Actividad comercial creada.");_emit(context,ActividadComercialCreada,o,"creada");return o
@transaction.atomic
def actualizar_actividad(*,context,pk,datos):
    _perm(context,"change_actividadcomercial");o=ActividadComercial.objects.select_for_update().get(pk=pk,empresa=context.empresa)
    if o.estado in ("COMPLETADA","CANCELADA"):raise ValidationError("La actividad está cerrada.")
    for k,v in datos.items():setattr(o,k,v)
    o.actualizado_por=context.usuario;o.full_clean();o.save();_hist_act(context,o,"ACTUALIZADA");_audit(context,o,"Actividad actualizada.");_emit(context,ActividadComercialActualizada,o,"actualizada");return o
def iniciar_actividad(*,context,pk):_perm(context,"change_actividadcomercial");return _estado_actividad(context,pk,"EN_PROGRESO",ActividadComercialActualizada)
def completar_actividad(*,context,pk,resultado):
    _perm(context,"completar_actividad_comercial");
    if not resultado.strip():raise ValidationError("El resultado es obligatorio.")
    return _estado_actividad(context,pk,"COMPLETADA",ActividadComercialCompletada,resultado)
def cancelar_actividad(*,context,pk):_perm(context,"cancelar_actividad_comercial");return _estado_actividad(context,pk,"CANCELADA",ActividadComercialCancelada)
@transaction.atomic
def _estado_actividad(context,pk,nuevo,evento,resultado=""):
    o=ActividadComercial.objects.select_for_update().get(pk=pk,empresa=context.empresa);anterior=o.estado
    if anterior in ("COMPLETADA","CANCELADA"):raise ValidationError("La actividad está cerrada.")
    o.estado=nuevo
    if resultado:o.resultado=resultado
    if nuevo=="COMPLETADA":o.completado_por=context.usuario
    o.full_clean();o.save();_hist_act(context,o,nuevo,anterior,nuevo);_audit(context,o,f"Actividad: {anterior} → {nuevo}.");_emit(context,evento,o,f"estado-{nuevo}");return o
@transaction.atomic
def reprogramar_actividad(*,context,pk,fecha_inicio,fecha_fin=None):
    _perm(context,"reprogramar_actividad_comercial");o=ActividadComercial.objects.select_for_update().get(pk=pk,empresa=context.empresa);anterior=o.fecha_inicio;o.fecha_inicio=fecha_inicio;o.fecha_fin=fecha_fin;o.estado="PENDIENTE";o.full_clean();o.save();_hist_act(context,o,"REPROGRAMADA");_audit(context,o,"Actividad reprogramada.",{"fecha_inicio":anterior.isoformat()},{"fecha_inicio":fecha_inicio.isoformat()});_emit(context,ActividadComercialReprogramada,o,"reprogramada");return o
@transaction.atomic
def marcar_actividades_vencidas(*,context):
    _perm(context,"administrar_actividad_comercial");ids=[]
    for o in ActividadComercial.objects.filter(empresa=context.empresa,estado__in=["PENDIENTE","EN_PROGRESO"],fecha_inicio__lt=timezone.now()).select_for_update():o.estado="VENCIDA";o.save(update_fields=["estado"]);_hist_act(context,o,"VENCIDA");_audit(context,o,"Actividad marcada vencida.");_emit(context,ActividadComercialVencida,o,"vencida");ids.append(o.pk)
    return ids
def crear_siguiente_actividad(*,context,pk,datos):
    origen=ActividadComercial.objects.get(pk=pk,empresa=context.empresa);datos.setdefault("prospecto",origen.prospecto);datos.setdefault("cliente",origen.cliente);datos.setdefault("oportunidad",origen.oportunidad);return crear_actividad(context=context,datos=datos)
