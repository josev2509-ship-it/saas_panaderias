from decimal import Decimal
from dataclasses import replace

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from contabilidad.models import (AnticipoProveedor, AplicacionAnticipoProveedor,AplicacionNotaProveedor,AplicacionPago, CuentaPorPagarEnterprise,
    CuotaCxP, DetalleFacturaProveedor, FacturaProveedor, HistorialNotaProveedor,MovimientoCxP,
    NotaCreditoProveedor, NotaDebitoProveedor, OrdenPago, PagoMasivo, SolicitudPago)
from contabilidad.cxp_services import registrar_factura,aplicar_pago
from core.application.numbering import obtener_siguiente_numero
from compras.models import OrdenCompraEnterprise,RecepcionCompra
from compras.domain.p2p_events import (AnticipoProveedorIntegrado, FacturaProveedorIntegrada,
    NotaCreditoProveedorIntegrada, NotaDebitoProveedorIntegrada, PagoMasivoProcesado,
    PagoProveedorIntegrado, PagoProveedorReversado)
from core.application.event_bus import event_bus

def _event(context,cls,obj,key,payload=None):event_bus.publish(cls(empresa_id=context.empresa.pk,usuario_id=getattr(context.usuario,"pk",None),agregado_tipo=f"contabilidad.{obj._meta.model_name}",agregado_id=str(obj.pk),referencia=str(obj.pk),clave_idempotente=key,payload={"schema_version":1,"empresa_id":context.empresa.pk,**(payload or {})}))

@transaction.atomic
def crear_factura_proveedor(*,context,orden_id,recepcion_id,datos,lineas):
    orden=OrdenCompraEnterprise.objects.select_for_update().get(pk=orden_id,empresa=context.empresa,estado__in=["RECIBIDA","PARCIALMENTE_RECIBIDA"]);recepcion=RecepcionCompra.objects.get(pk=recepcion_id,empresa=context.empresa,orden=orden,estado__in=["PARCIAL","COMPLETA","CON_DIFERENCIAS"])
    if FacturaProveedor.objects.filter(empresa=context.empresa,proveedor=orden.proveedor,numero=datos["numero"]).exists():raise ValidationError("Factura duplicada para el proveedor.")
    subtotal=sum((Decimal(str(x["cantidad"]))*Decimal(str(x["precio"])) for x in lineas),Decimal(0));descuentos=Decimal(str(datos.get("descuentos",0)));impuesto=Decimal(str(datos.get("impuesto",0)));retenciones=Decimal(str(datos.get("retenciones",0)));cargos=Decimal(str(datos.get("cargos",0)));anticipos=Decimal(str(datos.get("anticipos_aplicados",0)));total=subtotal-descuentos+impuesto+cargos-retenciones-anticipos
    if total<=0:raise ValidationError("El total de la factura debe ser positivo.")
    f=FacturaProveedor.objects.create(empresa=context.empresa,proveedor=orden.proveedor,orden=orden,recepcion=recepcion,numero=datos["numero"],ncf=datos.get("ncf",""),fecha=datos.get("fecha",timezone.localdate()),vence_el=datos["vence_el"],moneda=orden.moneda,tasa_cambio=datos.get("tasa_cambio",orden.tasa_cambio),subtotal=subtotal,descuentos=descuentos,impuesto=impuesto,retenciones=retenciones,cargos=cargos,anticipos_aplicados=anticipos,total=total,estado="REGISTRADA",dimensiones=orden.dimensiones,creado_por=context.usuario)
    for x in lineas:
        detail=orden.detalles.get(pk=x["detalle_orden_id"]);qty=Decimal(str(x["cantidad"]));price=Decimal(str(x["precio"]));
        if qty<=0 or detail.cantidad_facturada+qty>detail.cantidad_recibida:raise ValidationError("La factura excede la cantidad recibida.")
        DetalleFacturaProveedor.objects.create(factura=f,detalle_orden=detail,descripcion=detail.descripcion,cantidad=qty,precio=price,descuento=x.get("descuento",0),impuesto=x.get("impuesto",0),total=(qty*price-Decimal(str(x.get("descuento",0)))+Decimal(str(x.get("impuesto",0)))).quantize(Decimal("0.01")));detail.cantidad_facturada+=qty;detail.save(update_fields=["cantidad_facturada"])
    return f

