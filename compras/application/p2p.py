import hashlib
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from core.application.event_bus import event_bus
from core.application.numbering import obtener_siguiente_numero
from inventario.engine import InventoryEngine
from inventario.models import LoteInventario
from contabilidad.api import contabilizar_devolucion_compra,contabilizar_recepcion_compra
from compras.models import *
from compras.domain.p2p_events import *

DEFAULT_WEIGHTS={"precio":25,"impuestos":5,"descuentos":5,"plazo":8,"entrega":8,"garantia":5,"calidad":10,"cumplimiento":10,"riesgo":7,"capacidad":7,"respuesta":5,"documentacion":5}

def _perm(c,code):
    if not c.usuario or not c.usuario.has_perm(f"compras.{code}"):raise PermissionDenied
def _num(c,tipo):return obtener_siguiente_numero(empresa=c.empresa,tipo_documento=tipo,usuario=c.usuario,context=replace(c,clave_idempotente=f"{c.clave_idempotente}:{tipo}"))
def _audit(c,o,text,before=None,after=None):registrar_evento(empresa=c.empresa,usuario=c.usuario,request=c.request,objeto=o,modulo="compras",accion=EventoAuditoria.Accion.OTRO,descripcion=text,datos_anteriores=before,datos_nuevos=after)
def _emit(c,cls,o,suffix,payload=None):event_bus.publish(cls(empresa_id=c.empresa.pk,usuario_id=getattr(c.usuario,"pk",None),agregado_tipo=f"compras.{o._meta.model_name}",agregado_id=str(o.pk),referencia=getattr(o,"numero",str(o.pk)),clave_idempotente=f"p2p:{suffix}:{o.pk}",payload={"schema_version":1,"empresa_id":c.empresa.pk,"estado":getattr(o,"estado",None),**(payload or {})}))
def _hist(model,obj,c,old,new,comment=""):model.objects.create(**{obj._meta.model_name.split("compra")[0] if False else {HistorialOferta:"oferta",HistorialComparativo:"comparativo",HistorialAdjudicacion:"adjudicacion",HistorialOrdenCompra:"orden"}[model]:obj},estado_anterior=old,estado_nuevo=new,comentario=comment,usuario=c.usuario)

@transaction.atomic
def crear_oferta(*,context,rfq_id,proveedor_id,datos):
    rfq=ProcesoRFQ.objects.get(pk=rfq_id,empresa=context.empresa);proveedor=Proveedor.objects.get(pk=proveedor_id,empresa=context.empresa)
    oferta=OfertaProveedor.objects.create(empresa=context.empresa,rfq=rfq,proveedor=proveedor,numero=datos.get("numero") or _num(context,"OFE"),moneda=datos.get("moneda",rfq.moneda),tasa_cambio=datos.get("tasa_cambio",1),fecha_oferta=datos.get("fecha_oferta",timezone.localdate()),valida_hasta=datos["valida_hasta"],plazo_entrega_dias=datos.get("plazo_entrega_dias",0),garantia_dias=datos.get("garantia_dias",0),observaciones=datos.get("observaciones",""),creado_por=context.usuario,actualizado_por=context.usuario);_audit(context,oferta,"Oferta creada.");_emit(context,OfertaCreada,oferta,"oferta-creada");return oferta
