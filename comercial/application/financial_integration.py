from dataclasses import asdict, dataclass, replace
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from contabilidad.api import contabilizar,contabilizar_cobro, contabilizar_factura_venta,contabilizar_nota_credito_venta,contabilizar_nota_debito_venta,revertir_documento
from contabilidad.models import ReglaContabilizacion
from core.application.event_bus import event_bus
from core.application.numbering import obtener_siguiente_numero
from tesoreria.api import registrar_ingreso,revertir_movimiento

from comercial.domain.o2c_full_events import *
from comercial.models import FacturaVenta, ReciboCobro,NotaDebitoVenta,DetalleNotaDebitoVenta,MovimientoCxC,HistorialFacturaVenta,CesionFactoring,HistorialFactoring,HistorialCobro
from comercial.application.o2c_full import emitir_nota_credito


@dataclass(frozen=True)
class FacturaContabilizadaDTO:
    factura_id:int;cxc_id:int;asiento_id:int;numero_asiento:str;total:str

@dataclass(frozen=True)
class CobroFinancieroDTO:
    recibo_id:int;movimiento_id:int;asiento_id:int;numero_asiento:str;monto:str

def _emit(context, clase, obj, suffix, payload):
    event_bus.publish(clase(empresa_id=context.empresa.pk,usuario_id=getattr(context.usuario,"pk",None),agregado_tipo=f"comercial.{obj._meta.model_name}",agregado_id=str(obj.pk),referencia=obj.numero,clave_idempotente=f"{suffix}:{obj.pk}",payload={"schema_version":1,"empresa_id":context.empresa.pk,**payload}))

@transaction.atomic
def contabilizar_factura_emitida(*,context,factura_id,simular=False):
    factura=FacturaVenta.objects.select_for_update().select_related("cuenta_cobrar").get(pk=factura_id,empresa=context.empresa)
    if factura.estado not in {"EMITIDA","PARCIALMENTE_COBRADA","COBRADA"}:raise ValidationError("Solo se contabilizan facturas emitidas.")
    resultado=contabilizar_factura_venta(context=replace(context,clave_idempotente=f"factura-venta:{factura.pk}"),factura=factura,simular=simular)
    if simular:return resultado
    dto=FacturaContabilizadaDTO(factura.pk,factura.cuenta_cobrar.pk,resultado.asiento_id,resultado.numero,str(factura.total))
    _emit(context,FacturaVentaContabilizada,factura,"factura-contabilizada",asdict(dto));return dto

@transaction.atomic
def integrar_cobro(*,context,recibo_id,cuenta_bancaria_id=None,caja_id=None):
    recibo=ReciboCobro.objects.select_for_update().get(pk=recibo_id,empresa=context.empresa,estado__in=["REGISTRADO","PARCIALMENTE_APLICADO","APLICADO"])
    if recibo.monto_aplicado<=0:raise ValidationError("El cobro debe tener aplicaciones antes de integrarse.")
    mov=registrar_ingreso(context=replace(context,clave_idempotente=f"cobro-tesoreria:{recibo.pk}"),origen_tipo="COBRO_O2C",origen_id=recibo.pk,fecha=recibo.fecha,monto=recibo.monto_aplicado,referencia=recibo.referencia or recibo.numero,cuenta_id=cuenta_bancaria_id,caja_id=caja_id)
    asiento=contabilizar_cobro(context=replace(context,clave_idempotente=f"cobro-contabilidad:{recibo.pk}"),cobro=recibo)
    diferencia=sum((a.diferencia_cambiaria for a in recibo.aplicaciones.filter(revertida=False)),Decimal("0"))
    if diferencia:
        regla=ReglaContabilizacion.objects.get(empresa=context.empresa,evento="DIFERENCIA_CAMBIARIA",activa=True)
        contra=regla.configuracion["contrapartida"];ganancia=regla.configuracion["ganancia"];perdida=regla.configuracion["perdida"]
        dimensiones=recibo.dimensiones or {}
        lineas=([{"cuenta":contra,"debito":abs(diferencia),"dimensiones":dimensiones},{"cuenta":ganancia,"credito":abs(diferencia),"dimensiones":dimensiones}] if diferencia>0 else [{"cuenta":perdida,"debito":abs(diferencia),"dimensiones":dimensiones},{"cuenta":contra,"credito":abs(diferencia),"dimensiones":dimensiones}])
        contabilizar(context=context,origen_tipo="DIFERENCIA_CAMBIARIA",origen_id=recibo.pk,concepto=f"Diferencia cambiaria {recibo.numero}",lineas=lineas)
    dto=CobroFinancieroDTO(recibo.pk,mov.id,asiento.asiento_id,asiento.numero,str(recibo.monto_aplicado))
    _emit(context,CobroContabilizado,recibo,"cobro-contabilizado",asdict(dto));return dto

