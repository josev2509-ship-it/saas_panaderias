import hashlib
from dataclasses import replace
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from comercial.models import CuentaPorCobrar, MovimientoCxC
from contabilidad.models import (AplicacionRetencionProveedor, CertificadoRetencionProveedor,
 AnticipoProveedor,CompensacionP2P, CuentaPorPagarEnterprise, HistorialCompensacionP2P,
 MovimientoCxP, NotaCreditoProveedor,RetencionProveedor)
from core.application.event_bus import event_bus
from core.application.numbering import obtener_siguiente_numero
from compras.domain.p2p_events import (CertificadoRetencionEmitido,CompensacionP2PAplicada,
 CompensacionP2PReversada,RetencionProveedorAplicada,RetencionProveedorReversada)

def _emitir(context,cls,obj,accion):event_bus.publish(cls(empresa_id=context.empresa.pk,usuario_id=getattr(context.usuario,"pk",None),agregado_tipo=f"contabilidad.{obj._meta.model_name}",agregado_id=str(obj.pk),referencia=getattr(obj,"numero",str(obj.pk)),clave_idempotente=f"{accion}:{obj.pk}",payload={"schema_version":1,"empresa_id":context.empresa.pk,"monto":str(obj.monto),"estado":obj.estado}))
def _numero(context,tipo,clave):return obtener_siguiente_numero(empresa=context.empresa,tipo_documento=tipo,usuario=context.usuario,context=replace(context,clave_idempotente=clave))

@transaction.atomic
def proponer_compensacion(*,context,cuenta_pagar_id,monto,clave_idempotencia,cuenta_cobrar_id=None,anticipo_id=None,nota_credito_id=None,tasa_cambio=1):
    existente=CompensacionP2P.objects.filter(empresa=context.empresa,clave_idempotencia=clave_idempotencia).first()
    if existente:return existente
    fuentes=sum(bool(x) for x in (cuenta_cobrar_id,anticipo_id,nota_credito_id))
    if fuentes!=1:raise ValidationError("Seleccione exactamente una fuente de compensacion.")
    cxp=CuentaPorPagarEnterprise.objects.select_for_update().get(pk=cuenta_pagar_id,empresa=context.empresa)
    amount=Decimal(str(monto));tasa=Decimal(str(tasa_cambio));base=(amount*tasa).quantize(Decimal("0.01"))
    if amount<=0 or amount>cxp.saldo or tasa<=0:raise ValidationError("Monto o tasa de compensacion invalido.")
    cxc=anticipo=nota=None
    if cuenta_cobrar_id:
        cxc=CuentaPorCobrar.objects.select_for_update().get(pk=cuenta_cobrar_id,empresa=context.empresa)
        if amount>cxc.saldo:raise ValidationError("La compensacion excede la CxC.")
    elif anticipo_id:
        anticipo=AnticipoProveedor.objects.select_for_update().get(pk=anticipo_id,empresa=context.empresa,proveedor=cxp.proveedor,estado="DISPONIBLE")
        if amount>anticipo.saldo:raise ValidationError("La compensacion excede el anticipo disponible.")
    else:
        nota=NotaCreditoProveedor.objects.select_for_update().get(pk=nota_credito_id,empresa=context.empresa,factura__proveedor=cxp.proveedor,estado="REGISTRADA")
        if amount>nota.saldo_disponible:raise ValidationError("La compensacion excede el saldo de la nota.")
    comp=CompensacionP2P.objects.create(empresa=context.empresa,numero=_numero(context,"CP",f"comp:{clave_idempotencia}"),cuenta_pagar=cxp,cuenta_cobrar_id=cuenta_cobrar_id,anticipo_id=anticipo_id,nota_credito_id=nota_credito_id,moneda=cxp.moneda,tasa_cambio=tasa,monto=amount,monto_base=base,diferencia_cambiaria=base-amount,estado="PROPUESTA",clave_idempotencia=clave_idempotencia,creado_por=context.usuario)
    HistorialCompensacionP2P.objects.create(compensacion=comp,estado_anterior="BORRADOR",estado_nuevo="PROPUESTA",usuario=context.usuario);return comp

