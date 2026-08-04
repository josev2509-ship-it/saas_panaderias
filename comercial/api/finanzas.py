from django.db.models import Sum
from comercial.models import FacturaVenta,CuentaPorCobrar,ReciboCobro,CesionFactoring
from contabilidad.reportes import diario,mayor,saldos,estado_resultados,balance_general
from tesoreria.api import posicion
from tesoreria.models import MovimientoTesoreria

def facturas(*,empresa,moneda=None,cliente=None,estado=None,limit=100):
 qs=FacturaVenta.objects.filter(empresa=empresa).select_related("cliente","moneda__moneda").prefetch_related("detalles","notacreditoventa_set","notadebitoventa_set")
 if moneda:qs=qs.filter(moneda_id=getattr(moneda,"pk",moneda))
 if cliente:qs=qs.filter(cliente_id=getattr(cliente,"pk",cliente))
 if estado:qs=qs.filter(estado=estado)
 return list(qs.order_by("-fecha","-pk")[:limit])
def cobros(*,empresa,moneda=None,cliente=None,limit=100):
 qs=ReciboCobro.objects.filter(empresa=empresa).select_related("cliente","moneda__moneda").prefetch_related("aplicaciones__cuenta__factura")
 if moneda:qs=qs.filter(moneda_id=getattr(moneda,"pk",moneda))
 if cliente:qs=qs.filter(cliente_id=getattr(cliente,"pk",cliente))
 return list(qs.order_by("-fecha","-pk")[:limit])
def cuentas_cobrar(*,empresa,moneda=None,cliente=None,estado=None,limit=100):
 qs=CuentaPorCobrar.objects.filter(empresa=empresa).select_related("cliente","factura","moneda__moneda").prefetch_related("movimientos","aplicaciones")
 if moneda:qs=qs.filter(moneda_id=getattr(moneda,"pk",moneda))
 if cliente:qs=qs.filter(cliente_id=getattr(cliente,"pk",cliente))
 if estado:qs=qs.filter(estado=estado)
 return list(qs.order_by("fecha_vencimiento","pk")[:limit])

def dashboard(*,empresa,moneda=None,centro=None,proyecto=None,sucursal=None):
 def total(qs,campo):return str(qs.aggregate(v=Sum(campo))["v"] or 0)
 facturas=FacturaVenta.objects.filter(empresa=empresa).exclude(estado="BORRADOR");cxc=CuentaPorCobrar.objects.filter(empresa=empresa);cobros=ReciboCobro.objects.filter(empresa=empresa)
 if moneda:
  moneda_id=getattr(moneda,"pk",moneda);facturas=facturas.filter(moneda_id=moneda_id);cxc=cxc.filter(moneda_id=moneda_id);cobros=cobros.filter(moneda_id=moneda_id)
 filtros={"moneda":moneda,"centro":centro,"proyecto":proyecto,"sucursal":sucursal}
 return {"facturado":total(facturas,"total"),"cobrado":total(cobros,"monto_aplicado"),"pendiente":total(cxc,"saldo"),"vencido":total(cxc.filter(estado__in=["VENCIDA","EN_MORA"]),"saldo"),"factoring":total(CesionFactoring.objects.filter(empresa=empresa,**({"moneda_id":getattr(moneda,"pk",moneda)} if moneda else {})),"monto_cedido"),"movimientos_sin_conciliar":MovimientoTesoreria.objects.filter(empresa=empresa,conciliado=False,**({"cuenta__moneda_id":getattr(moneda,"pk",moneda)} if moneda else {})).count(),"facturas_sin_contabilizar":facturas.exclude(pk__in=[int(x["origen_id"]) for x in diario(empresa=empresa,moneda=moneda) if x["origen_tipo"]=="FACTURA_VENTA" and x["origen_id"].isdigit()]).count(),"tesoreria":posicion(empresa=empresa),"estado_resultados":estado_resultados(empresa=empresa,**filtros),"balance":balance_general(empresa=empresa,**filtros),"drilldown":mayor(empresa=empresa,**filtros) if any((centro,proyecto,sucursal)) else []}
def estados(*,empresa,desde=None,hasta=None):return {"diario":diario(empresa=empresa,desde=desde,hasta=hasta),"mayor":mayor(empresa=empresa,desde=desde,hasta=hasta),"balanza":saldos(empresa=empresa,desde=desde,hasta=hasta),"resultados":estado_resultados(empresa=empresa,desde=desde,hasta=hasta),"balance":balance_general(empresa=empresa,desde=desde,hasta=hasta)}
