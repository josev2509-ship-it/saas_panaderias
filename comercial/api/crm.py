from dataclasses import dataclass,asdict
from django.utils import timezone
from comercial.application import crm as services
from comercial.models import Prospecto,OportunidadComercial,ActividadComercial
from comercial.selectors_crm import prospectos,pipeline,agenda,resumen_crm
@dataclass(frozen=True)
class ProspectoDTO:id:int;numero:str;nombre:str;estado:str;vendedor_id:int|None;fecha_proxima_accion:str|None
@dataclass(frozen=True)
class OportunidadDTO:id:int;numero:str;titulo:str;etapa:str;monto:str;ponderado:str;moneda_id:int|None
@dataclass(frozen=True)
class ActividadDTO:id:int;asunto:str;tipo:str;estado:str;fecha_inicio:str;responsable_id:int
def _p(o):return ProspectoDTO(o.pk,o.numero,o.nombre_comercial or o.nombre,o.estado,o.vendedor_id,o.fecha_proxima_accion.isoformat() if o.fecha_proxima_accion else None)
def _o(o):return OportunidadDTO(o.pk,o.numero,o.titulo,o.etapa,str(o.monto_estimado),str(o.monto_ponderado),o.moneda_id)
def _a(o):return ActividadDTO(o.pk,o.asunto,o.tipo,o.estado,o.fecha_inicio.isoformat(),o.responsable_id)
def obtener_prospecto(*,empresa,pk):return _p(Prospecto.objects.get(empresa=empresa,pk=pk))
def buscar_prospectos(*,empresa,q="",limite=50):return tuple(_p(o) for o in prospectos(empresa).filter(nombre__icontains=q)[:min(limite,100)])
def crear_prospecto(**kwargs):return _p(services.crear_prospecto(**kwargs))
def calificar_prospecto(**kwargs):return _p(services.calificar_prospecto(**kwargs))
def convertir_prospecto(**kwargs):return services.convertir_prospecto_a_cliente(**kwargs).pk
def obtener_oportunidad(*,empresa,pk):return _o(OportunidadComercial.objects.get(empresa=empresa,pk=pk))
def crear_oportunidad(**kwargs):return _o(services.crear_oportunidad(**kwargs))
def cambiar_etapa_oportunidad(**kwargs):return _o(services.cambiar_etapa_oportunidad(**kwargs))
def obtener_pipeline(*,empresa):return tuple(dict(x) for x in pipeline(empresa))
def crear_actividad(**kwargs):return _a(services.crear_actividad(**kwargs))
def obtener_agenda(*,empresa,desde=None,hasta=None):
    desde=desde or timezone.localdate();hasta=hasta or desde;return tuple(_a(o) for o in agenda(empresa,desde,hasta))
def obtener_resumen_crm(*,empresa):return dict(resumen_crm(empresa))
