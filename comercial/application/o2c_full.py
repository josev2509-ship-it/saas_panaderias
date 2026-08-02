from dataclasses import replace
from decimal import Decimal
import hashlib
from uuid import uuid4
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from core.application.event_bus import event_bus
from core.application.numbering import obtener_siguiente_numero
from inventario.engine import InventoryEngine
from comercial.models import *
from comercial.domain.o2c_full_events import *

def _perm(c,p):
    if not c.usuario or not c.usuario.has_perm(f"comercial.{p}"):raise PermissionDenied
def _num(c,t):return obtener_siguiente_numero(empresa=c.empresa,tipo_documento=t,usuario=c.usuario,context=replace(c,clave_idempotente=f"{c.clave_idempotente or c.identificador_solicitud}:{t}:{uuid4().hex}"))
def _audit(c,o,d,b=None,a=None):registrar_evento(empresa=c.empresa,usuario=c.usuario,request=c.request,objeto=o,modulo="o2c",accion=EventoAuditoria.Accion.OTRO,descripcion=d,datos_anteriores=b,datos_nuevos=a)
def _emit(c,cls,o,suffix,p=None):event_bus.publish(cls(empresa_id=c.empresa.pk,usuario_id=getattr(c.usuario,"pk",None),agregado_tipo=f"comercial.{o.__class__.__name__}",agregado_id=str(o.pk),referencia=getattr(o,"numero",str(o.pk)),clave_idempotente=f"{c.identificador_solicitud}:{suffix}:{o.pk}"[:180],payload={"schema_version":1,"empresa_id":c.empresa.pk,"aggregate_id":o.pk,**(p or {})}))
def _hist(model,obj,usuario,a,n):model.objects.create(**{model._meta.fields[1].name:obj,"estado_anterior":a,"estado_nuevo":n,"usuario":usuario})

def consultar_disponibilidad(*,context,pedido):
    if pedido.empresa_id!=context.empresa.pk:raise ValidationError("Pedido de otra empresa.")
    return [{**InventoryEngine.commercial_availability(context=context,producto=d.producto,cantidad=d.cantidad),"detalle_id":d.pk,"cantidad":d.cantidad} for d in pedido.detalles.select_related("producto")]
consultar_atp=consultar_disponibilidad

@transaction.atomic
def crear_reserva_desde_pedido(*,context,pedido_id,expira_en=None):
    _perm(context,"gestionar_reserva_comercial");p=Pedido.objects.select_for_update().get(pk=pedido_id,empresa=context.empresa,estado__in=[Pedido.Estado.APROBADO,Pedido.Estado.PROGRAMADO]);obj=ReservaComercial.objects.filter(pedido=p).first()
    if obj:return obj
    obj=ReservaComercial.objects.create(empresa=context.empresa,numero=_num(context,"RESC"),pedido=p,estado="PENDIENTE",expira_en=expira_en,creado_por=context.usuario)
    for d in p.detalles.all():DetalleReservaComercial.objects.create(reserva=obj,detalle_pedido=d,producto=d.producto,cantidad_solicitada=d.cantidad)
    HistorialReservaComercial.objects.create(reserva=obj,estado_anterior="",estado_nuevo=obj.estado,usuario=context.usuario);_audit(context,obj,"Reserva comercial creada.");_emit(context,ReservaComercialCreada,obj,"creada");return obj
@transaction.atomic
def reservar_inventario(*,context,reserva_id,permitir_parcial=True):
    _perm(context,"gestionar_reserva_comercial");r=ReservaComercial.objects.select_for_update().get(pk=reserva_id,empresa=context.empresa)
    for d in list(r.detalles.filter(cantidad_reservada=0)):InventoryEngine.reserve_commercial(context=context,detalle=d)
    solicitada=r.pedido.detalles.aggregate(v=Sum("cantidad"))["v"] or 0;reservada=r.detalles.aggregate(v=Sum("cantidad_reservada"))["v"] or 0
    anterior=r.estado;r.estado="COMPLETA" if reservada>=solicitada else "PARCIAL"
    if r.estado=="PARCIAL" and not permitir_parcial:raise ValidationError("Inventario insuficiente y la reserva parcial no está permitida.")
    r.save(update_fields=["estado","actualizado_en"]);HistorialReservaComercial.objects.create(reserva=r,estado_anterior=anterior,estado_nuevo=r.estado,usuario=context.usuario);_audit(context,r,"Inventario reservado.",a={"reservada":str(reservada)});_emit(context,ReservaComercialCompletada,r,"reservada",{"estado":r.estado});return r