@transaction.atomic
def aprobar_compensacion(*,context,compensacion_id):
    comp=CompensacionP2P.objects.select_for_update().get(pk=compensacion_id,empresa=context.empresa)
    if comp.estado=="APROBADA":return comp
    if comp.estado!="PROPUESTA":raise ValidationError("Solo una propuesta puede aprobarse.")
    comp.estado="APROBADA";comp.save(update_fields=["estado"]);HistorialCompensacionP2P.objects.create(compensacion=comp,estado_anterior="PROPUESTA",estado_nuevo="APROBADA",usuario=context.usuario);return comp

@transaction.atomic
def aplicar_compensacion_aprobada(*,context,compensacion_id):
    from contabilidad.api import contabilizar_compensacion_p2p
    comp=CompensacionP2P.objects.select_for_update().select_related("cuenta_pagar").get(pk=compensacion_id,empresa=context.empresa)
    if comp.estado=="APLICADA":return comp
    if comp.estado!="APROBADA":raise ValidationError("La compensacion requiere aprobacion.")
    cxp=CuentaPorPagarEnterprise.objects.select_for_update().get(pk=comp.cuenta_pagar_id,empresa=context.empresa)
    if comp.monto>cxp.saldo:raise ValidationError("Saldo CxP insuficiente.")
    cxc=anticipo=nota=None
    if comp.cuenta_cobrar_id:
        cxc=CuentaPorCobrar.objects.select_for_update().get(pk=comp.cuenta_cobrar_id,empresa=context.empresa)
        if comp.monto>cxc.saldo:raise ValidationError("Saldo CxC insuficiente.")
    elif comp.anticipo_id:
        anticipo=AnticipoProveedor.objects.select_for_update().get(pk=comp.anticipo_id,empresa=context.empresa)
        if comp.monto>anticipo.saldo:raise ValidationError("Saldo de anticipo insuficiente.")
    else:
        nota=NotaCreditoProveedor.objects.select_for_update().get(pk=comp.nota_credito_id,empresa=context.empresa)
        if comp.monto>nota.saldo_disponible:raise ValidationError("Saldo de nota insuficiente.")
    anterior=cxp.saldo;cxp.saldo-=comp.monto;cxp.estado="PAGADA" if cxp.saldo==0 else "PARCIAL";cxp.save(update_fields=["saldo","estado"]);MovimientoCxP.objects.create(cuenta=cxp,tipo="COMPENSACION",monto=-comp.monto,saldo_anterior=anterior,saldo_posterior=cxp.saldo)
    if cxc:
        anterior_cxc=cxc.saldo;cxc.saldo-=comp.monto;cxc.estado="COBRADA" if cxc.saldo==0 else "PARCIAL";cxc.save(update_fields=["saldo","estado"]);MovimientoCxC.objects.create(cuenta=cxc,tipo="COBRO",monto=-comp.monto,saldo_anterior=anterior_cxc,saldo_posterior=cxc.saldo,referencia=comp.numero)
    elif anticipo:
        anticipo.saldo-=comp.monto;anticipo.estado="APLICADO" if anticipo.saldo==0 else "DISPONIBLE";anticipo.save(update_fields=["saldo","estado"])
    else:
        nota.saldo_disponible-=comp.monto;nota.estado="APLICADA" if nota.saldo_disponible==0 else "REGISTRADA";nota.save(update_fields=["saldo_disponible","estado"])
    dto=contabilizar_compensacion_p2p(context=context,compensacion=comp);comp.asiento_id=dto.asiento_id;comp.estado="APLICADA";comp.save(update_fields=["asiento_id","estado"]);HistorialCompensacionP2P.objects.create(compensacion=comp,estado_anterior="APROBADA",estado_nuevo="APLICADA",usuario=context.usuario);_emitir(context,CompensacionP2PAplicada,comp,"compensacion-aplicada");return comp

def aplicar_compensacion(*,context,**kwargs):
    comp=proponer_compensacion(context=context,**kwargs)
    if comp.estado=="APLICADA":return comp
    if comp.estado=="PROPUESTA":comp=aprobar_compensacion(context=context,compensacion_id=comp.pk)
    return aplicar_compensacion_aprobada(context=context,compensacion_id=comp.pk)