@transaction.atomic
def emitir_nota_credito_integrada(*,context,factura_id,monto,motivo,ncf=""):
    from comercial.models import NotaCreditoVenta
    nota=NotaCreditoVenta.objects.filter(empresa=context.empresa,factura_id=factura_id,total=monto,motivo=motivo,estado="EMITIDA").first()
    if nota is None:nota=emitir_nota_credito(context=context,factura_id=factura_id,monto=monto,motivo=motivo,ncf=ncf)
    asiento=contabilizar_nota_credito_venta(context=replace(context,clave_idempotente=f"nota-credito:{nota.pk}"),nota=nota)
    _emit(context,NotaCreditoVentaContabilizada,nota,"nota-credito-contabilizada",{"asiento_id":asiento.asiento_id,"monto":str(nota.total)})
    return {"nota_id":nota.pk,"asiento_id":asiento.asiento_id,"saldo":str(nota.factura.cuenta_cobrar.saldo)}

@transaction.atomic
def emitir_nota_debito_integrada(*,context,factura_id,monto,motivo,ncf=""):
    factura=FacturaVenta.objects.select_for_update().get(pk=factura_id,empresa=context.empresa)
    if factura.estado in {"BORRADOR","ANULADA"}:raise ValidationError("La factura no admite nota de débito.")
    numero=obtener_siguiente_numero(empresa=context.empresa,tipo_documento="ND",usuario=context.usuario,context=replace(context,clave_idempotente=f"nota-debito-numero:{factura.pk}:{monto}"))
    nota,creada=NotaDebitoVenta.objects.get_or_create(empresa=context.empresa,numero=numero,defaults={"factura":factura,"moneda":factura.moneda,"tasa_cambio":factura.tasa_cambio,"dimensiones":factura.dimensiones,"motivo":motivo,"ncf":ncf,"estado":"EMITIDA","total":monto,"creado_por":context.usuario})
    cuenta=factura.cuenta_cobrar
    if creada:
        DetalleNotaDebitoVenta.objects.create(nota=nota,descripcion=motivo,cantidad=1,monto=monto);anterior=cuenta.saldo;cuenta.saldo+=nota.total;cuenta.monto_original+=nota.total;cuenta.estado="PENDIENTE" if anterior==0 else cuenta.estado;cuenta.save(update_fields=["saldo","monto_original","estado"]);MovimientoCxC.objects.create(cuenta=cuenta,tipo="NOTA_DEBITO",monto=nota.total,saldo_anterior=anterior,saldo_posterior=cuenta.saldo,referencia=nota.numero);_emit(context,NotaDebitoEmitida,nota,"nota-debito-emitida",{"monto":str(nota.total)})
    asiento=contabilizar_nota_debito_venta(context=replace(context,clave_idempotente=f"nota-debito:{nota.pk}"),nota=nota);_emit(context,NotaDebitoVentaContabilizada,nota,"nota-debito-contabilizada",{"asiento_id":asiento.asiento_id,"monto":str(nota.total)})
    return {"nota_id":nota.pk,"asiento_id":asiento.asiento_id,"saldo":str(cuenta.saldo)}

@transaction.atomic
def anular_factura_sin_cobros(*,context,factura_id,motivo):
    factura=FacturaVenta.objects.select_for_update().get(pk=factura_id,empresa=context.empresa)
    if not motivo:raise ValidationError("El motivo es obligatorio.")
    if factura.cuenta_cobrar.aplicaciones.filter(revertida=False).exists():raise ValidationError("Una factura con cobros no puede anularse directamente.")
    if factura.estado=="ANULADA":return {"factura_id":factura.pk,"estado":factura.estado}
    reversa=revertir_documento(context=context,origen_tipo="FACTURA_VENTA",origen_id=factura.pk,motivo=motivo);anterior=factura.estado;factura.estado="ANULADA";factura.save(update_fields=["estado"]);cuenta=factura.cuenta_cobrar;cuenta.saldo=0;cuenta.estado="CANCELADA";cuenta.save(update_fields=["saldo","estado"]);HistorialFacturaVenta.objects.create(factura=factura,estado_anterior=anterior,estado_nuevo="ANULADA",usuario=context.usuario);_emit(context,FacturaVentaAnulada,factura,"factura-anulada",{"reversion_id":reversa["asiento_reversion_id"],"motivo":motivo});return {"factura_id":factura.pk,"estado":"ANULADA",**reversa}

