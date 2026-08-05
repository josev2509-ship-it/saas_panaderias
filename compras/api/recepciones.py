from compras.application.p2p import crear_recepcion,agregar_detalle_recepcion,cerrar_recepcion,procesar_devolucion
from compras.models import RecepcionCompra
def obtener(*,empresa,recepcion_id):return RecepcionCompra.objects.select_related("orden","almacen").prefetch_related("detalles__detalle_orden","inspecciones","devoluciones").get(pk=recepcion_id,empresa=empresa)
def listar(*,empresa,estado=None,limit=100):
 qs=RecepcionCompra.objects.filter(empresa=empresa).select_related("orden","almacen");qs=qs.filter(estado=estado) if estado else qs;return list(qs.order_by("-fecha","-pk")[:limit])
crear=crear_recepcion;agregar_detalle=agregar_detalle_recepcion;cerrar=cerrar_recepcion;devolver=procesar_devolucion
