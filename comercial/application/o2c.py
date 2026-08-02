from dataclasses import dataclass,replace
from decimal import Decimal,ROUND_HALF_UP
import hashlib,json
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.domain.o2c_events import *
from comercial.models import *
from comercial.pedidos_services import calcular_linea,recalcular_pedido,transicionar_pedido
from core.application.event_bus import event_bus
from core.application.numbering import obtener_siguiente_numero

CENT=Decimal("0.01")
def _perm(c,p):
    if not c.usuario or not c.usuario.has_perm(f"comercial.{p}"):raise PermissionDenied
def _audit(c,o,text,before=None,after=None):registrar_evento(empresa=c.empresa,usuario=c.usuario,request=c.request,objeto=o,modulo="comercial_o2c",accion=EventoAuditoria.Accion.OTRO,descripcion=text,datos_anteriores=before,datos_nuevos=after)
def _emit(c,cls,o,suffix,extra=None):
    event_bus.publish(cls(empresa_id=c.empresa.pk,usuario_id=getattr(c.usuario,"pk",None),agregado_tipo=f"comercial.{o.__class__.__name__}",agregado_id=str(o.pk),referencia=getattr(o,"numero",getattr(o,"codigo",str(o.pk))),clave_idempotente=f"{c.identificador_solicitud}:{suffix}:{o.pk}"[:180],payload={"schema_version":1,"empresa_id":c.empresa.pk,"aggregate_id":o.pk,"actor_id":getattr(c.usuario,"pk",None),**(extra or {})}))
def _number(c,tipo):return obtener_siguiente_numero(empresa=c.empresa,tipo_documento=tipo,usuario=c.usuario,context=replace(c,clave_idempotente=c.clave_idempotente or f"o2c-{tipo.lower()}-{c.identificador_solicitud}"))

@dataclass(frozen=True)
class RiesgoClienteDTO:score:int;categoria:str;explicacion:tuple;formula_version:str
@transaction.atomic
def calcular_riesgo_cliente(*,context,cliente_id,persistir=True):
    _perm(context,"calcular_riesgo_cliente");c=Cliente.objects.select_for_update().get(pk=cliente_id,empresa=context.empresa);score=100;razones=[]
    utilizacion=(c.credito_utilizado/c.limite_credito*100) if c.limite_credito else (100 if c.credito_utilizado else 0)
    if utilizacion>90:score-=35;razones.append("Utilización de crédito superior al 90%.")
    elif utilizacion>70:score-=20;razones.append("Utilización de crédito superior al 70%.")
    if c.estado==Cliente.Estado.BLOQUEADO_CREDITO:score-=40;razones.append("Cliente bloqueado por crédito.")
    if not c.rnc_cedula:score-=10;razones.append("Identificación fiscal pendiente.")
    if not c.correo or not c.telefono:score-=10;razones.append("Datos de contacto incompletos.")
    score=max(0,min(100,score));categoria="BAJO" if score>=75 else "MEDIO" if score>=50 else "ALTO";dto=RiesgoClienteDTO(score,categoria,tuple(razones or ["Sin factores adversos detectados."]),"1.0")
    if persistir:c.score_riesgo=score;c.categoria_riesgo=categoria;c.explicacion_riesgo=list(dto.explicacion);c.version_formula_riesgo=dto.formula_version;c.fecha_calculo_riesgo=timezone.now();c.save(update_fields=["score_riesgo","categoria_riesgo","explicacion_riesgo","version_formula_riesgo","fecha_calculo_riesgo","fecha_actualizacion"]);_audit(context,c,"Riesgo de cliente recalculado.",after={"score":score,"categoria":categoria});_emit(context,RiesgoClienteActualizado,c,"riesgo",{"score":score,"categoria":categoria})
    return dto
@transaction.atomic
def cambiar_estado_cliente(*,context,cliente_id,estado,motivo=""):
    _perm(context,"change_cliente");c=Cliente.objects.select_for_update().get(pk=cliente_id,empresa=context.empresa);anterior=c.estado
    if estado not in dict(Cliente.Estado.choices):raise ValidationError("Estado inválido.")
    if estado==Cliente.Estado.BLOQUEADO_CREDITO:_perm(context,"bloquear_credito_cliente")
    c.estado=estado;c.observaciones=(c.observaciones+f"\n{motivo}").strip();c.save();_audit(context,c,f"Cliente: {anterior} → {estado}.");evento={"ACTIVO":ClienteActivado,"SUSPENDIDO":ClienteSuspendido,"BLOQUEADO_CREDITO":ClienteBloqueadoCredito}.get(estado,ClienteDesbloqueadoCredito if anterior=="BLOQUEADO_CREDITO" else ClienteActualizado);_emit(context,evento,c,f"estado-{estado}");return c