completar_reserva=reservar_inventario
@transaction.atomic
def liberar_reserva(*,context,reserva_id,estado="LIBERADA",motivo=""):
    _perm(context,"gestionar_reserva_comercial");r=ReservaComercial.objects.select_for_update().get(pk=reserva_id,empresa=context.empresa);anterior=r.estado;InventoryEngine.release_commercial(context=context,reserva=r);r.estado=estado;r.motivo=motivo;r.save(update_fields=["estado","motivo","actualizado_en"]);HistorialReservaComercial.objects.create(reserva=r,estado_anterior=anterior,estado_nuevo=estado,usuario=context.usuario);_audit(context,r,f"Reserva {estado.lower()}.");_emit(context,{"LIBERADA":ReservaComercialLiberada,"EXPIRADA":ReservaComercialExpirada,"CANCELADA":ReservaComercialCancelada}[estado],r,estado.lower());return r
def expirar_reserva(*,context,reserva_id):return liberar_reserva(context=context,reserva_id=reserva_id,estado="EXPIRADA")
def cancelar_reserva(*,context,reserva_id,motivo):return liberar_reserva(context=context,reserva_id=reserva_id,estado="CANCELADA",motivo=motivo)
def recalcular_reserva(*,context,reserva_id):return reservar_inventario(context=context,reserva_id=reserva_id)

@transaction.atomic
def crear_preparacion(*,context,reserva_id):
    _perm(context,"gestionar_preparacion_o2c");r=ReservaComercial.objects.select_for_update().get(pk=reserva_id,empresa=context.empresa,estado="COMPLETA");obj=PreparacionPedido.objects.filter(reserva=r).first()
    if obj:return obj
    obj=PreparacionPedido.objects.create(empresa=context.empresa,numero=_num(context,"PREP"),pedido=r.pedido,reserva=r,creado_por=context.usuario)
    for d in r.detalles.all():DetallePreparacionPedido.objects.create(preparacion=obj,detalle_reserva=d)
    _audit(context,obj,"Preparación creada.");_emit(context,PreparacionCreada,obj,"creada");return obj
@transaction.atomic
def iniciar_preparacion(*,context,pk):
    o=PreparacionPedido.objects.select_for_update().get(pk=pk,empresa=context.empresa,estado="PENDIENTE");o.estado="EN_PROCESO";o.operador=context.usuario;o.save();_emit(context,PreparacionIniciada,o,"iniciada");return o
@transaction.atomic
def validar_preparacion(*,context,pk):
    o=PreparacionPedido.objects.select_for_update().get(pk=pk,empresa=context.empresa,estado__in=["EN_PROCESO","PREPARADA"])
    for d in o.detalles.all():d.cantidad_preparada=d.detalle_reserva.cantidad_reservada;d.diferencia=0;d.save()
    o.estado="VALIDADA";o.save();_audit(context,o,"Preparación validada.");_emit(context,PreparacionValidada,o,"validada");return o
@transaction.atomic
def generar_picking(*,context,preparacion_id):
    _perm(context,"gestionar_picking_o2c");p=PreparacionPedido.objects.get(pk=preparacion_id,empresa=context.empresa,estado="VALIDADA");o=TareaPicking.objects.filter(preparacion=p).first()
    if o:return o
    o=TareaPicking.objects.create(empresa=context.empresa,preparacion=p,creado_por=context.usuario)
    for d in p.detalles.all():DetallePicking.objects.create(picking=o,detalle_preparacion=d,lote=d.detalle_reserva.lote)
    _emit(context,PickingCreado,o,"creado");return o
@transaction.atomic
def completar_picking(*,context,pk):
    o=TareaPicking.objects.select_for_update().get(pk=pk,empresa=context.empresa);o.operador=context.usuario
    for d in o.detalles.all():d.cantidad=d.detalle_preparacion.cantidad_preparada;d.save()
    o.estado="VALIDADA";o.save();_audit(context,o,"Picking validado.");_emit(context,PickingValidado,o,"validado");return o