@transaction.atomic
def validar_e_integrar_factura(*,context,factura_id):
    f=FacturaProveedor.objects.select_for_update().get(pk=factura_id,empresa=context.empresa,estado__in=["REGISTRADA","OBSERVADA"])
    if not f.detalles.exists():raise ValidationError("La factura no contiene detalles.")
    f.estado="VALIDADA";f.save(update_fields=["estado"]);cuenta=registrar_factura(context=context,factura=f);f.orden.estado="FACTURADA" if all(x.cantidad_facturada>=x.cantidad for x in f.orden.detalles.all()) else "PARCIALMENTE_FACTURADA";f.orden.save(update_fields=["estado"]);_event(context,FacturaProveedorIntegrada,f,f"p2p-factura-integrada:{f.pk}",{"cxp_id":cuenta.pk,"total":str(f.total)});return cuenta

def actualizar_aging_cxp(*,empresa,hoy=None):
    hoy=hoy or timezone.localdate();result=[]
    for c in CuentaPorPagarEnterprise.objects.filter(empresa=empresa).exclude(estado__in=["PAGADA","CANCELADA"]):
        days=(hoy-c.vence_el).days;c.bucket_aging="CORRIENTE" if days<=0 else "1_30" if days<=30 else "31_60" if days<=60 else "61_90" if days<=90 else "91_120" if days<=120 else "MAS_120";c.estado="VENCIDA" if days>0 and c.saldo>0 else c.estado;c.save(update_fields=["bucket_aging","estado"]);result.append(c)
    return result

@transaction.atomic
def crear_solicitud_pago(*,context,cuenta_id,monto):
    c=CuentaPorPagarEnterprise.objects.get(pk=cuenta_id,empresa=context.empresa,bloqueada=False);amount=Decimal(str(monto));
    if amount<=0 or amount>c.saldo:raise ValidationError("Monto de solicitud inválido.")
    return SolicitudPago.objects.create(empresa=context.empresa,cuenta=c,monto=amount,estado="PENDIENTE_APROBACION",creado_por=context.usuario)
def aprobar_solicitud_y_orden(*,context,solicitud_id):
    s=SolicitudPago.objects.get(pk=solicitud_id,empresa=context.empresa,estado="PENDIENTE_APROBACION");s.estado="APROBADA";s.save(update_fields=["estado"]);numero=obtener_siguiente_numero(empresa=context.empresa,tipo_documento="OP",usuario=context.usuario,context=replace(context,clave_idempotente=f"orden-pago:{s.pk}"));return OrdenPago.objects.create(empresa=context.empresa,numero=numero,solicitud=s,estado="APROBADA",creado_por=context.usuario)
def pagar_orden(*,context,orden_id,cuenta_bancaria=None,caja=None,monto=0,referencia="",metodo="TRANSFERENCIA",retencion=0):
    orden=OrdenPago.objects.get(pk=orden_id,empresa=context.empresa,estado__in=["APROBADA","PARCIAL","PAGADA"]);mov=aplicar_pago(context=context,orden=orden,cuenta_bancaria=cuenta_bancaria,caja=caja,monto=monto,referencia=referencia);orden.metodo=metodo;orden.referencia=referencia;orden.retencion=retencion;orden.movimiento_tesoreria_id=mov.pk;orden.save(update_fields=["metodo","referencia","retencion","movimiento_tesoreria_id"]);_event(context,PagoProveedorIntegrado,orden,f"p2p-pago:{orden.pk}:{mov.pk}",{"movimiento_id":mov.pk,"monto":str(monto),"metodo":metodo,"retencion":str(retencion)});return mov