@transaction.atomic
def actualizar_limite_credito(*,context,cliente_id,limite):
    _perm(context,"gestionar_credito_cliente");c=Cliente.objects.select_for_update().get(pk=cliente_id,empresa=context.empresa);anterior=c.limite_credito;c.limite_credito=Decimal(limite);c.full_clean();c.save();_audit(context,c,"Límite de crédito actualizado.",{"limite":str(anterior)},{"limite":str(c.limite_credito)});_emit(context,LimiteCreditoActualizado,c,"limite");return c

@transaction.atomic
def crear_producto_comercial(*,context,datos):
    _perm(context,"add_productocomercial");o=ProductoComercial(empresa=context.empresa,**datos);o.full_clean();o.save();_audit(context,o,"Producto comercial creado.");_emit(context,ProductoComercialCreado,o,"creado");return o
@transaction.atomic
def crear_lista_precio(*,context,datos):
    _perm(context,"add_listaprecio");o=ListaPrecio(empresa=context.empresa,creado_por=context.usuario,**datos);o.full_clean();o.save();_audit(context,o,"Lista de precios creada.");_emit(context,ListaPrecioCreada,o,"creada");return o
@transaction.atomic
def activar_lista_precio(*,context,pk):
    _perm(context,"activar_lista_precio");o=ListaPrecio.objects.select_for_update().get(pk=pk,empresa=context.empresa);o.estado="ACTIVA";o.full_clean();o.save(update_fields=["estado"]);_audit(context,o,"Lista de precios activada.");_emit(context,ListaPrecioActivada,o,"activada");return o
@dataclass(frozen=True)
class ResolucionPrecioDTO:precio_base:Decimal;precio_final:Decimal;lista_id:int|None;regla_id:int|None;descuento_permitido:Decimal;promocion_id:int|None;impuesto:Decimal;explicacion:tuple;warnings:tuple;blockers:tuple;hash_resolucion:str
def _regla_aplica(regla,cliente,producto,cantidad):
    c=regla.condiciones
    return (not c.get("producto_id") or int(c["producto_id"])==producto.pk) and (not c.get("cliente_id") or int(c["cliente_id"])==cliente.pk) and Decimal(str(c.get("cantidad_minima",0)))<=cantidad