@transaction.atomic
def crear_packing(*,context,picking_id):
    _perm(context,"gestionar_packing_o2c");p=TareaPicking.objects.get(pk=picking_id,empresa=context.empresa,estado="VALIDADA");o=PackingPedido.objects.filter(picking=p).first()
    if o:return o
    o=PackingPedido.objects.create(empresa=context.empresa,pedido=p.preparacion.pedido,picking=p,creado_por=context.usuario);_emit(context,PackingCreado,o,"creado");return o
@transaction.atomic
def sellar_packing(*,context,pk,peso=0):
    o=PackingPedido.objects.select_for_update().get(pk=pk,empresa=context.empresa);paquete,_=PaquetePedido.objects.get_or_create(packing=o,codigo=f"PK-{o.pk}-1",defaults={"peso":peso,"sellado":True})
    for d in o.picking.detalles.all():DetallePaquetePedido.objects.get_or_create(paquete=paquete,detalle_picking=d,defaults={"cantidad":d.cantidad})
    o.estado="SELLADO";o.bultos=o.paquetes.count();o.peso_total=sum((p.peso for p in o.paquetes.all()),Decimal(0));o.save();_audit(context,o,"Packing sellado.");_emit(context,PackingSellado,o,"sellado");return o

@transaction.atomic
def crear_despacho(*,context,packing_ids,fecha=None):
    _perm(context,"gestionar_despacho_o2c");packings=list(PackingPedido.objects.select_for_update().filter(pk__in=packing_ids,empresa=context.empresa,estado="SELLADO"));
    if not packings:raise ValidationError("No hay packing válido.")
    o=DespachoComercial.objects.create(empresa=context.empresa,numero=_num(context,"DES"),fecha=fecha or timezone.localdate(),estado="LISTO",creado_por=context.usuario)
    for p in packings:DetalleDespachoComercial.objects.create(despacho=o,pedido=p.pedido,packing=p)
    _audit(context,o,"Despacho creado.");_emit(context,DespachoCreado,o,"creado");return o
@transaction.atomic
def autorizar_despacho(*,context,pk):
    _perm(context,"autorizar_salida_o2c");o=DespachoComercial.objects.select_for_update().get(pk=pk,empresa=context.empresa,estado="LISTO")
    for d in o.detalles.all():InventoryEngine.confirm_commercial_outbound(context=replace(context,clave_idempotente=f"salida:{o.pk}:{d.pk}"),reserva=d.pedido.reserva_comercial,referencia=o.numero);d.pedido.reserva_comercial.estado="CONSUMIDA";d.pedido.reserva_comercial.save(update_fields=["estado"])
    o.estado="DESPACHADO";o.save();_audit(context,o,"Salida autorizada.");_emit(context,DespachoAutorizado,o,"autorizado");return o

@transaction.atomic
def emitir_conduce(*,context,despacho_id):
    _perm(context,"emitir_conduce_o2c");d=DespachoComercial.objects.get(pk=despacho_id,empresa=context.empresa,estado__in=["DESPACHADO","EN_RUTA"]);o=ConduceComercial.objects.filter(despacho=d).first()
    if o:return o
    o=ConduceComercial.objects.create(empresa=context.empresa,numero=_num(context,"COND"),despacho=d,estado="EMITIDO",emitido_en=timezone.now(),qr_token=hashlib.sha256(f"{d.pk}:{d.numero}".encode()).hexdigest(),creado_por=context.usuario)
    for x in d.detalles.select_related("pedido"):
        for l in x.pedido.detalles.all():DetalleConduceComercial.objects.create(conduce=o,detalle_pedido=l,descripcion=l.descripcion,cantidad=l.cantidad,unidad=l.unidad_medida)
    _audit(context,o,"Conduce canónico emitido.");_emit(context,ConduceComercialEmitido,o,"emitido");return o
@transaction.atomic
def confirmar_entrega(*,context,conduce_id,receptor):
    _perm(context,"gestionar_entrega_o2c");c=ConduceComercial.objects.select_for_update().get(pk=conduce_id,empresa=context.empresa,estado__in=["EMITIDO","EN_RUTA"]);o=EntregaComercial.objects.filter(conduce=c).first() or EntregaComercial.objects.create(empresa=context.empresa,numero=_num(context,"ENT"),conduce=c,creado_por=context.usuario)
    for d in c.detalles.all():DetalleEntregaComercial.objects.get_or_create(entrega=o,detalle_conduce=d,defaults={"cantidad_entregada":d.cantidad})
    o.estado="ENTREGADA";o.receptor=receptor;o.confirmada_en=timezone.now();o.save();c.estado="ENTREGADO";c.save();_audit(context,o,"Entrega confirmada.");_emit(context,EntregaConfirmada,o,"confirmada");return o

