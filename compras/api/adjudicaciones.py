from compras.application.p2p import crear_adjudicacion,aprobar_adjudicacion
from compras.models import AdjudicacionCompra
def obtener(*,empresa,adjudicacion_id):return AdjudicacionCompra.objects.select_related("expediente","comparativo").prefetch_related("detalles__proveedor","historial").get(pk=adjudicacion_id,empresa=empresa)
def listar(*,empresa,estado=None,limit=100):
 qs=AdjudicacionCompra.objects.filter(empresa=empresa).select_related("expediente","comparativo");qs=qs.filter(estado=estado) if estado else qs;return list(qs.order_by("-pk")[:limit])
crear=crear_adjudicacion;aprobar=aprobar_adjudicacion
