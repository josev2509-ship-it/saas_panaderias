from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from compras.models import WizardAuditTrail, WizardSession, WizardStepState

PASOS={
 "COMPRA":["Solicitud aprobada","Expediente","RFQ","Proveedores","Invitaciones","Ofertas","Comparativo","Escenario","Adjudicacion","Orden","Resumen"],
 "RECEPCION":["Orden","Lineas","Cantidades","Lotes, series y vencimientos","Diferencias","Inspeccion","Evidencias","InventoryEngine","Acta","Resumen"],
 "FACTURA_PAGO":["Proveedor","Orden y recepcion","Factura","Validacion","CxP","Notas y anticipos","Retenciones","Solicitud de pago","Aprobacion","Pago","Extracto","Previsualizacion","Importacion","Matching por referencia","Matching por monto y fecha","Conciliacion","Asientos","Resumen"],
}
PROHIBIDAS={"password","secret","token","numero_cuenta","cuenta_bancaria_completa","documento","archivo","evidencia"}

def _sanear(datos):
    if not isinstance(datos,dict):raise ValidationError("El payload del paso debe ser un objeto.")
    if any(str(k).lower() in PROHIBIDAS for k in datos):raise ValidationError("El wizard no almacena secretos, documentos ni datos bancarios completos.")
    return {str(k):v for k,v in datos.items() if v not in (None,"")}