@transaction.atomic
def crear_nota_credito(*,context,factura_id,numero,monto,motivo,impuesto=0,retencion=0):
    from contabilidad.api import contabilizar_nota_credito_proveedor
    factura=FacturaProveedor.objects.select_for_update().get(pk=factura_id,empresa=context.empresa,estado__in=["VALIDADA","PARCIALMENTE_PAGADA","PAGADA"]);amount=Decimal(str(monto))
    if amount<=0 or amount>factura.total:raise ValidationError("Monto de nota de crédito inválido.")
    nota=NotaCreditoProveedor.objects.create(empresa=context.empresa,factura=factura,numero=numero,monto=amount,impuesto=impuesto,retencion=retencion,motivo=motivo,creado_por=context.usuario);cuenta=CuentaPorPagarEnterprise.objects.select_for_update().get(factura=factura,empresa=context.empresa);anterior=cuenta.saldo;cuenta.saldo=max(Decimal(0),cuenta.saldo-amount);cuenta.estado="PAGADA" if cuenta.saldo==0 else "PARCIAL";cuenta.save(update_fields=["saldo","estado"]);MovimientoCxP.objects.create(cuenta=cuenta,tipo="NOTA_CREDITO",monto=-amount,saldo_anterior=anterior,saldo_posterior=cuenta.saldo);dto=contabilizar_nota_credito_proveedor(context=context,nota=nota);nota.asiento_id=dto.asiento_id;nota.save(update_fields=["asiento_id"]);_event(context,NotaCreditoProveedorIntegrada,nota,f"p2p-nc:{nota.pk}",{"factura_id":factura.pk,"monto":str(amount)});return nota

@transaction.atomic
def crear_nota_debito(*,context,factura_id,numero,monto,motivo,impuesto=0):
    from contabilidad.api import contabilizar_nota_debito_proveedor
    factura=FacturaProveedor.objects.select_for_update().get(pk=factura_id,empresa=context.empresa,estado__in=["VALIDADA","PARCIALMENTE_PAGADA"]);amount=Decimal(str(monto))
    if amount<=0:raise ValidationError("Monto de nota de débito inválido.")
    nota=NotaDebitoProveedor.objects.create(empresa=context.empresa,factura=factura,numero=numero,monto=amount,impuesto=impuesto,motivo=motivo,creado_por=context.usuario);cuenta=CuentaPorPagarEnterprise.objects.select_for_update().get(factura=factura,empresa=context.empresa);anterior=cuenta.saldo;cuenta.saldo+=amount;cuenta.monto_original+=amount;cuenta.estado="PENDIENTE";cuenta.save(update_fields=["saldo","monto_original","estado"]);MovimientoCxP.objects.create(cuenta=cuenta,tipo="NOTA_DEBITO",monto=amount,saldo_anterior=anterior,saldo_posterior=cuenta.saldo);dto=contabilizar_nota_debito_proveedor(context=context,nota=nota);nota.asiento_id=dto.asiento_id;nota.save(update_fields=["asiento_id"]);_event(context,NotaDebitoProveedorIntegrada,nota,f"p2p-nd:{nota.pk}",{"factura_id":factura.pk,"monto":str(amount)});return nota

@transaction.atomic
def crear_anticipo(*,context,proveedor,moneda,monto,referencia):
    from contabilidad.api import contabilizar_anticipo_proveedor
    amount=Decimal(str(monto))
    if amount<=0 or proveedor.empresa_id!=context.empresa.pk or moneda.empresa_id!=context.empresa.pk:raise ValidationError("Anticipo inválido.")
    anticipo=AnticipoProveedor.objects.create(empresa=context.empresa,proveedor=proveedor,moneda=moneda,monto=amount,saldo=amount,referencia=referencia,creado_por=context.usuario);contabilizar_anticipo_proveedor(context=context,anticipo=anticipo);_event(context,AnticipoProveedorIntegrado,anticipo,f"p2p-anticipo:{anticipo.pk}");return anticipo

def crear_anticipo_borrador(*,context,proveedor,moneda,monto,referencia):
    amount=Decimal(str(monto))
    if amount<=0 or proveedor.empresa_id!=context.empresa.pk or moneda.empresa_id!=context.empresa.pk:raise ValidationError("Anticipo inválido.")
    return AnticipoProveedor.objects.create(empresa=context.empresa,proveedor=proveedor,moneda=moneda,monto=amount,saldo=amount,estado="BORRADOR",referencia=referencia,creado_por=context.usuario)

@transaction.atomic
def decidir_anticipo(*,context,anticipo_id,decision,motivo=""):
    from contabilidad.api import contabilizar_anticipo_proveedor
    obj=AnticipoProveedor.objects.select_for_update().get(pk=anticipo_id,empresa=context.empresa,estado__in=["BORRADOR","PENDIENTE_APROBACION"])
    if decision=="APROBAR":obj.estado="DISPONIBLE";obj.save(update_fields=["estado"]);contabilizar_anticipo_proveedor(context=context,anticipo=obj);_event(context,AnticipoProveedorIntegrado,obj,f"p2p-anticipo-aprobado:{obj.pk}")
    elif decision=="RECHAZAR" and motivo:obj.estado="RECHAZADO";obj.save(update_fields=["estado"])
    else:raise ValidationError("Decisión o motivo inválido.")
    return obj

