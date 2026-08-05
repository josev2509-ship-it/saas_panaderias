from compras.application.p2p import crear_orden_desde_adjudicacion,transicionar_orden,versionar_orden
from compras.models import OrdenCompraEnterprise
def obtener(*,empresa,orden_id):return OrdenCompraEnterprise.objects.select_related("proveedor","moneda__moneda","adjudicacion").prefetch_related("detalles","historial","versiones").get(pk=orden_id,empresa=empresa)
def listar(*,empresa,estado=None,proveedor=None,limit=100):
 qs=OrdenCompraEnterprise.objects.filter(empresa=empresa).select_related("proveedor","moneda__moneda");qs=qs.filter(estado=estado) if estado else qs;qs=qs.filter(proveedor_id=getattr(proveedor,"pk",proveedor)) if proveedor else qs;return list(qs.order_by("-fecha","-pk")[:limit])
crear_desde_adjudicacion=crear_orden_desde_adjudicacion;transicionar=transicionar_orden;versionar=versionar_orden