@transaction.atomic
def guardar_linea_oferta(*,context,oferta_id,linea_rfq_id,datos):
    oferta=OfertaProveedor.objects.select_for_update().get(pk=oferta_id,empresa=context.empresa,estado__in=["BORRADOR","ACLARACION_SOLICITADA","ACTUALIZADA"]);linea=DetalleRFQ.objects.get(pk=linea_rfq_id,empresa=context.empresa,rfq=oferta.rfq);cantidad=Decimal(str(datos["cantidad"]));precio=Decimal(str(datos["precio_unitario"]));descuento=Decimal(str(datos.get("descuento",0)));impuesto=Decimal(str(datos.get("impuesto",0)));total=(cantidad*precio-descuento+impuesto).quantize(Decimal("0.01"));obj,_=LineaOferta.objects.update_or_create(oferta=oferta,linea_rfq=linea,defaults={"cantidad":cantidad,"precio_unitario":precio,"descuento":descuento,"impuesto":impuesto,"total":total,"marca":datos.get("marca",""),"modelo":datos.get("modelo",""),"cumple":datos.get("cumple",True),"observaciones":datos.get("observaciones","")});tot=oferta.lineas.aggregate(sub=Sum("total"),desc=Sum("descuento"),imp=Sum("impuesto"));oferta.total=tot["sub"] or 0;oferta.descuento=tot["desc"] or 0;oferta.impuesto=tot["imp"] or 0;oferta.subtotal=oferta.total+oferta.descuento-oferta.impuesto;oferta.save(update_fields=["subtotal","descuento","impuesto","total"]);return obj
def _snapshot_offer(o):return {"numero":o.numero,"version":o.version,"total":str(o.total),"moneda_id":o.moneda_id,"tasa_cambio":str(o.tasa_cambio),"lineas":[{"linea_rfq_id":x.linea_rfq_id,"cantidad":str(x.cantidad),"precio":str(x.precio_unitario),"total":str(x.total)} for x in o.lineas.order_by("pk")]}
@transaction.atomic
def transicionar_oferta(*,context,oferta_id,nuevo,motivo=""):
    o=OfertaProveedor.objects.select_for_update().get(pk=oferta_id,empresa=context.empresa);allowed={"BORRADOR":{"ENVIADA","RETIRADA"},"ENVIADA":{"ACLARACION_SOLICITADA","RETIRADA","VENCIDA","DESCALIFICADA","EVALUADA"},"ACLARACION_SOLICITADA":{"ACTUALIZADA","RETIRADA"},"ACTUALIZADA":{"ENVIADA","RETIRADA","VENCIDA","DESCALIFICADA","EVALUADA"},"EVALUADA":{"CERRADA"}}
    if nuevo not in allowed.get(o.estado,set()):raise ValidationError("Transición de oferta inválida.")
    if nuevo=="ENVIADA" and (not o.lineas.exists() or o.total<=0):raise ValidationError("La oferta debe contener líneas y total positivo.")
    old=o.estado;o.estado=nuevo;o.enviada_en=timezone.now() if nuevo=="ENVIADA" else o.enviada_en;o.save(update_fields=["estado","enviada_en"]);HistorialOferta.objects.create(oferta=o,estado_anterior=old,estado_nuevo=nuevo,comentario=motivo,usuario=context.usuario);event={"ENVIADA":OfertaEnviada,"ACLARACION_SOLICITADA":OfertaAclaracionSolicitada,"ACTUALIZADA":OfertaActualizada,"RETIRADA":OfertaRetirada,"VENCIDA":OfertaVencida,"DESCALIFICADA":OfertaDescalificada,"EVALUADA":OfertaEvaluada}.get(nuevo);_audit(context,o,f"Oferta {nuevo.lower()}.",{"estado":old},{"estado":nuevo,"motivo":motivo});_emit(context,event,o,f"oferta-{nuevo.lower()}") if event else None
    if nuevo in {"ENVIADA","ACTUALIZADA"}:versionar_oferta(context=context,oferta=o)
    return o
def versionar_oferta(*,context,oferta):
    snap=_snapshot_offer(oferta);raw=repr(snap).encode();v,_=VersionOferta.objects.get_or_create(oferta=oferta,version=oferta.version,defaults={"snapshot":snap,"hash_contenido":hashlib.sha256(raw).hexdigest(),"creado_por":context.usuario});_emit(context,OfertaVersionada,oferta,f"oferta-version-{oferta.version}");return v
@transaction.atomic
def solicitar_aclaracion(*,context,oferta_id,pregunta):
    o=transicionar_oferta(context=context,oferta_id=oferta_id,nuevo="ACLARACION_SOLICITADA",motivo=pregunta);return AclaracionOferta.objects.create(oferta=o,pregunta=pregunta,solicitada_por=context.usuario)