@transaction.atomic
def anular_anticipo(*,context,anticipo_id,motivo):
    obj=AnticipoProveedor.objects.select_for_update().get(pk=anticipo_id,empresa=context.empresa)
    if not motivo or obj.saldo!=obj.monto or obj.estado not in ["BORRADOR","DISPONIBLE","RECHAZADO"]:raise ValidationError("El anticipo no puede anularse.")
    obj.estado="ANULADO";obj.save(update_fields=["estado"]);return obj

@transaction.atomic
def aplicar_anticipo(*,context,anticipo_id,cuenta_id,monto,clave_idempotencia=None,tasa_cambio=1):
    clave=clave_idempotencia or context.clave_idempotente
    existente=AplicacionAnticipoProveedor.objects.filter(anticipo_id=anticipo_id,clave_idempotencia=clave).first()
    if existente:return existente.anticipo
    anticipo=AnticipoProveedor.objects.select_for_update().get(pk=anticipo_id,empresa=context.empresa,estado="DISPONIBLE");cuenta=CuentaPorPagarEnterprise.objects.select_for_update().get(pk=cuenta_id,empresa=context.empresa,proveedor=anticipo.proveedor,moneda=anticipo.moneda);amount=Decimal(str(monto))
    if amount<=0 or amount>anticipo.saldo or amount>cuenta.saldo:raise ValidationError("Aplicación de anticipo inválida.")
    tasa=Decimal(str(tasa_cambio));base=(amount*tasa).quantize(Decimal("0.01"));anterior=cuenta.saldo;anticipo.saldo-=amount;anticipo.estado="APLICADO" if anticipo.saldo==0 else "DISPONIBLE";anticipo.save(update_fields=["saldo","estado"]);cuenta.saldo-=amount;cuenta.estado="PAGADA" if cuenta.saldo==0 else "PARCIAL";cuenta.save(update_fields=["saldo","estado"]);MovimientoCxP.objects.create(cuenta=cuenta,tipo="ANTICIPO",monto=-amount,saldo_anterior=anterior,saldo_posterior=cuenta.saldo);AplicacionAnticipoProveedor.objects.create(anticipo=anticipo,cuenta=cuenta,monto=amount,tasa_cambio=tasa,diferencia_cambiaria=base-amount,clave_idempotencia=clave);return anticipo

@transaction.atomic
def revertir_aplicacion_anticipo(*,context,aplicacion_id,motivo):
    if not motivo:raise ValidationError("El motivo es obligatorio.")
    app=AplicacionAnticipoProveedor.objects.select_for_update().select_related("anticipo","cuenta").get(pk=aplicacion_id,anticipo__empresa=context.empresa,revertida=False);anticipo=app.anticipo;cuenta=app.cuenta;anterior=cuenta.saldo;anticipo.saldo+=app.monto;anticipo.estado="DISPONIBLE";anticipo.save(update_fields=["saldo","estado"]);cuenta.saldo+=app.monto;cuenta.estado="PENDIENTE";cuenta.save(update_fields=["saldo","estado"]);MovimientoCxP.objects.create(cuenta=cuenta,tipo="REVERSO_ANTICIPO",monto=app.monto,saldo_anterior=anterior,saldo_posterior=cuenta.saldo);app.revertida=True;app.save(update_fields=["revertida"]);return app

@transaction.atomic
def procesar_pago_masivo(*,context,entradas,cuenta_bancaria=None,caja=None):
    total=sum((Decimal(str(x["monto"])) for x in entradas),Decimal(0));lote=PagoMasivo.objects.create(empresa=context.empresa,numero=obtener_siguiente_numero(empresa=context.empresa,tipo_documento="PM",usuario=context.usuario,context=replace(context,clave_idempotente=f"pago-masivo:{context.clave_idempotente}")),estado="EN_PROCESO",total=total,creado_por=context.usuario);result=[]
    for item in entradas:
        mov=pagar_orden(context=replace(context,clave_idempotente=f"{context.clave_idempotente}:{item['orden_id']}"),orden_id=item["orden_id"],cuenta_bancaria=cuenta_bancaria,caja=caja,monto=item["monto"],referencia=item.get("referencia",lote.numero));result.append(mov.pk)
    lote.estado="PROCESADO";lote.procesados=len(result);lote.resultado={"movimientos":result};lote.save(update_fields=["estado","procesados","resultado"]);_event(context,PagoMasivoProcesado,lote,f"p2p-pago-masivo:{lote.pk}");return lote

