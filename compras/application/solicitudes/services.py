import csv
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from core.application.event_bus import event_bus
from core.application.numbering import obtener_siguiente_numero
from core.domain.rules import validate_safe_payload
from documentos.services import obtener_documentos
from workflow.api import workflow_service
from workflow.application.services import cancelar_workflow, marcar_correccion_atendida, reabrir_workflow
from workflow.domain.adapters import adapter_registry
from workflow.domain.exceptions import WorkflowError

from compras.domain.solicitudes.events import *
from compras.models import DetalleSolicitudCompra, HistorialEstadoSolicitudCompra, SolicitudCompra

MONEY=Decimal("0.01")
EDITABLE={SolicitudCompra.Estado.BORRADOR,SolicitudCompra.Estado.DEVUELTA}
FINALES={SolicitudCompra.Estado.APROBADA,SolicitudCompra.Estado.RECHAZADA,SolicitudCompra.Estado.CANCELADA,SolicitudCompra.Estado.CERRADA}

@dataclass
class ValidationResult:
    errors:list=field(default_factory=list); warnings:list=field(default_factory=list); blockers:list=field(default_factory=list)
    @property
    def valid(self): return not self.errors and not self.blockers

def _perm(ctx,code):
    if not ctx.usuario or not ctx.usuario.has_perm(f"compras.{code}"): raise PermissionDenied(f"Se requiere compras.{code}.")
def _owned(ctx,obj):
    if obj.empresa_id != ctx.empresa.pk: raise PermissionDenied("El registro pertenece a otra empresa.")
def _audit(ctx,obj,text,before=None,after=None):
    registrar_evento(empresa=ctx.empresa,usuario=ctx.usuario,request=ctx.request,objeto=obj,modulo="compras",accion=EventoAuditoria.Accion.OTRO,descripcion=text,datos_anteriores=before,datos_nuevos=after)
def _event(ctx,cls,obj,suffix,payload=None):
    data={"empresa_id":ctx.empresa.pk,"solicitud_id":obj.pk,"numero":obj.numero,"estado":obj.estado,"version":obj.version_documento,"actor_id":getattr(ctx.usuario,"pk",None),"schema_version":1,**(payload or {})};validate_safe_payload(data)
    return event_bus.publish(cls(empresa_id=ctx.empresa.pk,usuario_id=getattr(ctx.usuario,"pk",None),agregado_tipo="compras.SolicitudCompra",agregado_id=str(obj.pk),referencia=obj.numero,clave_idempotente=ctx.clave_idempotente or f"solicitud:{suffix}:{obj.pk}:{uuid4().hex}",payload=data))
def _history(ctx,obj,old,new,comment="",origin="USUARIO",metadata=None):
    return HistorialEstadoSolicitudCompra.objects.create(empresa=ctx.empresa,solicitud=obj,estado_anterior=old,estado_nuevo=new,usuario=ctx.usuario,comentario=comment,origen=origin,workflow_instancia_id=obj.workflow_instancia_id,ronda=obj.ronda_workflow_actual,metadata_segura=metadata or {})
def _lock(ctx,pk): return SolicitudCompra.objects.select_for_update().get(pk=pk,empresa=ctx.empresa)

@transaction.atomic
def crear_solicitud_compra(*,context,datos):
    _perm(context,"add_solicitudcompra")
    number=obtener_siguiente_numero(empresa=context.empresa,tipo_documento="SC",fecha=datos.get("fecha_solicitud"),prefijo="SC",longitud=6,context=context)
    existing=SolicitudCompra.objects.filter(empresa=context.empresa,numero=number).first()
    if existing:return existing
    obj=SolicitudCompra(empresa=context.empresa,numero=number,solicitante=datos.pop("solicitante",context.usuario),creado_por=context.usuario,actualizado_por=context.usuario,**datos);obj.full_clean();obj.save();_history(context,obj,"",obj.estado,"Creación");_audit(context,obj,"Solicitud de compra creada.",after={"numero":number});_event(context,SolicitudCompraCreada,obj,"creada");return obj