@transaction.atomic
def crear_factura_desde_entrega(*,context,entrega_id,vence_el,ncf=""):
    e=EntregaComercial.objects.get(pk=entrega_id,empresa=context.empresa,estado="ENTREGADA");pedido=e.conduce.despacho.detalles.first().pedido;existente=FacturaVenta.objects.filter(empresa=context.empresa,entrega=e,estado__in=["EMITIDA","PARCIALMENTE_COBRADA","COBRADA"]).first()
    if existente:return existente
    moneda=pedido.cliente.moneda_comercial;f=FacturaVenta.objects.create(empresa=context.empresa,numero=_num(context,"FACV"),cliente=pedido.cliente,pedido=pedido,entrega=e,moneda=moneda,fecha=timezone.localdate(),vence_el=vence_el,ncf=ncf,creado_por=context.usuario)
    for d in pedido.detalles.all():DetalleFacturaVenta.objects.create(factura=f,detalle_pedido=d,descripcion=d.descripcion,cantidad=d.cantidad,precio=d.precio_unitario,descuento=d.monto_descuento,impuesto=d.monto_impuesto,total=d.total,snapshot={"pedido":pedido.numero,"producto_id":d.producto_id})
    f.subtotal=sum((d.subtotal for d in pedido.detalles.all()),Decimal(0));f.descuento=pedido.descuento_total;f.impuesto=pedido.impuesto_total;f.total=pedido.total;f.save();_audit(context,f,"Factura de venta creada.");_emit(context,FacturaVentaCreada,f,"creada");return f
@transaction.atomic
def emitir_factura(*,context,pk):
    _perm(context,"emitir_factura_venta");f=FacturaVenta.objects.select_for_update().get(pk=pk,empresa=context.empresa,estado="BORRADOR")
    if f.total<=0:raise ValidationError("La factura debe tener total positivo.")
    f.estado="EMITIDA";f.save();HistorialFacturaVenta.objects.create(factura=f,estado_anterior="BORRADOR",estado_nuevo="EMITIDA",usuario=context.usuario);c=CuentaPorCobrar.objects.create(empresa=context.empresa,factura=f,cliente=f.cliente,moneda=f.moneda,fecha_emision=f.fecha,fecha_vencimiento=f.vence_el,monto_original=f.total,saldo=f.total,creado_por=context.usuario);MovimientoCxC.objects.create(cuenta=c,tipo="CARGO",monto=f.total,saldo_anterior=0,saldo_posterior=f.total,referencia=f.numero);_audit(context,f,"Factura emitida y CxC creada.");_emit(context,FacturaVentaEmitida,f,"emitida");_emit(context,CuentaPorCobrarCreada,c,"creada");return f

def _aging(c,hoy=None):
    dias=((hoy or timezone.localdate())-c.fecha_vencimiento).days
    return "CORRIENTE" if dias<=0 else "1_30" if dias<=30 else "31_60" if dias<=60 else "61_90" if dias<=90 else "91_120" if dias<=120 else "MAS_120"
@transaction.atomic
def actualizar_aging_cuenta(*,context,cuenta_id):
    c=CuentaPorCobrar.objects.select_for_update().get(pk=cuenta_id,empresa=context.empresa);c.bucket_aging=_aging(c)
    if c.saldo>0 and c.fecha_vencimiento<timezone.localdate():c.estado="EN_MORA"
    c.save();return c
@transaction.atomic
def registrar_cobro(*,context,cliente,moneda,monto,metodo,fecha=None,referencia=""):
    _perm(context,"registrar_cobro");
    if cliente.empresa_id!=context.empresa.pk or moneda.empresa_id!=context.empresa.pk:raise ValidationError("Datos de otra empresa.")
    o=ReciboCobro.objects.create(empresa=context.empresa,numero=_num(context,"REC"),cliente=cliente,moneda=moneda,fecha=fecha or timezone.localdate(),metodo=metodo,monto=monto,referencia=referencia,estado="REGISTRADO",creado_por=context.usuario);_audit(context,o,"Cobro registrado.");_emit(context,CobroRegistrado,o,"registrado");return o
