from compras.application.financial import crear_solicitud_pago,aprobar_solicitud_y_orden,pagar_orden
from contabilidad.models import OrdenPago
def listar(*,empresa,estado=None,limit=100):
 qs=OrdenPago.objects.filter(empresa=empresa).select_related("solicitud__cuenta__proveedor").prefetch_related("aplicaciones");qs=qs.filter(estado=estado) if estado else qs;return list(qs.order_by("-pk")[:limit])
solicitar=crear_solicitud_pago;aprobar=aprobar_solicitud_y_orden;pagar=pagar_orden