@transaction.atomic
def actualizar_solicitud_compra(*,context,solicitud_id,datos):
    _perm(context,"change_solicitudcompra");obj=_lock(context,solicitud_id)
    if obj.estado not in EDITABLE: raise ValidationError("La solicitud no admite edición estructural.")
    if obj.solicitante_id != context.usuario.pk and not context.usuario.has_perm("compras.administrar_solicitudescompra"): raise PermissionDenied
    protected={"empresa","numero","estado","version_documento","workflow_instancia","solicitante","subtotal_estimado","descuento_estimado","impuesto_estimado","total_estimado"}
    for key,value in datos.items():
        if key not in protected: setattr(obj,key,value)
    obj.actualizado_por=context.usuario;obj.full_clean();obj.save();_audit(context,obj,"Solicitud actualizada.");_event(context,SolicitudCompraActualizada,obj,"actualizada");return obj

def calcular_linea_solicitud(*,cantidad,precio_unitario_estimado,descuento_porcentaje=0,descuento_monto=0,impuesto_porcentaje=0):
    cantidad=Decimal(cantidad);precio=Decimal(precio_unitario_estimado);pct=Decimal(descuento_porcentaje or 0);explicit=Decimal(descuento_monto or 0);tax=Decimal(impuesto_porcentaje or 0)
    if cantidad<=0 or precio<0 or not 0<=pct<=100 or not 0<=tax<=100: raise ValidationError("Valores de cálculo inválidos.")
    gross=cantidad*precio;discount=explicit if explicit else gross*pct/100
    if discount>gross: raise ValidationError("El descuento supera el importe bruto.")
    subtotal=(gross-discount).quantize(MONEY,ROUND_HALF_UP);tax_amount=(subtotal*tax/100).quantize(MONEY,ROUND_HALF_UP)
    return {"descuento_monto":discount.quantize(MONEY,ROUND_HALF_UP),"subtotal":subtotal,"impuesto_monto":tax_amount,"total":subtotal+tax_amount}

def _line_values(datos):
    tax=datos.get("impuesto");rate=getattr(tax,"tasa",datos.get("impuesto_porcentaje_snapshot",0)) or 0
    values=calcular_linea_solicitud(cantidad=datos["cantidad"],precio_unitario_estimado=datos.get("precio_unitario_estimado",0),descuento_porcentaje=datos.get("descuento_porcentaje",0),descuento_monto=datos.get("descuento_monto",0),impuesto_porcentaje=rate)
    datos.update(values,impuesto_porcentaje_snapshot=rate);return datos

@transaction.atomic
def agregar_linea_solicitud(*,context,solicitud_id,datos):
    _perm(context,"change_solicitudcompra");obj=_lock(context,solicitud_id)
    if obj.estado not in EDITABLE: raise ValidationError("La solicitud no admite líneas.")
    datos=_line_values(dict(datos));line=DetalleSolicitudCompra(empresa=context.empresa,solicitud=obj,orden=datos.pop("orden",obj.lineas.count()+1),**datos);line.full_clean();line.save();recalcular_totales_solicitud(context=context,solicitud_id=obj.pk);_event(context,LineaSolicitudCompraAgregada,obj,f"linea:{line.pk}",{"linea_id":line.pk});return line

@transaction.atomic
def actualizar_linea_solicitud(*,context,linea_id,datos):
    _perm(context,"change_solicitudcompra");line=DetalleSolicitudCompra.objects.select_for_update().select_related("solicitud").get(pk=linea_id,empresa=context.empresa)
    if line.solicitud.estado not in EDITABLE: raise ValidationError("La solicitud no admite edición.")
    for key,value in _line_values(dict(datos)).items(): setattr(line,key,value)
    line.full_clean();line.save();recalcular_totales_solicitud(context=context,solicitud_id=line.solicitud_id);_event(context,LineaSolicitudCompraActualizada,line.solicitud,f"linea:{line.pk}",{"linea_id":line.pk});return line

