from dataclasses import dataclass
from comercial.models import Pedido
from comercial.application.o2c import aprobar_pedido_o2c,programar_pedido
@dataclass(frozen=True)
class PedidoDTO:id:int;numero:str;estado:str;total:str;cliente_id:int;cotizacion_id:int|None
def _dto(o):return PedidoDTO(o.pk,o.numero,o.estado,str(o.total),o.cliente_id,o.cotizacion_origen_id)
def obtener_pedido(*,empresa,pk):return _dto(Pedido.objects.get(empresa=empresa,pk=pk))
def aprobar(**kwargs):return _dto(aprobar_pedido_o2c(**kwargs))
def programar(**kwargs):return programar_pedido(**kwargs).pk