@transaction.atomic
def revertir_compensacion(*,context,compensacion_id,motivo):
    from contabilidad.api import revertir_compensacion_p2p
    comp=CompensacionP2P.objects.select_for_update().select_related("cuenta_pagar").get(pk=compensacion_id,empresa=context.empresa)
    if comp.estado=="REVERSADA":return comp
    if comp.estado!="APLICADA" or not motivo:raise ValidationError("Compensacion no reversible.")
    cxp=CuentaPorPagarEnterprise.objects.select_for_update().get(pk=comp.cuenta_pagar_id);anterior=cxp.saldo;cxp.saldo+=comp.monto;cxp.estado="PENDIENTE";cxp.save(update_fields=["saldo","estado"]);MovimientoCxP.objects.create(cuenta=cxp,tipo="REVERSO_COMPENSACION",monto=comp.monto,saldo_anterior=anterior,saldo_posterior=cxp.saldo)
    if comp.cuenta_cobrar_id:
        cxc=CuentaPorCobrar.objects.select_for_update().get(pk=comp.cuenta_cobrar_id,empresa=context.empresa);ant=cxc.saldo;cxc.saldo+=comp.monto;cxc.estado="PENDIENTE";cxc.save(update_fields=["saldo","estado"]);MovimientoCxC.objects.create(cuenta=cxc,tipo="REVERSO",monto=comp.monto,saldo_anterior=ant,saldo_posterior=cxc.saldo,referencia=comp.numero)
    elif comp.anticipo_id:
        fuente=AnticipoProveedor.objects.select_for_update().get(pk=comp.anticipo_id,empresa=context.empresa);fuente.saldo+=comp.monto;fuente.estado="DISPONIBLE";fuente.save(update_fields=["saldo","estado"])
    else:
        fuente=NotaCreditoProveedor.objects.select_for_update().get(pk=comp.nota_credito_id,empresa=context.empresa);fuente.saldo_disponible+=comp.monto;fuente.estado="REGISTRADA";fuente.save(update_fields=["saldo_disponible","estado"])
    revertir_compensacion_p2p(context=context,compensacion=comp,motivo=motivo);comp.estado="REVERSADA";comp.motivo_reversion=motivo;comp.save(update_fields=["estado","motivo_reversion"]);HistorialCompensacionP2P.objects.create(compensacion=comp,estado_anterior="APLICADA",estado_nuevo="REVERSADA",usuario=context.usuario,comentario=motivo);_emitir(context,CompensacionP2PReversada,comp,"compensacion-reversada");return comp

@transaction.atomic
def anular_compensacion(*,context,compensacion_id,motivo):
    comp=CompensacionP2P.objects.select_for_update().get(pk=compensacion_id,empresa=context.empresa)
    if comp.estado=="ANULADA":return comp
    if comp.estado not in {"PROPUESTA","APROBADA"} or not motivo:raise ValidationError("Solo propuestas no aplicadas pueden anularse.")
    anterior=comp.estado;comp.estado="ANULADA";comp.motivo_reversion=motivo;comp.save(update_fields=["estado","motivo_reversion"]);HistorialCompensacionP2P.objects.create(compensacion=comp,estado_anterior=anterior,estado_nuevo="ANULADA",usuario=context.usuario,comentario=motivo);return comp