@transaction.atomic
def retirar_linea_solicitud(*,context,linea_id):
    _perm(context,"change_solicitudcompra");line=DetalleSolicitudCompra.objects.select_for_update().select_related("solicitud").get(pk=linea_id,empresa=context.empresa)
    if line.solicitud.estado not in EDITABLE: raise ValidationError("La solicitud no admite edición.")
    line.activo=False;line.save(update_fields=["activo","actualizado_en"]);recalcular_totales_solicitud(context=context,solicitud_id=line.solicitud_id);_event(context,LineaSolicitudCompraRetirada,line.solicitud,f"linea-retirada:{line.pk}",{"linea_id":line.pk});return line

@transaction.atomic
def recalcular_totales_solicitud(*,context,solicitud_id):
    obj=_lock(context,solicitud_id);tot=obj.lineas.filter(activo=True).aggregate(subtotal=Sum("subtotal"),descuento=Sum("descuento_monto"),impuesto=Sum("impuesto_monto"),total=Sum("total"));obj.subtotal_estimado=tot["subtotal"] or 0;obj.descuento_estimado=tot["descuento"] or 0;obj.impuesto_estimado=tot["impuesto"] or 0;obj.total_estimado=tot["total"] or 0;obj.save(update_fields=["subtotal_estimado","descuento_estimado","impuesto_estimado","total_estimado","fecha_actualizacion"]);return obj

def validar_solicitud_para_envio(*,context,solicitud):
    _owned(context,solicitud);result=ValidationResult()
    for field,label in (("titulo","título"),("justificacion","justificación"),("impacto_no_compra","impacto de no compra")):
        if not getattr(solicitud,field,"{}").strip(): result.errors.append(f"Falta {label}.")
    if solicitud.fecha_necesaria<solicitud.fecha_solicitud: result.errors.append("La fecha necesaria es inválida.")
    if not solicitud.lineas.filter(activo=True).exists(): result.blockers.append("Debe registrar al menos una línea.")
    for line in solicitud.lineas.filter(activo=True).select_related("producto","unidad_medida"):
        try: line.full_clean()
        except ValidationError as exc: result.errors.extend(exc.messages)
    if solicitud.es_urgente and solicitud.prioridad!=SolicitudCompra.Prioridad.URGENTE: result.warnings.append("La solicitud urgente no tiene prioridad URGENTE.")
    if solicitud.compra_directa_propuesta and not solicitud.motivo_compra_directa.strip(): result.errors.append("Falta motivo de compra directa.")
    if solicitud.proveedor_exclusivo_declarado and not solicitud.motivo_exclusividad.strip(): result.errors.append("Falta motivo de exclusividad.")
    try: adapter_registry.get("compras.solicitud_compra")
    except Exception as exc: result.blockers.append(str(exc))
    return result

@transaction.atomic
def marcar_solicitud_lista(*,context,solicitud_id):
    _perm(context,"marcar_lista_solicitudcompra");obj=_lock(context,solicitud_id)
    if obj.estado!=SolicitudCompra.Estado.BORRADOR: raise ValidationError("Transición inválida.")
    recalcular_totales_solicitud(context=context,solicitud_id=obj.pk);result=validar_solicitud_para_envio(context=context,solicitud=obj)
    if not result.valid: raise ValidationError(result.errors+result.blockers)
    old=obj.estado;obj.estado=SolicitudCompra.Estado.LISTA_PARA_ENVIO;obj.save(update_fields=["estado","fecha_actualizacion"]);_history(context,obj,old,obj.estado);_event(context,SolicitudCompraMarcadaLista,obj,"lista");return obj