def resolver_precio_comercial(*,context,cliente,producto,cantidad,fecha=None,moneda=None,canal=None,zona=None,vendedor=None,documento_origen=""):
    _perm(context,"simular_precio_comercial");fecha=fecha or timezone.localdate();cantidad=Decimal(cantidad);blockers=[];warnings=[];exp=[]
    if cliente.empresa_id!=context.empresa.pk or producto.empresa_id!=context.empresa.pk:raise ValidationError("Datos de otra empresa.")
    moneda=moneda or cliente.moneda_comercial or producto.moneda;listas=ListaPrecio.objects.filter(empresa=context.empresa,estado="ACTIVA",moneda=moneda,vigencia_desde__lte=fecha).filter(Q(vigencia_hasta__isnull=True)|Q(vigencia_hasta__gte=fecha)).filter(Q(cliente__isnull=True)|Q(cliente=cliente)).filter(Q(segmento__isnull=True)|Q(segmento=cliente.segmento)).filter(Q(canal__isnull=True)|Q(canal=canal or cliente.canal)).filter(Q(zona__isnull=True)|Q(zona=zona or cliente.zona)).order_by("prioridad","-version")
    candidatos=[]
    for lista in listas:
        for d in lista.detalles.filter(producto=producto,cantidad_minima__lte=cantidad).filter(Q(cantidad_maxima__isnull=True)|Q(cantidad_maxima__gte=cantidad)):candidatos.append((lista,d))
    if candidatos and len([x for x in candidatos if x[0].prioridad==candidatos[0][0].prioridad])>1:blockers.append("Resolución ambigua: más de un precio con igual prioridad.")
    lista,detalle=candidatos[0] if candidatos else (None,None);base=detalle.precio if detalle else producto.precio_base
    if not detalle:warnings.append("Se utilizó el precio base del producto.")
    final=base;regla_aplicada=None
    for regla in ReglaPrecio.objects.filter(empresa=context.empresa,activa=True,vigencia_desde__lte=fecha).filter(Q(vigencia_hasta__isnull=True)|Q(vigencia_hasta__gte=fecha)).order_by("prioridad"):
        if _regla_aplica(regla,cliente,producto,cantidad):
            if regla_aplicada and regla.prioridad==regla_aplicada.prioridad:blockers.append("Reglas de precio ambiguas.");break
            regla_aplicada=regla;valor=Decimal(str(regla.accion.get("valor",0)))
            if regla.tipo in ("FIJO","ESPECIAL"):final=valor
            elif regla.tipo=="DESCUENTO":final*=1-valor/100
            elif regla.tipo=="RECARGO":final*=1+valor/100
            exp.append(f"Regla {regla.codigo} aplicada.")
    promo_id=None
    for promo in PromocionComercial.objects.filter(empresa=context.empresa,activa=True,vigencia_desde__lte=fecha,vigencia_hasta__gte=fecha).order_by("prioridad"):
        rp=promo.reglas.filter(Q(producto__isnull=True)|Q(producto=producto),cantidad_minima__lte=cantidad).first()
        if rp:final=rp.precio_especial if rp.precio_especial is not None else final*(1-rp.porcentaje_descuento/100);promo_id=promo.pk;exp.append(f"Promoción {promo.codigo} aplicada.");break
    impuesto=Decimal("0") if cliente.exento_impuestos else Decimal(getattr(producto.impuesto,"tasa",0) or 0);final=final.quantize(Decimal("0.0001"),rounding=ROUND_HALF_UP);payload={"empresa":context.empresa.pk,"cliente":cliente.pk,"producto":producto.pk,"cantidad":str(cantidad),"fecha":fecha.isoformat(),"moneda":moneda.pk,"base":str(base),"final":str(final),"lista":getattr(lista,"pk",None),"regla":getattr(regla_aplicada,"pk",None),"promocion":promo_id};digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest();dto=ResolucionPrecioDTO(base,final,getattr(lista,"pk",None),getattr(regla_aplicada,"pk",None),cliente.descuento_maximo,promo_id,impuesto,tuple(exp),tuple(warnings),tuple(blockers),digest);_audit(context,producto,"Precio comercial resuelto.",after={"hash":digest,"precio":str(final)});_emit(context,PrecioResuelto,producto,f"precio-{digest[:12]}",{"hash":digest,"precio":str(final)});return dto

def _recalcular_linea(linea):
    bruto=Decimal(linea.cantidad)*Decimal(linea.precio_unitario);linea.subtotal=bruto.quantize(CENT);linea.descuento=(bruto*Decimal(linea.porcentaje_descuento)/100).quantize(CENT);base=linea.subtotal-linea.descuento;linea.impuesto=(base*Decimal(linea.porcentaje_impuesto)/100).quantize(CENT);linea.total=(base+linea.impuesto).quantize(CENT);return linea
@transaction.atomic
def crear_cotizacion(*,context,datos):
    _perm(context,"add_cotizacionventa");o=CotizacionVenta(empresa=context.empresa,numero=_number(context,"COT"),creado_por=context.usuario,actualizado_por=context.usuario,**datos);o.full_clean();o.save();HistorialCotizacionVenta.objects.create(empresa=context.empresa,cotizacion=o,estado_anterior="",estado_nuevo=o.estado,usuario=context.usuario);_audit(context,o,"Cotización creada.");_emit(context,CotizacionCreada,o,"creada");return o
@transaction.atomic
def agregar_linea_cotizacion(*,context,cotizacion_id,producto,cantidad,resolucion,descuento=Decimal("0")):
    _perm(context,"change_cotizacionventa");c=CotizacionVenta.objects.select_for_update().get(pk=cotizacion_id,empresa=context.empresa,estado="BORRADOR")
    if producto.empresa_id!=context.empresa.pk:raise ValidationError("Producto de otra empresa.")
    if resolucion.blockers:raise ValidationError({"precio":list(resolucion.blockers)})
    if Decimal(descuento)>resolucion.descuento_permitido:raise ValidationError({"descuento":"Supera el descuento autorizado; requiere Workflow."})
    l=DetalleCotizacionVenta(cotizacion=c,producto=producto,descripcion=producto.nombre,cantidad=cantidad,precio_unitario=resolucion.precio_final,porcentaje_descuento=descuento,porcentaje_impuesto=resolucion.impuesto,hash_precio=resolucion.hash_resolucion,snapshot={"producto_id":producto.pk,"codigo":producto.codigo,"nombre":producto.nombre,"precio":str(resolucion.precio_final),"impuesto":str(resolucion.impuesto),"hash":resolucion.hash_resolucion});_recalcular_linea(l);l.full_clean();l.save();recalcular_cotizacion(context=context,cotizacion_id=c.pk);return l
