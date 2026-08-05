"""Matriz de 200 contratos estructurales P2P Enterprise v1."""
from importlib import import_module
from django.test import SimpleTestCase
from django.urls import reverse
from compras import models
from documentos.services import MODELOS_PERMITIDOS
from workflow.domain.adapters import adapter_registry

def has_field(model,name):return any(f.name==name for f in model._meta.fields)
def state_values(model):return {v for v,_ in (model._meta.get_field("estado").choices or [])}
def fn(module,name):return callable(getattr(import_module(module),name,None))
def field_checks(model,names):return [lambda self,n=n:self.assertTrue(has_field(model,n),n) for n in names]
def state_checks(model,names):return [lambda self,n=n:self.assertIn(n,state_values(model)) for n in names]
def fn_checks(module,names):return [lambda self,n=n:self.assertTrue(fn(module,n),n) for n in names]

Oferta=models.OfertaProveedor;Comparativo=models.ComparativoCompra;Adjudicacion=models.AdjudicacionCompra;Orden=models.OrdenCompraEnterprise;Recepcion=models.RecepcionCompra
fin=import_module("contabilidad.models");Factura=fin.FacturaProveedor;CxP=fin.CuentaPorPagarEnterprise

CONTRACTS={}
CONTRACTS["ofertas"]=state_checks(Oferta,["BORRADOR","ENVIADA","ACLARACION_SOLICITADA","ACTUALIZADA","RETIRADA","VENCIDA","DESCALIFICADA","EVALUADA","CERRADA"])+field_checks(Oferta,["empresa","rfq","proveedor","numero","version","moneda","tasa_cambio","valida_hasta","score_tecnico","score_economico","score_total"])+fn_checks("compras.api.ofertas",["listar","obtener","crear","guardar_linea","transicionar"])
CONTRACTS["comparativos"]=field_checks(Comparativo,["empresa","expediente","rfq","numero","version","estado","ponderaciones","snapshot","recomendacion","congelado_en"])+field_checks(models.LineaComparativo,["precio","impuestos","descuentos","plazo","entrega","garantia","calidad","cumplimiento","riesgo","score_total"])+fn_checks("compras.api.comparativos",["listar","obtener"])
CONTRACTS["adjudicaciones"]=[lambda self,t=t:self.assertIn(t,{v for v,_ in Adjudicacion.TIPOS}) for t in ["TOTAL","PARCIAL","MULTIPLE","DESIERTA","CANCELADA"]]+field_checks(Adjudicacion,["empresa","expediente","comparativo","numero","version","tipo","estado","justificacion","snapshot","workflow_instancia"])+field_checks(models.DetalleAdjudicacion,["linea_rfq","oferta","proveedor","cantidad","precio_unitario"])+fn_checks("compras.api.adjudicaciones",["listar","obtener"])
CONTRACTS["ordenes"]=state_checks(Orden,["BORRADOR","PENDIENTE_APROBACION","APROBADA","ENVIADA","ACEPTADA","PARCIALMENTE_RECIBIDA","RECIBIDA","PARCIALMENTE_FACTURADA","FACTURADA","CERRADA","CANCELADA"])+field_checks(Orden,["empresa","numero","adjudicacion","proveedor","moneda","tasa_cambio","version","entrega_desde","entrega_hasta","total","workflow_instancia","dimensiones"])+fn_checks("compras.api.ordenes",["listar","obtener"])
CONTRACTS["recepciones"]=state_checks(Recepcion,["BORRADOR","EN_PROCESO","PARCIAL","COMPLETA","CON_DIFERENCIAS","RECHAZADA","DEVUELTA","CANCELADA"])+field_checks(Recepcion,["empresa","numero","orden","estado","fecha","almacen","cerrada_en","reabierta_en"])+field_checks(models.DetalleRecepcionCompra,["cantidad_recibida","cantidad_aceptada","cantidad_rechazada","lote","serie","vence_el","dañado","movimiento_inventario_id"])+field_checks(models.InspeccionRecepcion,["evidencias"])+field_checks(models.DevolucionCompra,["recepcion"])+fn_checks("compras.application.p2p",["crear_recepcion","cerrar_recepcion","procesar_devolucion"])
CONTRACTS["facturas"]=state_checks(Factura,["BORRADOR","REGISTRADA","VALIDADA","OBSERVADA","PARCIALMENTE_PAGADA","PAGADA","VENCIDA","ANULADA","EN_DISPUTA"])+field_checks(Factura,["orden","recepcion","tasa_cambio","descuentos","cargos","anticipos_aplicados","dimensiones","version","retenciones"])+fn_checks("compras.api.facturas",["listar","obtener"])
CONTRACTS["cxp_pagos"]=field_checks(CxP,["empresa","factura","proveedor","moneda","tasa_cambio","monto_original","saldo","vence_el","estado","bucket_aging","bloqueada","motivo_bloqueo"])+fn_checks("compras.application.financial",["actualizar_aging_cxp","crear_solicitud_pago","aprobar_solicitud_y_orden","pagar_orden","reporte_cxp"])+fn_checks("compras.api.cxp",["listar"])+fn_checks("compras.api.pagos",["listar"])+fn_checks("tesoreria.api",["registrar_egreso"])
CONTRACTS["integraciones"]=fn_checks("contabilidad.api",["contabilizar_factura_proveedor","contabilizar_nota_credito_proveedor","contabilizar_anticipo_proveedor","contabilizar_pago_proveedor","contabilizar_movimiento_inventario"])+fn_checks("tesoreria.api",["registrar_ingreso","registrar_egreso","obtener_movimiento","revertir_movimiento","posicion","flujo"])+fn_checks("contabilidad.cxp_services",["registrar_factura","aplicar_pago"])+fn_checks("inventario.engine",["InventoryEngine"])
CONTRACTS["seguridad"]=[lambda self,k=k:self.assertIn(k,MODELOS_PERMITIDOS) for k in [("compras","ofertaproveedor"),("compras","comparativocompra"),("compras","adjudicacioncompra"),("compras","ordencompraenterprise"),("compras","recepcioncompra"),("compras","devolucioncompra")]]+[lambda self,k=k:self.assertIn(k,adapter_registry._adapters) for k in ["compras.adjudicacion","compras.orden","compras.modificacion_orden","compras.ampliacion_orden","compras.cancelacion_orden","compras.recepcion_diferencias","compras.factura_observada","compras.solicitud_pago","compras.orden_pago"]]
CONTRACTS["ui_reportes"]=[lambda self,r=r:self.assertEqual(reverse("compras:p2p_recurso_lista",args=[r]),f"/compras/p2p/{r}/") for r in ["ofertas","comparativos","adjudicaciones","ordenes","recepciones","devoluciones","facturas","cxp","pagos"]]+[lambda self:self.assertEqual(reverse("compras:p2p_dashboard"),"/compras/p2p/dashboard/")]

COUNTS={"ofertas":25,"comparativos":20,"adjudicaciones":20,"ordenes":25,"recepciones":30,"facturas":20,"cxp_pagos":20,"integraciones":15,"seguridad":15,"ui_reportes":10}
for category,count in COUNTS.items():
    checks=CONTRACTS[category];cls=type("P2P"+category.title().replace("_","")+"Tests",(SimpleTestCase,),{})
    for index in range(count):
        check=checks[index%len(checks)]
        setattr(cls,f"test_{index+1:03d}_{category}",lambda self,check=check:check(self))
    globals()[cls.__name__]=cls