@transaction.atomic
def devolver_solicitud_a_borrador(*,context,solicitud_id):
    _perm(context,"devolver_borrador_solicitudcompra");obj=_lock(context,solicitud_id)
    if obj.estado!=SolicitudCompra.Estado.LISTA_PARA_ENVIO: raise ValidationError("Transición inválida.")
    old=obj.estado;obj.estado=SolicitudCompra.Estado.BORRADOR;obj.save(update_fields=["estado","fecha_actualizacion"]);_history(context,obj,old,obj.estado);_event(context,SolicitudCompraDevueltaABorrador,obj,"borrador");return obj

def congelar_snapshot_solicitud(*,solicitud):
    for line in solicitud.lineas.filter(activo=True).select_related("producto","unidad_medida"):
        if line.producto_id: line.codigo_producto_snapshot=line.producto.codigo or "";line.unidad_producto_snapshot=line.producto.unidad_medida or ""
        line.cantidad_base=line.cantidad*line.factor_conversion;line.save(update_fields=["codigo_producto_snapshot","unidad_producto_snapshot","cantidad_base","actualizado_en"])

@transaction.atomic
def enviar_solicitud_a_aprobacion(*,context,solicitud_id,idempotency_key):
    _perm(context,"enviar_solicitudcompra");obj=_lock(context,solicitud_id)
    if obj.estado!=SolicitudCompra.Estado.LISTA_PARA_ENVIO: raise ValidationError("La solicitud no está lista para enviar.")
    recalcular_totales_solicitud(context=context,solicitud_id=obj.pk);result=validar_solicitud_para_envio(context=context,solicitud=obj)
    if not result.valid: raise ValidationError(result.errors+result.blockers)
    congelar_snapshot_solicitud(solicitud=obj)
    inst=workflow_service.start(document=obj,adapter="compras.solicitud_compra",context=context,idempotency_key=idempotency_key,dominio="COMPRAS",tipo_documento="SOLICITUD_COMPRA")
    obj.refresh_from_db();obj.workflow_instancia=inst;obj.estado_workflow_snapshot=inst.estado;obj.ronda_workflow_actual=1;obj.enviada_por=context.usuario;obj.enviada_en=obj.enviada_en or timezone.now();obj.save();_event(context,SolicitudCompraEnviadaAWorkflow,obj,"enviada",{"workflow_instancia_id":inst.pk});return obj

@transaction.atomic
def cancelar_solicitud_compra(*,context,solicitud_id,motivo):
    _perm(context,"cancelar_solicitudcompra");obj=_lock(context,solicitud_id)
    if obj.estado in FINALES: raise ValidationError("La solicitud no puede cancelarse.")
    if not motivo.strip(): raise ValidationError("El motivo es obligatorio.")
    if obj.estado==SolicitudCompra.Estado.EN_APROBACION: cancelar_workflow(context=context,instancia_id=obj.workflow_instancia_id,motivo=motivo)
    old=obj.estado;obj.estado=SolicitudCompra.Estado.CANCELADA;obj.motivo_cancelacion=motivo;obj.cancelada_en=timezone.now();obj.save();_history(context,obj,old,obj.estado,motivo);_event(context,SolicitudCompraCancelada,obj,"cancelada");return obj

