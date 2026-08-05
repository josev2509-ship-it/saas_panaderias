from compras.application.p2p import crear_oferta,guardar_linea_oferta,transicionar_oferta,solicitar_aclaracion,responder_aclaracion,versionar_oferta
from compras.models import OfertaProveedor
def obtener(*,empresa,oferta_id):return OfertaProveedor.objects.select_related("rfq","proveedor","moneda__moneda").prefetch_related("lineas","versiones","historial","aclaraciones").get(pk=oferta_id,empresa=empresa)
def listar(*,empresa,estado=None,proveedor=None,limit=100):
 qs=OfertaProveedor.objects.filter(empresa=empresa).select_related("rfq","proveedor","moneda__moneda");qs=qs.filter(estado=estado) if estado else qs;qs=qs.filter(proveedor_id=getattr(proveedor,"pk",proveedor)) if proveedor else qs;return list(qs.order_by("-fecha_oferta","-pk")[:limit])
crear=crear_oferta;guardar_linea=guardar_linea_oferta;transicionar=transicionar_oferta;aclarar=solicitar_aclaracion;responder=responder_aclaracion;versionar=versionar_oferta