@transaction.atomic
def responder_aclaracion(*,context,aclaracion_id,respuesta):
    a=AclaracionOferta.objects.select_for_update().get(pk=aclaracion_id,oferta__empresa=context.empresa,estado="PENDIENTE");a.respuesta=respuesta;a.estado="RESPONDIDA";a.respondida_por=context.usuario;a.respondido_en=timezone.now();a.save();transicionar_oferta(context=context,oferta_id=a.oferta_id,nuevo="ACTUALIZADA",motivo="Aclaración respondida");return a

def _score(oferta,weights):
    lowest=oferta.rfq.ofertas.filter(estado__in=["ENVIADA","ACTUALIZADA","EVALUADA"],total__gt=0).order_by("total").values_list("total",flat=True).first() or oferta.total
    economic=(Decimal(str(lowest))/oferta.total*100 if oferta.total else 0);technical=Decimal("100") if all(x.cumple for x in oferta.lineas.all()) else Decimal("50");total=(Decimal(str(weights.get("precio",25)))*economic+Decimal(str(100-weights.get("precio",25)))*technical)/100;return technical,economic,min(Decimal("100"),total)
@transaction.atomic
def crear_comparativo(*,context,rfq_id,ponderaciones=None):
    rfq=ProcesoRFQ.objects.get(pk=rfq_id,empresa=context.empresa);obj=ComparativoCompra.objects.create(empresa=context.empresa,expediente=rfq.expediente,rfq=rfq,numero=_num(context,"COM"),ponderaciones=ponderaciones or DEFAULT_WEIGHTS,creado_por=context.usuario,actualizado_por=context.usuario);_emit(context,ComparativoCreado,obj,"comparativo-creado");return recalcular_comparativo(context=context,comparativo_id=obj.pk)
@transaction.atomic
def recalcular_comparativo(*,context,comparativo_id,ponderaciones=None):
    c=ComparativoCompra.objects.select_for_update().get(pk=comparativo_id,empresa=context.empresa);weights=ponderaciones or c.ponderaciones
    if Decimal(str(sum(weights.values())))!=100:raise ValidationError("Las ponderaciones deben sumar 100.")
    c.lineas.all().delete()
    for oferta in c.rfq.ofertas.filter(estado__in=["ENVIADA","ACTUALIZADA","EVALUADA"]).select_related("proveedor"):
        tech,econ,total=_score(oferta,weights);risk={"BAJO":100,"MEDIO":70,"ALTO":35,"CRITICO":0}.get(oferta.proveedor.nivel_riesgo,50);documentation=100 if oferta.proveedor.documentacion_completa else 0;LineaComparativo.objects.create(comparativo=c,oferta=oferta,proveedor=oferta.proveedor,precio=oferta.subtotal,impuestos=oferta.impuesto,descuentos=oferta.descuento,plazo=max(0,100-oferta.plazo_entrega_dias),entrega=max(0,100-oferta.plazo_entrega_dias),garantia=min(100,oferta.garantia_dias),calidad=tech,cumplimiento=tech,riesgo=risk,capacidad=tech,respuesta=tech,documentacion=documentation,score_tecnico=tech,score_economico=econ,score_total=total,explicacion=f"Score técnico {tech:.2f}; económico {econ:.2f}; total {total:.2f}.")
    for pos,row in enumerate(c.lineas.order_by("-score_total","precio","proveedor_id"),1):row.posicion=pos;row.save(update_fields=["posicion"])
    best=c.lineas.order_by("posicion").first();c.ponderaciones=weights;c.recomendacion=(f"Proveedor recomendado: {best.proveedor.nombre_comercial}. {best.explicacion}" if best else "Sin ofertas evaluables.");c.save(update_fields=["ponderaciones","recomendacion"]);HistorialComparativo.objects.create(comparativo=c,accion="RECALCULADO",snapshot={"ponderaciones":weights,"recomendacion":c.recomendacion},usuario=context.usuario);_emit(context,ComparativoRecalculado,c,"comparativo-recalculado");return c