@transaction.atomic
def aplicar_retencion(*,context,cuenta_id,tipo,codigo,base,tasa,clave_idempotencia,orden_pago_id=None,vigente_desde=None,vigente_hasta=None,configuracion_snapshot=None):
    from contabilidad.api import contabilizar_retencion_proveedor
    existente=RetencionProveedor.objects.filter(empresa=context.empresa,clave_idempotencia=clave_idempotencia).first()
    if existente:return existente
    cuenta=CuentaPorPagarEnterprise.objects.select_for_update().select_related("factura","proveedor").get(pk=cuenta_id,empresa=context.empresa)
    base=Decimal(str(base));tasa=Decimal(str(tasa));monto=(base*tasa).quantize(Decimal("0.01"))
    hoy=timezone.localdate();desde=vigente_desde or hoy
    if tipo not in {"ITBIS","ISR","OTRA"} or base<=0 or tasa<=0 or monto>cuenta.saldo or hoy<desde or (vigente_hasta and hoy>vigente_hasta):raise ValidationError("Retencion invalida o fuera de vigencia; tasas legales deben provenir de configuracion.")
    ret=RetencionProveedor.objects.create(empresa=context.empresa,numero=_numero(context,"RT",f"ret:{clave_idempotencia}"),proveedor=cuenta.proveedor,factura=cuenta.factura,orden_pago_id=orden_pago_id,tipo=tipo,codigo=codigo,base=base,tasa=tasa,monto=monto,saldo=monto,moneda=cuenta.moneda,tasa_cambio_snapshot=cuenta.tasa_cambio,configuracion_snapshot=configuracion_snapshot or {"codigo":codigo,"tipo":tipo,"base":str(base),"tasa":str(tasa)},vigente_desde=desde,vigente_hasta=vigente_hasta,estado="APLICADA",clave_idempotencia=clave_idempotencia,fecha=hoy,creado_por=context.usuario)
    anterior=cuenta.saldo;cuenta.saldo-=monto;cuenta.estado="PAGADA" if cuenta.saldo==0 else "PARCIAL";cuenta.save(update_fields=["saldo","estado"]);AplicacionRetencionProveedor.objects.create(retencion=ret,cuenta=cuenta,monto=monto,saldo_anterior=anterior,saldo_posterior=cuenta.saldo);MovimientoCxP.objects.create(cuenta=cuenta,tipo="RETENCION",monto=-monto,saldo_anterior=anterior,saldo_posterior=cuenta.saldo)
    dto=contabilizar_retencion_proveedor(context=context,retencion=ret);ret.asiento_id=dto.asiento_id;ret.save(update_fields=["asiento_id"]);_emitir(context,RetencionProveedorAplicada,ret,"retencion-aplicada");return ret

@transaction.atomic
def crear_retencion_borrador(*,context,cuenta_id,tipo,codigo,base,tasa,clave_idempotencia,orden_pago_id=None,vigente_desde=None,vigente_hasta=None):
    cuenta=CuentaPorPagarEnterprise.objects.select_related("factura","proveedor").get(pk=cuenta_id,empresa=context.empresa);base=Decimal(str(base));tasa=Decimal(str(tasa));monto=(base*tasa).quantize(Decimal("0.01"));hoy=timezone.localdate()
    if monto<=0 or monto>cuenta.saldo:raise ValidationError("Retención inválida.")
    return RetencionProveedor.objects.create(empresa=context.empresa,numero=_numero(context,"RT",f"ret-borrador:{clave_idempotencia}"),proveedor=cuenta.proveedor,factura=cuenta.factura,orden_pago_id=orden_pago_id,tipo=tipo,codigo=codigo,base=base,tasa=tasa,monto=monto,saldo=monto,moneda=cuenta.moneda,tasa_cambio_snapshot=cuenta.tasa_cambio,configuracion_snapshot={"codigo":codigo,"tipo":tipo,"base":str(base),"tasa":str(tasa)},vigente_desde=vigente_desde or hoy,vigente_hasta=vigente_hasta,estado="PENDIENTE_APROBACION",clave_idempotencia=clave_idempotencia,fecha=hoy,creado_por=context.usuario)

@transaction.atomic
def decidir_retencion(*,context,retencion_id,decision,motivo=""):
    ret=RetencionProveedor.objects.select_for_update().get(pk=retencion_id,empresa=context.empresa,estado="PENDIENTE_APROBACION")
    if decision=="APROBAR":ret.estado="APROBADA"
    elif decision=="RECHAZAR" and motivo:ret.estado="RECHAZADA";ret.motivo_reversion=motivo
    else:raise ValidationError("Decisión o motivo inválido.")
    ret.save(update_fields=["estado","motivo_reversion"]);return ret