@transaction.atomic
def recalcular_cotizacion(*,context,cotizacion_id):
    c=CotizacionVenta.objects.select_for_update().get(pk=cotizacion_id,empresa=context.empresa);lineas=list(c.detalles.all());c.subtotal=sum((x.subtotal for x in lineas),Decimal(0));c.descuento_total=sum((x.descuento for x in lineas),Decimal(0));c.impuesto_total=sum((x.impuesto for x in lineas),Decimal(0));c.total=sum((x.total for x in lineas),Decimal(0));c.save(update_fields=["subtotal","descuento_total","impuesto_total","total","fecha_actualizacion"]);return c
TRANS_COT={"revision":("BORRADOR","EN_REVISION",CotizacionEnviadaRevision),"aprobar":("EN_REVISION","APROBADA_INTERNA",CotizacionAprobada),"devolver":("EN_REVISION","BORRADOR",CotizacionActualizada),"enviar":("APROBADA_INTERNA","ENVIADA",CotizacionEnviada),"aceptar":("ENVIADA","ACEPTADA",CotizacionAceptada),"rechazar":("ENVIADA","RECHAZADA",CotizacionRechazada),"vencer":("ENVIADA","VENCIDA",CotizacionVencida),"cancelar":("BORRADOR","CANCELADA",CotizacionCancelada)}
@transaction.atomic
def transicionar_cotizacion(*,context,pk,accion,comentario=""):
    c=CotizacionVenta.objects.select_for_update().get(pk=pk,empresa=context.empresa);_perm(context,"aprobar_cotizacion_venta" if accion=="aprobar" else "change_cotizacionventa")
    if accion not in TRANS_COT:raise ValidationError("Acción no permitida.")
    origen,destino,evento=TRANS_COT[accion]
    if c.estado!=origen:raise ValidationError("Estado no admite la transición.")
    if accion=="revision" and not c.detalles.exists():raise ValidationError("La cotización requiere líneas.")
    c.estado=destino
    if accion=="aprobar":c.aprobado_por=context.usuario
    c.save();HistorialCotizacionVenta.objects.create(empresa=context.empresa,cotizacion=c,estado_anterior=origen,estado_nuevo=destino,usuario=context.usuario,comentario=comentario);_audit(context,c,f"Cotización: {origen} → {destino}.");_emit(context,evento,c,f"estado-{destino}");return c
@transaction.atomic
def versionar_cotizacion(*,context,pk,motivo):
    _perm(context,"versionar_cotizacion_venta");c=CotizacionVenta.objects.select_for_update().get(pk=pk,empresa=context.empresa);data={"numero":c.numero,"version":c.version,"estado":c.estado,"cliente_id":c.cliente_id,"totales":{"subtotal":str(c.subtotal),"descuento":str(c.descuento_total),"impuesto":str(c.impuesto_total),"total":str(c.total)},"lineas":[x.snapshot for x in c.detalles.all()]};raw=json.dumps(data,sort_keys=True);v=VersionCotizacionVenta.objects.create(empresa=context.empresa,cotizacion=c,version=c.version,snapshot=data,hash_contenido=hashlib.sha256(raw.encode()).hexdigest(),motivo=motivo,creado_por=context.usuario);c.version+=1;c.estado="BORRADOR";c.save(update_fields=["version","estado","fecha_actualizacion"]);_audit(context,c,"Cotización versionada.");_emit(context,CotizacionVersionada,c,f"version-{c.version}",{"snapshot_id":v.pk});return c