@transaction.atomic
def aplicar_cobro(*,context,recibo_id,cuenta_id,monto):
    r=ReciboCobro.objects.select_for_update().get(pk=recibo_id,empresa=context.empresa);c=CuentaPorCobrar.objects.select_for_update().get(pk=cuenta_id,empresa=context.empresa,cliente=r.cliente,moneda=r.moneda);m=Decimal(monto)
    if m<=0 or m>c.saldo or r.monto_aplicado+m>r.monto:raise ValidationError("Aplicación de cobro inválida.")
    anterior=c.saldo;c.saldo-=m;c.estado="COBRADA" if c.saldo==0 else "PARCIAL";c.save();AplicacionCobro.objects.create(recibo=r,cuenta=c,monto=m);MovimientoCxC.objects.create(cuenta=c,tipo="COBRO",monto=m,saldo_anterior=anterior,saldo_posterior=c.saldo,referencia=r.numero);r.monto_aplicado+=m;r.estado="APLICADO" if r.monto_aplicado==r.monto else "PARCIALMENTE_APLICADO";r.save();c.factura.estado="COBRADA" if c.saldo==0 else "PARCIALMENTE_COBRADA";c.factura.save();_audit(context,r,"Cobro aplicado.");_emit(context,CobroAplicado,r,f"aplicado-{c.pk}",{"cuenta_id":c.pk,"monto":str(m)});return c

@transaction.atomic
def solicitar_factoring(*,context,cuenta_id,factor,porcentaje):
    _perm(context,"gestionar_factoring_o2c");c=CuentaPorCobrar.objects.get(pk=cuenta_id,empresa=context.empresa);o=CesionFactoring.objects.create(empresa=context.empresa,numero=_num(context,"FACT"),cuenta=c,factor=factor,porcentaje_anticipo=porcentaje,monto_cedido=c.saldo,estado="SOLICITADA",creado_por=context.usuario);_audit(context,o,"Cesión factoring solicitada.");_emit(context,CesionFactoringSolicitada,o,"solicitada");return o

@transaction.atomic
def emitir_nota_credito(*,context,factura_id,monto,motivo,ncf=""):
    f=FacturaVenta.objects.select_for_update().get(pk=factura_id,empresa=context.empresa);m=Decimal(monto)
    if m<=0 or m>f.cuenta_cobrar.saldo:raise ValidationError("Monto de nota inválido.")
    n=NotaCreditoVenta.objects.create(empresa=context.empresa,numero=_num(context,"NC"),factura=f,motivo=motivo,ncf=ncf,estado="EMITIDA",total=m,creado_por=context.usuario);DetalleNotaCreditoVenta.objects.create(nota=n,descripcion=motivo,cantidad=1,monto=m);c=f.cuenta_cobrar;anterior=c.saldo;c.saldo-=m;c.estado="COBRADA" if c.saldo==0 else "PARCIAL";c.save();MovimientoCxC.objects.create(cuenta=c,tipo="NOTA_CREDITO",monto=m,saldo_anterior=anterior,saldo_posterior=c.saldo,referencia=n.numero);f.estado="NOTA_CREDITO_TOTAL" if c.saldo==0 else "NOTA_CREDITO_PARCIAL";f.save();_audit(context,n,"Nota de crédito emitida.");_emit(context,NotaCreditoEmitida,n,"emitida");return n

@transaction.atomic
def avanzar_factoring(*,context,pk,estado,monto=0):
    _perm(context,"gestionar_factoring_o2c");o=CesionFactoring.objects.select_for_update().get(pk=pk,empresa=context.empresa);permitidas={"SOLICITADA":"APROBADA","APROBADA":"CEDIDA","CEDIDA":"PAGADA"}
    if permitidas.get(o.estado)!=estado:raise ValidationError("Transición de factoring inválida.")
    anterior=o.estado;o.estado=estado;o.save();HistorialFactoring.objects.create(cesion=o,estado_anterior=anterior,estado_nuevo=estado,usuario=context.usuario)
    if monto:MovimientoFactoring.objects.create(cesion=o,tipo=estado,monto=monto)
    if estado=="CEDIDA":o.cuenta.estado="CEDIDA_FACTORING";o.cuenta.save();o.cuenta.factura.estado="CEDIDA_FACTORING";o.cuenta.factura.save()
    evento={"APROBADA":CesionFactoringAprobada,"CEDIDA":CesionFactoringCedida,"PAGADA":CesionFactoringPagada}[estado];_audit(context,o,f"Factoring {estado.lower()}.");_emit(context,evento,o,estado.lower());return o