@transaction.atomic
def aplicar_retencion_aprobada(*,context,retencion_id):
    from contabilidad.api import contabilizar_retencion_proveedor
    ret=RetencionProveedor.objects.select_for_update().select_related("factura").get(pk=retencion_id,empresa=context.empresa)
    if ret.estado=="APLICADA":return ret
    if ret.estado!="APROBADA":raise ValidationError("La retención requiere aprobación.")
    cuenta=CuentaPorPagarEnterprise.objects.select_for_update().get(empresa=context.empresa,factura=ret.factura)
    if ret.monto>cuenta.saldo:raise ValidationError("Saldo insuficiente para aplicar la retención.")
    anterior=cuenta.saldo;cuenta.saldo-=ret.monto;cuenta.estado="PAGADA" if cuenta.saldo==0 else "PARCIAL";cuenta.save(update_fields=["saldo","estado"]);AplicacionRetencionProveedor.objects.create(retencion=ret,cuenta=cuenta,monto=ret.monto,saldo_anterior=anterior,saldo_posterior=cuenta.saldo);MovimientoCxP.objects.create(cuenta=cuenta,tipo="RETENCION",monto=-ret.monto,saldo_anterior=anterior,saldo_posterior=cuenta.saldo);dto=contabilizar_retencion_proveedor(context=context,retencion=ret);ret.estado="APLICADA";ret.asiento_id=dto.asiento_id;ret.save(update_fields=["estado","asiento_id"]);_emitir(context,RetencionProveedorAplicada,ret,"retencion-aplicada");return ret

@transaction.atomic
def emitir_certificado(*,context,retencion_id):
    ret=RetencionProveedor.objects.get(pk=retencion_id,empresa=context.empresa,estado="APLICADA");numero=f"CRT-{ret.numero}";contenido=f"{context.empresa.pk}|{ret.pk}|{ret.proveedor_id}|{ret.tipo}|{ret.monto}|{ret.fecha}";cert,_=CertificadoRetencionProveedor.objects.get_or_create(empresa=context.empresa,retencion=ret,defaults={"numero":numero,"contenido_hash":hashlib.sha256(contenido.encode()).hexdigest(),"creado_por":context.usuario});_emitir(context,CertificadoRetencionEmitido,ret,"certificado-retencion");return cert

@transaction.atomic
def revertir_retencion(*,context,retencion_id,motivo):
    from contabilidad.api import revertir_retencion_proveedor
    ret=RetencionProveedor.objects.select_for_update().get(pk=retencion_id,empresa=context.empresa)
    if ret.estado=="REVERTIDA":return ret
    if ret.estado!="APLICADA" or not motivo:raise ValidationError("Retencion no reversible.")
    app=AplicacionRetencionProveedor.objects.select_for_update().select_related("cuenta").get(retencion=ret,revertida=False);cuenta=app.cuenta;anterior=cuenta.saldo;cuenta.saldo+=app.monto;cuenta.estado="PENDIENTE";cuenta.save(update_fields=["saldo","estado"]);MovimientoCxP.objects.create(cuenta=cuenta,tipo="REVERSO_RETENCION",monto=app.monto,saldo_anterior=anterior,saldo_posterior=cuenta.saldo);app.revertida=True;app.save(update_fields=["revertida"]);revertir_retencion_proveedor(context=context,retencion=ret,motivo=motivo);ret.estado="REVERTIDA";ret.motivo_reversion=motivo;ret.saldo=0;ret.save(update_fields=["estado","motivo_reversion","saldo"]);_emitir(context,RetencionProveedorReversada,ret,"retencion-reversada");return ret

@transaction.atomic
def anular_retencion(*,context,retencion_id,motivo):
    ret=RetencionProveedor.objects.select_for_update().get(pk=retencion_id,empresa=context.empresa)
    if ret.estado=="ANULADA":return ret
    if ret.estado=="APLICADA":revertir_retencion(context=context,retencion_id=ret.pk,motivo=motivo);ret.refresh_from_db()
    ret.estado="ANULADA";ret.motivo_reversion=motivo;ret.save(update_fields=["estado","motivo_reversion"]);return ret