@transaction.atomic
def desembolsar_factoring(*,context,cesion_id,cuenta_bancaria_id,comision=0,costo_financiero=0,retencion=0,referencia=""):
    cesion=CesionFactoring.objects.select_for_update().select_related("cuenta__factura").get(pk=cesion_id,empresa=context.empresa)
    if cesion.estado not in {"APROBADA","CEDIDA"}:raise ValidationError("La cesión no está aprobada para desembolso.")
    if cesion.cuenta.factura.estado in {"ANULADA","COBRADA"} or cesion.monto_cedido>cesion.cuenta.saldo:raise ValidationError("La factura no tiene saldo elegible.")
    comision,costo_financiero,retencion=map(Decimal,map(str,(comision,costo_financiero,retencion)));neto=cesion.monto_cedido-comision-costo_financiero-retencion
    if neto<=0:raise ValidationError("El neto de factoring debe ser positivo.")
    regla=ReglaContabilizacion.objects.get(empresa=context.empresa,evento="FACTORING",activa=True)
    lineas=[{"cuenta":regla.configuracion["banco"],"debito":neto,"dimensiones":cesion.dimensiones},{"cuenta":regla.configuracion["gasto"],"debito":comision+costo_financiero,"dimensiones":cesion.dimensiones},{"cuenta":regla.configuracion["cxc"],"credito":cesion.monto_cedido,"dimensiones":cesion.dimensiones}]
    if retencion:lineas.insert(2,{"cuenta":regla.configuracion["retencion"],"debito":retencion,"dimensiones":cesion.dimensiones})
    mov=registrar_ingreso(context=context,origen_tipo="FACTORING_O2C",origen_id=cesion.pk,fecha=timezone.localdate(),monto=neto,referencia=referencia or cesion.numero,cuenta_id=cuenta_bancaria_id)
    asiento=contabilizar(context=context,origen_tipo="FACTORING",origen_id=cesion.pk,concepto=f"Desembolso factoring {cesion.numero}",lineas=lineas,moneda=cesion.moneda,tasa_cambio=cesion.tasa_cambio)
    cesion.comision=comision;cesion.costo_financiero=costo_financiero;cesion.retencion=retencion;cesion.neto_recibido=neto;cesion.estado="DESEMBOLSADA";cesion.desembolsado_en=timezone.now();cesion.referencia_desembolso=referencia;cesion.save();cesion.cuenta.estado="CEDIDA_FACTORING";cesion.cuenta.save(update_fields=["estado"]);cesion.cuenta.factura.estado="CEDIDA_FACTORING";cesion.cuenta.factura.save(update_fields=["estado"]);_emit(context,DesembolsoFactoringRegistrado,cesion,"factoring-desembolso",{"movimiento_id":mov.id,"neto":str(neto)});_emit(context,FactoringContabilizado,cesion,"factoring-contabilizado",{"asiento_id":asiento.pk});return {"cesion_id":cesion.pk,"movimiento_id":mov.id,"asiento_id":asiento.pk,"neto":str(neto)}

@transaction.atomic
def revertir_cobro_integral(*,context,recibo_id,motivo):
    if not context.usuario or not context.usuario.has_perm("comercial.revertir_cobro"):raise ValidationError("No tiene permiso para revertir cobros.")
    if not motivo:raise ValidationError("El motivo es obligatorio.")
    recibo=ReciboCobro.objects.select_for_update().get(pk=recibo_id,empresa=context.empresa)
    if recibo.estado=="REVERTIDO":return {"recibo_id":recibo.pk,"estado":"REVERTIDO"}
    _emit(context,CobroReversionSolicitada,recibo,"cobro-reversion-solicitada",{"motivo":motivo})
    reverso_tesoreria=revertir_movimiento(context=context,origen_tipo="COBRO_O2C",origen_id=recibo.pk,motivo=motivo);reversa=revertir_documento(context=context,origen_tipo="COBRO",origen_id=recibo.pk,motivo=motivo)
    from contabilidad.models import AsientoContable
    if AsientoContable.objects.filter(empresa=context.empresa,origen_tipo="DIFERENCIA_CAMBIARIA",origen_id=str(recibo.pk),estado="CONTABILIZADO").exists():revertir_documento(context=context,origen_tipo="DIFERENCIA_CAMBIARIA",origen_id=recibo.pk,motivo=motivo)
    for aplicacion in recibo.aplicaciones.select_for_update().filter(revertida=False):
        cuenta=aplicacion.cuenta;anterior=cuenta.saldo;cuenta.saldo+=aplicacion.monto;cuenta.estado="PENDIENTE" if cuenta.saldo==cuenta.monto_original else "PARCIAL";cuenta.save(update_fields=["saldo","estado"]);cuenta.factura.estado="EMITIDA" if cuenta.saldo==cuenta.monto_original else "PARCIALMENTE_COBRADA";cuenta.factura.save(update_fields=["estado"]);aplicacion.revertida=True;aplicacion.save(update_fields=["revertida"]);MovimientoCxC.objects.create(cuenta=cuenta,tipo="REVERSO",monto=aplicacion.monto,saldo_anterior=anterior,saldo_posterior=cuenta.saldo,referencia=recibo.numero);_emit(context,AplicacionCobroRevertida,recibo,f"aplicacion-revertida-{aplicacion.pk}",{"aplicacion_id":aplicacion.pk,"saldo":str(cuenta.saldo)})
    anterior=recibo.estado;recibo.estado="REVERTIDO";recibo.save(update_fields=["estado"]);HistorialCobro.objects.create(recibo=recibo,estado_anterior=anterior,estado_nuevo="REVERTIDO",usuario=context.usuario);_emit(context,CobroRevertido,recibo,"cobro-revertido",{"movimiento_reverso_id":reverso_tesoreria.id,"asiento_reversion_id":reversa["asiento_reversion_id"]});return {"recibo_id":recibo.pk,"estado":"REVERTIDO","movimiento_reverso_id":reverso_tesoreria.id,**reversa}