def guardar_escenario(*,context,comparativo_id,nombre,ponderaciones):
    c=recalcular_comparativo(context=context,comparativo_id=comparativo_id,ponderaciones=ponderaciones);results={str(x.proveedor_id):str(x.score_total) for x in c.lineas.all()};o=EscenarioComparativo.objects.create(comparativo=c,nombre=nombre,ponderaciones=ponderaciones,resultados=results,creado_por=context.usuario);_emit(context,EscenarioComparativoCreado,c,f"escenario-{o.pk}");return o
def congelar_comparativo(*,context,comparativo_id):
    c=ComparativoCompra.objects.get(pk=comparativo_id,empresa=context.empresa);c.snapshot={"ponderaciones":c.ponderaciones,"lineas":[{"proveedor_id":x.proveedor_id,"score_total":str(x.score_total),"posicion":x.posicion} for x in c.lineas.all()]};c.estado="CONGELADO";c.congelado_en=timezone.now();c.save();_emit(context,ComparativoCongelado,c,"comparativo-congelado");return c

@transaction.atomic
def crear_adjudicacion(*,context,comparativo_id,tipo="TOTAL",selecciones=None,justificacion=""):
    comp=ComparativoCompra.objects.get(pk=comparativo_id,empresa=context.empresa);a=AdjudicacionCompra.objects.create(empresa=context.empresa,expediente=comp.expediente,comparativo=comp,numero=_num(context,"ADJ"),tipo=tipo,justificacion=justificacion,snapshot=comp.snapshot or {"recomendacion":comp.recomendacion},creado_por=context.usuario,actualizado_por=context.usuario)
    for s in selecciones or []:
        oferta=OfertaProveedor.objects.get(pk=s["oferta_id"],empresa=context.empresa);line=LineaOferta.objects.get(oferta=oferta,linea_rfq_id=s["linea_rfq_id"]);qty=Decimal(str(s.get("cantidad",line.cantidad)));DetalleAdjudicacion.objects.create(adjudicacion=a,linea_rfq=line.linea_rfq,oferta=oferta,proveedor=oferta.proveedor,cantidad=qty,precio_unitario=line.precio_unitario,total=(qty*line.precio_unitario).quantize(Decimal("0.01")))
    _audit(context,a,"Adjudicación creada.");_emit(context,AdjudicacionCreada,a,"adjudicacion-creada");return a
def aprobar_adjudicacion(*,context,adjudicacion_id):
    a=AdjudicacionCompra.objects.get(pk=adjudicacion_id,empresa=context.empresa,estado="BORRADOR");old=a.estado;a.estado="APROBADA";a.aprobada_en=timezone.now();a.save();HistorialAdjudicacion.objects.create(adjudicacion=a,estado_anterior=old,estado_nuevo=a.estado,usuario=context.usuario);_emit(context,AdjudicacionAprobada,a,"adjudicacion-aprobada");return a

@transaction.atomic
def crear_orden_desde_adjudicacion(*,context,adjudicacion_id,proveedor_id=None):
    a=AdjudicacionCompra.objects.get(pk=adjudicacion_id,empresa=context.empresa,estado="APROBADA");details=a.detalles.filter(**({"proveedor_id":proveedor_id} if proveedor_id else {}));first=details.select_related("proveedor","oferta__moneda").first()
    if first is None:raise ValidationError("La adjudicación no contiene líneas para el proveedor.")
    if not proveedor_id and details.values("proveedor_id").distinct().count()>1:raise ValidationError("Indique el proveedor para generar una orden por adjudicación múltiple.")
    provider=first.proveedor;currency=first.oferta.moneda;o=OrdenCompraEnterprise.objects.create(empresa=context.empresa,numero=_num(context,"OCE"),adjudicacion=a,proveedor=provider,moneda=currency,tasa_cambio=first.oferta.tasa_cambio,fecha=timezone.localdate(),entrega_desde=timezone.localdate(),entrega_hasta=timezone.localdate()+timedelta(days=30),creado_por=context.usuario,actualizado_por=context.usuario)
    for d in details:DetalleOrdenCompraEnterprise.objects.create(orden=o,linea_adjudicacion=d,producto=d.linea_rfq.producto,descripcion=d.linea_rfq.descripcion,cantidad=d.cantidad,precio_unitario=d.precio_unitario,total=d.total,almacen=d.linea_rfq.almacen_destino)
    o.total=o.detalles.aggregate(v=Sum("total"))["v"] or 0;o.subtotal=o.total;o.save(update_fields=["subtotal","total"]);_emit(context,OrdenCompraCreada,o,"orden-creada");return o
