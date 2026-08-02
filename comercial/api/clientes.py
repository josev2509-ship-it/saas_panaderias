from dataclasses import dataclass
from comercial.models import Cliente
from comercial.application.o2c import calcular_riesgo_cliente,actualizar_limite_credito,cambiar_estado_cliente
@dataclass(frozen=True)
class Cliente360DTO:id:int;codigo:str;nombre:str;estado:str;limite:str;utilizado:str;disponible:str;score:int;categoria:str
def _dto(o):return Cliente360DTO(o.pk,o.codigo,o.nombre_comercial,o.estado,str(o.limite_credito),str(o.credito_utilizado),str(o.credito_disponible),o.score_riesgo,o.categoria_riesgo)
def obtener_cliente(*,empresa,pk):return _dto(Cliente.objects.get(empresa=empresa,pk=pk))
def obtener_riesgo(**kwargs):return calcular_riesgo_cliente(**kwargs)
def actualizar_credito(**kwargs):return _dto(actualizar_limite_credito(**kwargs))
def cambiar_estado(**kwargs):return _dto(cambiar_estado_cliente(**kwargs))