@transaction.atomic
def convertir_cotizacion_a_pedido(*,context,pk,fecha_entrega,direccion=None):
    _perm(context,"convertir_cotizacion_venta");c=CotizacionVenta.objects.select_for_update().get(pk=pk,empresa=context.empresa)
    existente=Pedido.objects.filter(empresa=context.empresa,cotizacion_origen=c).first()
    if existente:return existente
    if c.estado!="ACEPTADA":raise ValidationError("Solo se convierte una cotización aceptada.")
    cliente=c.cliente
    if cliente.estado!=Cliente.Estado.ACTIVO or cliente.credito_disponible<c.total:raise ValidationError("Cliente o crédito no habilitado.")
    p=Pedido.objects.create(empresa=context.empresa,cotizacion_origen=c,numero=_number(context,"PED"),cliente=cliente,direccion_entrega=direccion,fecha_pedido=timezone.localdate(),fecha_entrega=fecha_entrega,prioridad="NORMAL",condicion_pago=cliente.condicion_pago,dias_credito=cliente.dias_credito,lista_precio="",moneda=getattr(c.moneda.moneda,"codigo","DOP")[:3],creado_por=context.usuario,actualizado_por=context.usuario)
    for x in c.detalles.all():d=DetallePedido(pedido=p,producto=x.producto.producto_inventario,descripcion=x.snapshot.get("nombre",x.descripcion),cantidad=x.cantidad,unidad_medida=x.producto.unidad_venta,precio_unitario=x.precio_unitario,porcentaje_descuento=x.porcentaje_descuento,porcentaje_impuesto=x.porcentaje_impuesto,observaciones=f"Cotización {c.numero} v{c.version}");calcular_linea(d);d.save()
    recalcular_pedido(p);c.estado="CONVERTIDA";c.save(update_fields=["estado"]);HistorialCotizacionVenta.objects.create(empresa=context.empresa,cotizacion=c,estado_anterior="ACEPTADA",estado_nuevo="CONVERTIDA",usuario=context.usuario);_audit(context,p,"Pedido creado desde cotización.",after={"cotizacion_id":c.pk});_emit(context,PedidoCreadoDesdeCotizacion,p,"desde-cotizacion",{"cotizacion_id":c.pk});_emit(context,CotizacionConvertida,c,"convertida",{"pedido_id":p.pk});return p
@transaction.atomic
def aprobar_pedido_o2c(*,context,pk):
    p=Pedido.objects.select_for_update().get(pk=pk,empresa=context.empresa)
    if p.cliente.estado!=Cliente.Estado.ACTIVO or p.cliente.credito_disponible<p.total:raise ValidationError("Crédito insuficiente o cliente no activo.")
    p=transicionar_pedido(pedido=p,empresa=context.empresa,usuario=context.usuario,accion="aprobar",request=context.request);_emit(context,PedidoAprobado,p,"aprobado");return p
@transaction.atomic
def programar_pedido(*,context,pk,fecha,ruta=None,zona=None,vendedor=None,motivo=""):
    _perm(context,"programar_pedido_comercial");p=Pedido.objects.select_for_update().get(pk=pk,empresa=context.empresa,estado=Pedido.Estado.APROBADO);obj,created=ProgramacionPedido.objects.update_or_create(empresa=context.empresa,pedido=p,defaults={"fecha_programada":fecha,"ruta":ruta,"zona":zona,"vendedor":vendedor,"estado":"PROGRAMADA","motivo":motivo,"creado_por":context.usuario,"actualizado_por":context.usuario});p.estado=Pedido.Estado.PROGRAMADO;p.save(update_fields=["estado","fecha_actualizacion"]);_audit(context,obj,"Pedido programado.");_emit(context,PedidoProgramado,p,"programado",{"fecha":fecha.isoformat()});_emit(context,DemandaComercialPublicada,p,"demanda",{"fecha":fecha.isoformat(),"lineas":p.detalles.count()});return obj

@transaction.atomic
def reprogramar_pedido(*,context,pk,fecha,motivo):
    _perm(context,"reprogramar_pedido_comercial");p=Pedido.objects.select_for_update().get(pk=pk,empresa=context.empresa,estado=Pedido.Estado.PROGRAMADO);obj=ProgramacionPedido.objects.select_for_update().get(empresa=context.empresa,pedido=p);obj.fecha_programada=fecha;obj.estado="REPROGRAMADA";obj.motivo=motivo;obj.actualizado_por=context.usuario;obj.full_clean();obj.save();_audit(context,obj,"Pedido reprogramado.");_emit(context,PedidoReprogramado,p,"reprogramado",{"fecha":fecha.isoformat()});return obj