def transicionar_orden(*,context,orden_id,nuevo,comentario=""):
    o=OrdenCompraEnterprise.objects.get(pk=orden_id,empresa=context.empresa);allowed={"BORRADOR":{"PENDIENTE_APROBACION","CANCELADA"},"PENDIENTE_APROBACION":{"APROBADA","BORRADOR","CANCELADA"},"APROBADA":{"ENVIADA","CANCELADA"},"ENVIADA":{"ACEPTADA","CANCELADA"},"ACEPTADA":{"PARCIALMENTE_RECIBIDA","RECIBIDA","CANCELADA"},"PARCIALMENTE_RECIBIDA":{"RECIBIDA","CANCELADA"},"RECIBIDA":{"PARCIALMENTE_FACTURADA","FACTURADA","CERRADA"},"FACTURADA":{"CERRADA"}};
    if nuevo not in allowed.get(o.estado,set()):raise ValidationError("Transición de orden inválida.")
    old=o.estado;o.estado=nuevo;o.save(update_fields=["estado"]);HistorialOrdenCompra.objects.create(orden=o,estado_anterior=old,estado_nuevo=nuevo,comentario=comentario,usuario=context.usuario);event={"APROBADA":OrdenCompraAprobada,"ENVIADA":OrdenCompraEnviada,"ACEPTADA":OrdenCompraAceptada,"CANCELADA":OrdenCompraCancelada}.get(nuevo);_emit(context,event,o,f"orden-{nuevo.lower()}") if event else None;return o
def versionar_orden(*,context,orden_id):
    o=OrdenCompraEnterprise.objects.get(pk=orden_id,empresa=context.empresa);snap={"numero":o.numero,"estado":o.estado,"total":str(o.total),"detalles":list(o.detalles.values("descripcion","cantidad","precio_unitario","total"))};v,_=VersionOrdenCompra.objects.get_or_create(orden=o,version=o.version,defaults={"snapshot":snap,"creado_por":context.usuario});return v

@transaction.atomic
def crear_recepcion(*,context,orden_id,datos):
    o=OrdenCompraEnterprise.objects.get(pk=orden_id,empresa=context.empresa,estado__in=["ACEPTADA","PARCIALMENTE_RECIBIDA"]);r=RecepcionCompra.objects.create(empresa=context.empresa,numero=datos.get("numero") or _num(context,"REC"),orden=o,estado="EN_PROCESO",fecha=datos.get("fecha",timezone.now()),almacen=datos["almacen"],documento_proveedor=datos.get("documento_proveedor",""),creado_por=context.usuario,actualizado_por=context.usuario);_emit(context,RecepcionCreada,r,"recepcion-creada");return r
@transaction.atomic
def agregar_detalle_recepcion(*,context,recepcion_id,detalle_orden_id,cantidad,aceptada=None,rechazada=0,lote="",vence_el=None,motivo=""):
    r=RecepcionCompra.objects.select_for_update().get(pk=recepcion_id,empresa=context.empresa,estado="EN_PROCESO");d=DetalleOrdenCompraEnterprise.objects.select_for_update().get(pk=detalle_orden_id,orden=r.orden);qty=Decimal(str(cantidad));accepted=Decimal(str(aceptada if aceptada is not None else qty-Decimal(str(rechazada))));rejected=Decimal(str(rechazada))
    if qty<=0 or accepted<0 or rejected<0 or accepted+rejected!=qty or d.cantidad_recibida+accepted>d.cantidad:raise ValidationError("Cantidad de recepción inválida.")
    return DetalleRecepcionCompra.objects.create(recepcion=r,detalle_orden=d,cantidad_recibida=qty,cantidad_aceptada=accepted,cantidad_rechazada=rejected,lote=lote,vence_el=vence_el,motivo_diferencia=motivo)
