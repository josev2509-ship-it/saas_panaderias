from compras.application.financial import crear_factura_proveedor,validar_e_integrar_factura
from contabilidad.models import FacturaProveedor
def obtener(*,empresa,factura_id):return FacturaProveedor.objects.select_related("proveedor","orden","recepcion","moneda__moneda").prefetch_related("detalles").get(pk=factura_id,empresa=empresa)
def listar(*,empresa,estado=None,proveedor=None,limit=100):
 qs=FacturaProveedor.objects.filter(empresa=empresa).select_related("proveedor","orden","recepcion","moneda__moneda");qs=qs.filter(estado=estado) if estado else qs;qs=qs.filter(proveedor_id=getattr(proveedor,"pk",proveedor)) if proveedor else qs;return list(qs.order_by("-fecha","-pk")[:limit])
crear=crear_factura_proveedor;validar=validar_e_integrar_factura