@transaction.atomic
def revertir_pago(*,context,orden_id,motivo):
    from contabilidad.api import revertir_documento
    from tesoreria.api import revertir_egreso
    orden=OrdenPago.objects.select_for_update().get(pk=orden_id,empresa=context.empresa,estado__in=["PAGADA","PARCIAL"]);aplicacion=AplicacionPago.objects.filter(orden=orden).order_by("-pk").first()
    if not aplicacion:raise ValidationError("La orden no contiene pagos reversibles.")
    from tesoreria.models import MovimientoTesoreria
    original=MovimientoTesoreria.objects.filter(empresa=context.empresa,tipo="EGRESO",referencia__startswith=f"PAGO_PROVEEDOR:{orden.pk}:").order_by("-pk").first()
    if not original:raise ValidationError("No existe movimiento de tesorería reversible.")
    origen_id=original.referencia.removeprefix("PAGO_PROVEEDOR:");mov_dto=revertir_egreso(context=context,origen_tipo="PAGO_PROVEEDOR",origen_id=origen_id,motivo=motivo);cuenta=CuentaPorPagarEnterprise.objects.select_for_update().get(pk=aplicacion.cuenta_id);anterior=cuenta.saldo;cuenta.saldo+=aplicacion.monto;cuenta.estado="PENDIENTE" if cuenta.saldo==cuenta.monto_original else "PARCIAL";cuenta.save(update_fields=["saldo","estado"]);MovimientoCxP.objects.create(cuenta=cuenta,tipo="REVERSO_PAGO",monto=aplicacion.monto,saldo_anterior=anterior,saldo_posterior=cuenta.saldo);orden.estado="REVERSADA";orden.save(update_fields=["estado"]);revertir_documento(context=context,origen_tipo="PAGO_PROVEEDOR",origen_id=original.pk,motivo=motivo);_event(context,PagoProveedorReversado,orden,f"p2p-pago-reversado:{orden.pk}:{original.pk}",{"movimiento_reverso_id":mov_dto.id});return mov_dto

def reporte_cxp(*,empresa,moneda=None,proveedor=None,estado=None):
    qs=CuentaPorPagarEnterprise.objects.filter(empresa=empresa).select_related("proveedor","factura","moneda__moneda").prefetch_related("movimientos")
    if moneda:qs=qs.filter(moneda_id=getattr(moneda,"pk",moneda))
    if proveedor:qs=qs.filter(proveedor_id=getattr(proveedor,"pk",proveedor))
    if estado:qs=qs.filter(estado=estado)
    return list(qs.order_by("vence_el","pk"))

@transaction.atomic
def crear_nota_borrador(*,context,tipo,factura_id,numero,monto,motivo,impuesto=0,retencion=0,concepto="RECARGO"):
    factura=FacturaProveedor.objects.get(pk=factura_id,empresa=context.empresa);amount=Decimal(str(monto));cls=NotaCreditoProveedor if tipo=="CREDITO" else NotaDebitoProveedor
    if amount<=0:raise ValidationError("Monto de nota inválido.")
    extra={"saldo_disponible":amount,"retencion":retencion} if tipo=="CREDITO" else {"concepto":concepto};nota=cls.objects.create(empresa=context.empresa,factura=factura,numero=numero,monto=amount,impuesto=impuesto,tasa_cambio_snapshot=factura.tasa_cambio,motivo=motivo,estado="BORRADOR",creado_por=context.usuario,**extra);HistorialNotaProveedor.objects.create(**({"nota_credito":nota} if tipo=="CREDITO" else {"nota_debito":nota}),estado_anterior="",estado_nuevo="BORRADOR",usuario=context.usuario);return nota

@transaction.atomic
def enviar_nota_aprobacion(*,context,tipo,nota_id):
    cls=NotaCreditoProveedor if tipo=="CREDITO" else NotaDebitoProveedor;nota=cls.objects.select_for_update().get(pk=nota_id,empresa=context.empresa,estado="BORRADOR");nota.estado="PENDIENTE_APROBACION";nota.save(update_fields=["estado"]);HistorialNotaProveedor.objects.create(**({"nota_credito":nota} if tipo=="CREDITO" else {"nota_debito":nota}),estado_anterior="BORRADOR",estado_nuevo="PENDIENTE_APROBACION",usuario=context.usuario);return nota