@transaction.atomic
def cerrar_recepcion(*,context,recepcion_id):
    r=RecepcionCompra.objects.select_for_update().select_related("orden").get(pk=recepcion_id,empresa=context.empresa,estado="EN_PROCESO")
    if not r.detalles.exists():raise ValidationError("La recepción no contiene detalles.")
    for x in r.detalles.select_related("detalle_orden__producto"):
        if x.cantidad_aceptada and x.detalle_orden.producto_id:
            lote=None
            if x.lote:lote,_=LoteInventario.objects.get_or_create(empresa=context.empresa,producto=x.detalle_orden.producto,lote=x.lote,defaults={"fecha_ingreso":timezone.localdate(),"fecha_vencimiento":x.vence_el,"cantidad_inicial":0,"cantidad_disponible":0})
            mov=InventoryEngine.apply_movement(context=replace(context,clave_idempotente=f"recepcion:{r.pk}:{x.pk}"),producto=x.detalle_orden.producto,lote=lote,tipo="entrada",cantidad=x.cantidad_aceptada,referencia=r.numero);x.movimiento_inventario_id=mov.pk;x.save(update_fields=["movimiento_inventario_id"]);x.detalle_orden.cantidad_recibida+=x.cantidad_aceptada;x.detalle_orden.save(update_fields=["cantidad_recibida"])
    contabilizar_recepcion_compra(context=replace(context,clave_idempotente=f"recepcion-contable:{r.pk}"),recepcion=r)
    differences=r.detalles.filter(Q(cantidad_rechazada__gt=0)|Q(dañado=True)).exists();complete=all(d.cantidad_recibida>=d.cantidad for d in r.orden.detalles.all());r.estado="CON_DIFERENCIAS" if differences else "COMPLETA" if complete else "PARCIAL";r.cerrada_en=timezone.now();r.save(update_fields=["estado","cerrada_en"]);r.orden.estado="RECIBIDA" if complete else "PARCIALMENTE_RECIBIDA";r.orden.save(update_fields=["estado"]);_audit(context,r,"Recepción procesada.");_emit(context,RecepcionConDiferencias if differences else RecepcionProcesada,r,"recepcion-procesada");return r
@transaction.atomic
def procesar_devolucion(*,context,devolucion_id):
    d=DevolucionCompra.objects.select_for_update().get(pk=devolucion_id,empresa=context.empresa,estado="BORRADOR")
    for x in d.detalles.select_related("detalle_recepcion__detalle_orden__producto"):
        source=x.detalle_recepcion
        if x.cantidad<=0 or x.cantidad>source.cantidad_aceptada:raise ValidationError("Cantidad de devolución inválida.")
        lote=LoteInventario.objects.filter(empresa=context.empresa,producto=source.detalle_orden.producto,lote=source.lote).first();mov=InventoryEngine.apply_movement(context=replace(context,clave_idempotente=f"devolucion:{d.pk}:{x.pk}"),producto=source.detalle_orden.producto,lote=lote,tipo="salida",cantidad=x.cantidad,referencia=d.numero);x.movimiento_inventario_id=mov.pk;x.save(update_fields=["movimiento_inventario_id"]);source.detalle_orden.cantidad_recibida-=x.cantidad;source.detalle_orden.save(update_fields=["cantidad_recibida"])
    contabilizar_devolucion_compra(context=replace(context,clave_idempotente=f"devolucion-contable:{d.pk}"),devolucion=d)
    d.estado="PROCESADA";d.procesada_en=timezone.now();d.save(update_fields=["estado","procesada_en"]);_emit(context,DevolucionCompraProcesada,d,"devolucion-procesada");return d
