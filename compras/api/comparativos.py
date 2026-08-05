from compras.application.p2p import crear_comparativo,recalcular_comparativo,guardar_escenario,congelar_comparativo
from compras.models import ComparativoCompra
def obtener(*,empresa,comparativo_id):return ComparativoCompra.objects.select_related("rfq","expediente").prefetch_related("lineas__proveedor","escenarios","historial").get(pk=comparativo_id,empresa=empresa)
def listar(*,empresa,estado=None,limit=100):
 qs=ComparativoCompra.objects.filter(empresa=empresa).select_related("rfq","expediente");qs=qs.filter(estado=estado) if estado else qs;return list(qs.order_by("-pk")[:limit])
crear=crear_comparativo;recalcular=recalcular_comparativo;guardar_escenario=guardar_escenario;congelar=congelar_comparativo