@transaction.atomic
def decidir_nota(*,context,tipo,nota_id,decision,motivo=""):
    cls=NotaCreditoProveedor if tipo=="CREDITO" else NotaDebitoProveedor;nota=cls.objects.select_for_update().get(pk=nota_id,empresa=context.empresa,estado="PENDIENTE_APROBACION");nuevo="APROBADA" if decision=="APROBAR" else "RECHAZADA" if decision=="RECHAZAR" and motivo else None
    if not nuevo:raise ValidationError("Decisión o motivo inválido.")
    nota.estado=nuevo;nota.save(update_fields=["estado"]);HistorialNotaProveedor.objects.create(**({"nota_credito":nota} if tipo=="CREDITO" else {"nota_debito":nota}),estado_anterior="PENDIENTE_APROBACION",estado_nuevo=nuevo,usuario=context.usuario,comentario=motivo);return nota

@transaction.atomic
def aplicar_nota(*,context,tipo,nota_id,cuenta_id,monto,clave_idempotencia,tasa_cambio=None):
    from contabilidad.api import contabilizar_aplicacion_nota_credito,contabilizar_aplicacion_nota_debito
    cls=NotaCreditoProveedor if tipo=="CREDITO" else NotaDebitoProveedor;nota=cls.objects.select_for_update().get(pk=nota_id,empresa=context.empresa,estado__in=["APROBADA","APLICADA"]);cuenta=CuentaPorPagarEnterprise.objects.select_for_update().get(pk=cuenta_id,empresa=context.empresa,proveedor=nota.factura.proveedor);existente=AplicacionNotaProveedor.objects.filter(cuenta=cuenta,clave_idempotencia=clave_idempotencia).first()
    if existente:return existente
    amount=Decimal(str(monto));usado=nota.aplicaciones.filter(revertida=False).aggregate(v=Sum("monto"))["v"] or Decimal(0);disponible=nota.monto-usado
    if amount<=0 or amount>disponible or (tipo=="CREDITO" and amount>cuenta.saldo):raise ValidationError("Aplicación de nota inválida.")
    tasa=Decimal(str(tasa_cambio or nota.tasa_cambio_snapshot));app=AplicacionNotaProveedor.objects.create(**({"nota_credito":nota} if tipo=="CREDITO" else {"nota_debito":nota}),cuenta=cuenta,monto=amount,tasa_cambio=tasa,diferencia_cambiaria=(amount*tasa-amount).quantize(Decimal("0.01")),clave_idempotencia=clave_idempotencia);anterior=cuenta.saldo
    if tipo=="CREDITO":cuenta.saldo-=amount;mov=-amount;fn=contabilizar_aplicacion_nota_credito
    else:cuenta.saldo+=amount;cuenta.monto_original+=amount;mov=amount;fn=contabilizar_aplicacion_nota_debito
    cuenta.estado="PAGADA" if cuenta.saldo==0 else "PARCIAL" if tipo=="CREDITO" else "PENDIENTE";cuenta.save(update_fields=["saldo","estado"]+(["monto_original"] if tipo=="DEBITO" else []));MovimientoCxP.objects.create(cuenta=cuenta,tipo=f"NOTA_{tipo}",monto=mov,saldo_anterior=anterior,saldo_posterior=cuenta.saldo);dto=fn(context=context,aplicacion=app);app.asiento_id=dto.asiento_id;app.save(update_fields=["asiento_id"]);nota.estado="APLICADA" if amount==disponible else "APROBADA";nota.asiento_id=dto.asiento_id
    if tipo=="CREDITO":nota.saldo_disponible=disponible-amount;nota.save(update_fields=["estado","asiento_id","saldo_disponible"])
    else:nota.save(update_fields=["estado","asiento_id"])
    return app

