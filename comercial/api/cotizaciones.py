from dataclasses import dataclass
from comercial.models import CotizacionVenta
from comercial.application.o2c import crear_cotizacion,agregar_linea_cotizacion,recalcular_cotizacion,transicionar_cotizacion,versionar_cotizacion,convertir_cotizacion_a_pedido
@dataclass(frozen=True)
class CotizacionDTO:id:int;numero:str;estado:str;version:int;total:str;cliente_id:int
def _dto(o):return CotizacionDTO(o.pk,o.numero,o.estado,o.version,str(o.total),o.cliente_id)
def obtener_cotizacion(*,empresa,pk):return _dto(CotizacionVenta.objects.get(empresa=empresa,pk=pk))
def crear(**kwargs):return _dto(crear_cotizacion(**kwargs))
def agregar_linea(**kwargs):return agregar_linea_cotizacion(**kwargs).pk
def recalcular(**kwargs):return _dto(recalcular_cotizacion(**kwargs))
def transicionar(**kwargs):return _dto(transicionar_cotizacion(**kwargs))
def versionar(**kwargs):return _dto(versionar_cotizacion(**kwargs))
def convertir(**kwargs):return convertir_cotizacion_a_pedido(**kwargs).pk