@transaction.atomic
def duplicar_solicitud_compra(*,context,solicitud_id):
    _perm(context,"duplicar_solicitudcompra");source=_lock(context,solicitud_id);data={f.name:getattr(source,f.name) for f in SolicitudCompra._meta.fields if f.name not in {"id","empresa","numero","version_documento","estado","workflow_instancia","estado_workflow_snapshot","ronda_workflow_actual","enviada_en","aprobada_en","rechazada_en","devuelta_en","cancelada_en","cerrada_en","motivo_rechazo","motivo_cancelacion","comentario_devolucion_actual","creado_por","actualizado_por","fecha_creacion","fecha_actualizacion","enviada_por","aprobada_por_sistema","rechazada_por_sistema","origen_duplicacion"}}
    data.update(origen_duplicacion=source,fecha_solicitud=timezone.localdate(),solicitante=context.usuario);obj=crear_solicitud_compra(context=context,datos=data)
    for line in source.lineas.filter(activo=True):
        values={f.name:getattr(line,f.name) for f in DetalleSolicitudCompra._meta.fields if f.name not in {"id","empresa","solicitud","creado_en","actualizado_en"}};DetalleSolicitudCompra.objects.create(empresa=context.empresa,solicitud=obj,**values)
    recalcular_totales_solicitud(context=context,solicitud_id=obj.pk);_event(context,SolicitudCompraDuplicada,obj,"duplicada",{"origen_id":source.pk});return obj

def sincronizar_estado_desde_workflow(*,context,solicitud_id):
    obj=SolicitudCompra.objects.get(pk=solicitud_id,empresa=context.empresa)
    if obj.workflow_instancia_id:
        from compras.domain.solicitudes.workflow_adapter import SolicitudCompraWorkflowAdapter
        SolicitudCompraWorkflowAdapter()._sync(obj,obj.workflow_instancia.estado)
    return obj

@transaction.atomic
def corregir_solicitud_devuelta(*,context,solicitud_id,respuesta=""):
    _perm(context,"corregir_solicitudcompra");obj=_lock(context,solicitud_id)
    if obj.estado!=SolicitudCompra.Estado.DEVUELTA: raise ValidationError("Solo se corrigen solicitudes devueltas.")
    obj.version_documento+=1;obj.estado=SolicitudCompra.Estado.BORRADOR;obj.save();_history(context,obj,"DEVUELTA","BORRADOR",respuesta);_event(context,SolicitudCompraCorregida,obj,"corregida");return obj

@transaction.atomic
def reenviar_solicitud_devuelta(*,context,solicitud_id,motivo):
    _perm(context,"enviar_solicitudcompra");obj=_lock(context,solicitud_id)
    if obj.estado not in {SolicitudCompra.Estado.BORRADOR,SolicitudCompra.Estado.LISTA_PARA_ENVIO}: raise ValidationError("La solicitud no admite reenvío.")
    result=validar_solicitud_para_envio(context=context,solicitud=obj)
    if not result.valid: raise ValidationError(result.errors+result.blockers)
    inst=reabrir_workflow(context=context,instancia_id=obj.workflow_instancia_id,motivo=motivo);obj.refresh_from_db();obj.estado=SolicitudCompra.Estado.EN_APROBACION;obj.ronda_workflow_actual=inst.rondas.order_by("-numero").first().numero;obj.save();_event(context,SolicitudCompraReenviada,obj,"reenviada");return obj

def obtener_estado_aprobacion(*,solicitud): return solicitud.workflow_instancia
def obtener_historial_integrado(*,empresa,solicitud):
    if solicitud.empresa_id!=empresa.pk: raise PermissionDenied
    return {"solicitud":solicitud.historial.select_related("usuario"),"workflow":solicitud.workflow_instancia.decisiones.select_related("usuario_efectivo") if solicitud.workflow_instancia_id else []}

def exportar_solicitudes_csv(*,context,queryset):
    _perm(context,"exportar_solicitudescompra");out=StringIO(newline="");writer=csv.writer(out);writer.writerow(["Número","Título","Estado","Prioridad","Fecha","Moneda","Total"])
    def safe(value):
        text=str(value or "");return "'"+text if text[:1] in ("=","+","-","@") else text
    rows=0
    for obj in queryset.filter(empresa=context.empresa): writer.writerow([safe(obj.numero),safe(obj.titulo),obj.estado,obj.prioridad,obj.fecha_solicitud,safe(obj.moneda.moneda.codigo),obj.total_estimado]);rows+=1
    _audit(context,None,"Exportación de solicitudes generada.",after={"filas":rows});return out.getvalue()