@transaction.atomic
def anular_nota(*,context,tipo,nota_id,motivo):
    cls=NotaCreditoProveedor if tipo=="CREDITO" else NotaDebitoProveedor;nota=cls.objects.select_for_update().get(pk=nota_id,empresa=context.empresa,estado__in=["BORRADOR","PENDIENTE_APROBACION","RECHAZADA","APROBADA"])
    if nota.aplicaciones.filter(revertida=False).exists() or not motivo:raise ValidationError("La nota aplicada no puede anularse.")
    anterior=nota.estado;nota.estado="ANULADA";nota.save(update_fields=["estado"]);HistorialNotaProveedor.objects.create(**({"nota_credito":nota} if tipo=="CREDITO" else {"nota_debito":nota}),estado_anterior=anterior,estado_nuevo="ANULADA",usuario=context.usuario,comentario=motivo);return nota

@transaction.atomic
def revertir_aplicacion_nota(*,context,aplicacion_id,motivo):
    from contabilidad.api import revertir_documento
    app=AplicacionNotaProveedor.objects.select_for_update().select_related("nota_credito","nota_debito","cuenta").get(pk=aplicacion_id,cuenta__empresa=context.empresa,revertida=False)
    if not motivo:raise ValidationError("El motivo de reversión es obligatorio.")
    tipo="CREDITO" if app.nota_credito_id else "DEBITO";nota=app.nota_credito or app.nota_debito;cuenta=CuentaPorPagarEnterprise.objects.select_for_update().get(pk=app.cuenta_id);anterior=cuenta.saldo
    if tipo=="CREDITO":cuenta.saldo+=app.monto;nota.saldo_disponible+=app.monto;nota.save(update_fields=["saldo_disponible"])
    else:
        if cuenta.saldo<app.monto or cuenta.monto_original<app.monto:raise ValidationError("La cuenta no admite la reversión de la nota débito.")
        cuenta.saldo-=app.monto;cuenta.monto_original-=app.monto
    cuenta.estado="PAGADA" if cuenta.saldo==0 else "PENDIENTE" if cuenta.saldo==cuenta.monto_original else "PARCIAL";cuenta.save(update_fields=["saldo","monto_original","estado"]);MovimientoCxP.objects.create(cuenta=cuenta,tipo=f"REVERSO_NOTA_{tipo}",monto=(-app.monto if tipo=="DEBITO" else app.monto),saldo_anterior=anterior,saldo_posterior=cuenta.saldo)
    revertir_documento(context=context,origen_tipo=f"APLICACION_NOTA_{tipo}",origen_id=app.pk,motivo=motivo);app.revertida=True;app.save(update_fields=["revertida"]);estado_anterior=nota.estado;nota.estado="REVERTIDA";nota.save(update_fields=["estado"]);HistorialNotaProveedor.objects.create(**({"nota_credito":nota} if tipo=="CREDITO" else {"nota_debito":nota}),estado_anterior=estado_anterior,estado_nuevo="REVERTIDA",usuario=context.usuario,comentario=motivo);_event(context,NotaCreditoProveedorIntegrada if tipo=="CREDITO" else NotaDebitoProveedorIntegrada,nota,f"p2p-nota-revertida:{tipo}:{app.pk}",{"accion":"REVERSADA","aplicacion_id":app.pk});return app

def _nota_compat(*,context,tipo,factura_id,numero,monto,motivo,impuesto=0,retencion=0,concepto="RECARGO"):
    nota=crear_nota_borrador(context=context,tipo=tipo,factura_id=factura_id,numero=numero,monto=monto,motivo=motivo,impuesto=impuesto,retencion=retencion,concepto=concepto);enviar_nota_aprobacion(context=context,tipo=tipo,nota_id=nota.pk);decidir_nota(context=context,tipo=tipo,nota_id=nota.pk,decision="APROBAR");cuenta=CuentaPorPagarEnterprise.objects.get(empresa=context.empresa,factura_id=factura_id);aplicar_nota(context=context,tipo=tipo,nota_id=nota.pk,cuenta_id=cuenta.pk,monto=monto,clave_idempotencia=f"compat:{tipo}:{nota.pk}");nota.refresh_from_db();return nota

def crear_nota_credito(*,context,factura_id,numero,monto,motivo,impuesto=0,retencion=0):return _nota_compat(context=context,tipo="CREDITO",factura_id=factura_id,numero=numero,monto=monto,motivo=motivo,impuesto=impuesto,retencion=retencion)
def crear_nota_debito(*,context,factura_id,numero,monto,motivo,impuesto=0,concepto="RECARGO"):return _nota_compat(context=context,tipo="DEBITO",factura_id=factura_id,numero=numero,monto=monto,motivo=motivo,impuesto=impuesto,concepto=concepto)