def _json_safe(value):
    if isinstance(value,dict):return {str(k):_json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [_json_safe(v) for v in value]
    if hasattr(value,"pk"):return value.pk
    if hasattr(value,"isoformat"):return value.isoformat()
    from decimal import Decimal
    return str(value) if isinstance(value,Decimal) else value
def _persistible(datos):return {k:_json_safe(v) for k,v in _sanear(datos).items() if str(k).lower() not in {"contenido","csv","xlsx","archivo"}}

def _propia(sesion,context):
    if sesion.empresa_id!=context.empresa.pk or sesion.usuario_id!=context.usuario.pk:raise PermissionDenied
    if sesion.estado=="ACTIVO" and sesion.expirada:
        sesion.estado="EXPIRADO";sesion.save(update_fields=["estado","actualizado_en"]);WizardAuditTrail.objects.create(sesion=sesion,usuario=context.usuario,accion="EXPIRAR")
    return sesion

@transaction.atomic
def iniciar(*,context,tipo,clave_idempotencia,ttl_horas=24):
    if tipo not in PASOS:raise ValidationError("Tipo de wizard invalido.")
    sesion,creada=WizardSession.objects.get_or_create(empresa=context.empresa,usuario=context.usuario,tipo=tipo,clave_idempotencia=clave_idempotencia,defaults={"total_pasos":len(PASOS[tipo]),"expira_en":timezone.now()+timedelta(hours=ttl_horas)})
    if creada:
        WizardStepState.objects.bulk_create([WizardStepState(sesion=sesion,numero=i,nombre=n) for i,n in enumerate(PASOS[tipo],1)])
        WizardAuditTrail.objects.create(sesion=sesion,usuario=context.usuario,accion="INICIAR",paso=1)
    elif sesion.estado=="ACTIVO" and sesion.total_pasos!=len(PASOS[tipo]):
        existentes=set(sesion.pasos.values_list("numero",flat=True));WizardStepState.objects.bulk_create([WizardStepState(sesion=sesion,numero=i,nombre=n) for i,n in enumerate(PASOS[tipo],1) if i not in existentes]);sesion.total_pasos=len(PASOS[tipo]);sesion.save(update_fields=["total_pasos","actualizado_en"])
    return sesion

def reanudar(*,context,sesion_id):return _propia(WizardSession.objects.prefetch_related("pasos").get(pk=sesion_id),context)

@transaction.atomic
def guardar_paso(*,context,sesion_id,numero,datos,avanzar=True):
    sesion=_propia(WizardSession.objects.select_for_update().get(pk=sesion_id),context)
    if sesion.estado!="ACTIVO":raise ValidationError("El wizard no esta activo.")
    if numero!=sesion.paso_actual:raise ValidationError("No se puede manipular ni saltar el paso activo.")
    seguros=_sanear(datos)
    if numero<sesion.total_pasos and not seguros:raise ValidationError("Complete los datos obligatorios del paso.")
    paso=WizardStepState.objects.select_for_update().get(sesion=sesion,numero=numero);paso.datos=seguros;paso.estado="VALIDADO";paso.validado_en=timezone.now();paso.save(update_fields=["datos","estado","validado_en","actualizado_en"])
    sesion.datos={**sesion.datos,str(numero):seguros}
    if avanzar:
        if numero==sesion.total_pasos:sesion.estado="COMPLETADO"
        else:sesion.paso_actual+=1
    sesion.save(update_fields=["datos","paso_actual","estado","actualizado_en"])
    WizardAuditTrail.objects.create(sesion=sesion,usuario=context.usuario,accion="COMPLETAR" if sesion.estado=="COMPLETADO" else "AVANZAR",paso=numero,metadata_segura={"campos":sorted(seguros)})
    return sesion

@transaction.atomic
def retroceder(*,context,sesion_id):
    sesion=_propia(WizardSession.objects.select_for_update().get(pk=sesion_id),context)
    if sesion.estado!="ACTIVO" or sesion.paso_actual<=1:raise ValidationError("No es posible retroceder.")
    sesion.paso_actual-=1;sesion.save(update_fields=["paso_actual","actualizado_en"]);WizardAuditTrail.objects.create(sesion=sesion,usuario=context.usuario,accion="RETROCEDER",paso=sesion.paso_actual);return sesion

@transaction.atomic
def cancelar(*,context,sesion_id):
    sesion=_propia(WizardSession.objects.select_for_update().get(pk=sesion_id),context)
    if sesion.estado!="ACTIVO":raise ValidationError("Solo un wizard activo puede cancelarse.")
    sesion.estado="CANCELADO";sesion.save(update_fields=["estado","actualizado_en"]);WizardAuditTrail.objects.create(sesion=sesion,usuario=context.usuario,accion="CANCELAR",paso=sesion.paso_actual);return sesion

def _refs(sesion):return dict(sesion.datos.get("agregados",{}))
def _guardar_refs(sesion,refs):sesion.datos={**sesion.datos,"agregados":refs};sesion.save(update_fields=["datos","actualizado_en"])

@transaction.atomic
def orquestar_paso(*,context,sesion_id,numero,datos):
    """Ejecuta el agregado productivo del paso una sola vez y persiste sus referencias."""
    sesion=_propia(WizardSession.objects.select_for_update().get(pk=sesion_id),context)
    refs=_refs(sesion);key=str(numero)
    if key in refs:return sesion
    if numero!=sesion.paso_actual:raise ValidationError("El paso solicitado no es el activo.")
    operativos=_sanear(datos);seguros=_persistible(datos);resultado={}
    if sesion.tipo=="COMPRA":resultado=_orquestar_compra(context,numero,operativos,refs)
    elif sesion.tipo=="RECEPCION":resultado=_orquestar_recepcion(context,numero,operativos,refs,sesion)
    else:resultado=_orquestar_factura_pago(context,numero,operativos,refs,sesion)
    refs[key]=resultado or {"validado":True};_guardar_refs(sesion,refs);seguros={**seguros,"resultado":resultado or {"validado":True}}
    return guardar_paso(context=context,sesion_id=sesion.pk,numero=numero,datos=seguros)

def _orquestar_compra(context,n,data,refs):
    from compras.models import SolicitudCompra
    if n==1:
        obj=SolicitudCompra.objects.get(pk=data["solicitud_id"],empresa=context.empresa,estado="APROBADA");return {"solicitud_id":obj.pk}
    if n==2:
        from compras.application.expedientes_rfq import abrir_expediente,crear_expediente_desde_solicitud
        obj=crear_expediente_desde_solicitud(context=context,solicitud_id=refs["1"]["solicitud_id"]);abrir_expediente(context=context,expediente_id=obj.pk);return {"expediente_id":obj.pk}
    if n==3:
        from compras.application.expedientes_rfq import crear_rfq
        from catalogos.models import Almacen
        if isinstance(data.get("almacen_destino"),int):data={**data,"almacen_destino":Almacen.objects.get(pk=data["almacen_destino"],empresa=context.empresa)}
        obj=crear_rfq(context=context,expediente_id=refs["2"]["expediente_id"],datos=data);return {"rfq_id":obj.pk}
    if n==4:return {"proveedor_ids":data["proveedor_ids"]}
    if n==5:
        from compras.application.expedientes_rfq import agregar_proveedor_a_rfq
        ids=[]
        for item in data["invitaciones"]:ids.append(agregar_proveedor_a_rfq(context=context,rfq_id=refs["3"]["rfq_id"],proveedor_id=item["proveedor_id"],contacto_id=item.get("contacto_id")).pk)
        return {"invitacion_ids":ids}
    if n==6:
        from compras.application.p2p import crear_oferta,guardar_linea_oferta,transicionar_oferta
        ids=[]
        for item in data["ofertas"]:
            oferta=crear_oferta(context=context,rfq_id=refs["3"]["rfq_id"],proveedor_id=item["proveedor_id"],datos=item)
            for linea in item.get("lineas",[]):guardar_linea_oferta(context=context,oferta_id=oferta.pk,linea_rfq_id=linea["linea_rfq_id"],datos=linea)
            if item.get("enviar",True):transicionar_oferta(context=context,oferta_id=oferta.pk,nuevo="ENVIADA")
            ids.append(oferta.pk)
        return {"oferta_ids":ids}
    if n==7:
        from compras.application.p2p import crear_comparativo
        obj=crear_comparativo(context=context,rfq_id=refs["3"]["rfq_id"],ponderaciones=data.get("ponderaciones"));return {"comparativo_id":obj.pk}
    if n==8:
        from compras.application.p2p import guardar_escenario
        obj=guardar_escenario(context=context,comparativo_id=refs["7"]["comparativo_id"],nombre=data["nombre"],ponderaciones=data["ponderaciones"]);return {"escenario_id":obj.pk}
    if n==9:
        from compras.application.p2p import crear_adjudicacion,aprobar_adjudicacion
        obj=crear_adjudicacion(context=context,comparativo_id=refs["7"]["comparativo_id"],tipo=data["tipo"],selecciones=data["selecciones"],justificacion=data["justificacion"])
        if data.get("aprobar",True):aprobar_adjudicacion(context=context,adjudicacion_id=obj.pk)
        return {"adjudicacion_id":obj.pk}
    if n==10:
        from compras.application.p2p import crear_orden_desde_adjudicacion
        obj=crear_orden_desde_adjudicacion(context=context,adjudicacion_id=refs["9"]["adjudicacion_id"],proveedor_id=data.get("proveedor_id"));return {"orden_id":obj.pk}
    return {"resumen_pasos":sorted(refs)}

def _orquestar_recepcion(context,n,data,refs,sesion):
    from compras.models import OrdenCompraEnterprise
    if n==1:return {"orden_id":OrdenCompraEnterprise.objects.get(pk=data["orden_id"],empresa=context.empresa).pk}
    if n==8:
        from compras.application.p2p import crear_recepcion,agregar_detalle_recepcion,cerrar_recepcion
        from catalogos.models import Almacen
        acumulado={str(x.numero):x.datos for x in sesion.pasos.filter(numero__lt=8)};cabecera=acumulado.get("2",{});cabecera={**cabecera,"almacen":Almacen.objects.get(pk=cabecera["almacen"],empresa=context.empresa)};obj=crear_recepcion(context=context,orden_id=refs["1"]["orden_id"],datos={**cabecera,**data})
        for item in acumulado.get("3",{}).get("lineas",[]):agregar_detalle_recepcion(context=context,recepcion_id=obj.pk,detalle_orden_id=item["detalle_orden_id"],cantidad=item["cantidad"],aceptada=item.get("aceptada"),rechazada=item.get("rechazada",0),lote=item.get("lote",""),vence_el=item.get("vence_el"),motivo=item.get("motivo",""))
        cerrar_recepcion(context=context,recepcion_id=obj.pk);return {"recepcion_id":obj.pk,"inventory_engine":True}
    if n==9:return {"acta_recepcion_id":refs["8"]["recepcion_id"]}
    return {"validado":True}

def _orquestar_factura_pago(context,n,data,refs,sesion):
    if n==1:return {"proveedor_id":data["proveedor_id"]}
    if n==2:return {"orden_id":data["orden_id"],"recepcion_id":data["recepcion_id"]}
    if n==3:
        from compras.application.financial import crear_factura_proveedor
        obj=crear_factura_proveedor(context=context,orden_id=refs["2"]["orden_id"],recepcion_id=refs["2"]["recepcion_id"],datos=data,lineas=data["lineas"]);return {"factura_id":obj.pk}
    if n==4:
        from compras.application.financial import validar_e_integrar_factura
        obj=validar_e_integrar_factura(context=context,factura_id=refs["3"]["factura_id"]);return {"cxp_id":obj.pk}
    if n==5:return {"cxp_id":refs["4"]["cxp_id"]}
    if n==7:
        from compras.application.settlements import aplicar_retencion,emitir_certificado
        ids=[]
        for item in data.get("retenciones",[]):
            ret=aplicar_retencion(context=context,cuenta_id=refs["4"]["cxp_id"],tipo=item["tipo"],codigo=item["codigo"],base=item["base"],tasa=item["tasa"],clave_idempotencia=item["clave"]);cert=emitir_certificado(context=context,retencion_id=ret.pk);ids.append({"retencion_id":ret.pk,"certificado_id":cert.pk})
        return {"retenciones":ids}
    if n==8:
        from compras.application.financial import crear_solicitud_pago
        obj=crear_solicitud_pago(context=context,cuenta_id=refs["4"]["cxp_id"],monto=data["monto"]);return {"solicitud_pago_id":obj.pk}
    if n==9:
        from compras.application.financial import aprobar_solicitud_y_orden
        obj=aprobar_solicitud_y_orden(context=context,solicitud_id=refs["8"]["solicitud_pago_id"]);return {"orden_pago_id":obj.pk}
    if n==10:
        from compras.application.financial import pagar_orden
        from tesoreria.models import CuentaBancariaEmpresa,Caja
        banco=CuentaBancariaEmpresa.objects.get(pk=data["cuenta_bancaria_id"],empresa=context.empresa) if data.get("cuenta_bancaria_id") else None;caja=Caja.objects.get(pk=data["caja_id"],empresa=context.empresa) if data.get("caja_id") else None
        pagos=data.get("pagos") or [data];ids=[]
        for pago in pagos:
            obj=pagar_orden(context=context,orden_id=refs["9"]["orden_pago_id"],cuenta_bancaria=banco,caja=caja,monto=pago["monto"],referencia=pago["referencia"],metodo=pago.get("metodo","TRANSFERENCIA"),retencion=pago.get("retencion",0));ids.append(obj.pk)
        return {"movimiento_id":ids[-1],"movimiento_ids":ids,"cuenta_bancaria_id":getattr(banco,"pk",None)}
    if n==11:return {"nombre_archivo":data["nombre_archivo"],"cuenta_bancaria_id":data.get("cuenta_bancaria_id") or refs["10"]["cuenta_bancaria_id"]}
    if n==12:
        from tesoreria.models import CuentaBancariaEmpresa
        from tesoreria.services import importar_extracto
        cuenta=CuentaBancariaEmpresa.objects.get(pk=refs["11"]["cuenta_bancaria_id"],empresa=context.empresa);filas=importar_extracto(context=context,cuenta=cuenta,contenido=data["contenido"],nombre_archivo=refs["11"]["nombre_archivo"],confirmar=False);return {"filas":len(filas)}
    if n==13:
        from tesoreria.models import CuentaBancariaEmpresa
        from tesoreria.services import importar_extracto
        cuenta=CuentaBancariaEmpresa.objects.get(pk=refs["11"]["cuenta_bancaria_id"],empresa=context.empresa);obj=importar_extracto(context=context,cuenta=cuenta,contenido=data["contenido"],nombre_archivo=refs["11"]["nombre_archivo"],confirmar=True);return {"importacion_id":obj.pk}
    if n in {14,15}:
        from tesoreria.models import ImportacionExtractoBancario
        from tesoreria.services import sugerir_coincidencias
        imp=ImportacionExtractoBancario.objects.get(pk=refs["13"]["importacion_id"],empresa=context.empresa);matches=sugerir_coincidencias(context=context,importacion=imp,tolerancia_dias=data.get("tolerancia_dias",3));tipo="REFERENCIA" if n==14 else "MONTO_FECHA";elegidos=[x for x in matches if x["tipo"]==tipo];return {"sugerencias":elegidos}
    if n==16:
        from tesoreria.models import ConciliacionBancaria
        from tesoreria.services import conciliar_linea
        sugerencias=refs["14"].get("sugerencias",[])+refs["15"].get("sugerencias",[]);match=next((x for x in sugerencias if x["linea_id"]==data["linea_id"]),None)
        if not match:raise ValidationError("La coincidencia no pertenece a este wizard.")
        conc=ConciliacionBancaria.objects.create(empresa=context.empresa,cuenta_id=refs["11"]["cuenta_bancaria_id"],desde=data["desde"],hasta=data["hasta"],saldo_banco=data["saldo_banco"],saldo_libros=data["saldo_libros"],estado="BORRADOR");conciliar_linea(context=context,conciliacion=conc,linea_id=match["linea_id"],movimiento_id=match["movimiento_id"],tipo=match["tipo"]);return {"conciliacion_id":conc.pk}
    if n==17:return {"factura_id":refs["3"]["factura_id"],"movimiento_id":refs["10"]["movimiento_id"],"conciliacion_id":refs["16"]["conciliacion_id"]}
    if n==18:return {"resumen_pasos":sorted(refs)}
    return {"validado":True}
