from datetime import timedelta
from django.db.models import Count,Sum,Avg,Q
from django.utils import timezone
from comercial.models import Prospecto,OportunidadComercial,ActividadComercial
def prospectos(empresa):return Prospecto.objects.filter(empresa=empresa).select_related("fuente","canal","segmento","vendedor","equipo","zona","ruta","cliente_convertido")
def oportunidades(empresa):return OportunidadComercial.objects.filter(empresa=empresa).select_related("prospecto","cliente","vendedor","equipo","canal","segmento","zona","ruta","moneda")
def actividades(empresa):return ActividadComercial.objects.filter(empresa=empresa).select_related("prospecto","cliente","oportunidad","responsable")
def prospectos_por_vendedor(empresa,vendedor):return prospectos(empresa).filter(vendedor=vendedor)
def prospectos_por_estado(empresa,estado):return prospectos(empresa).filter(estado=estado)
def oportunidades_por_etapa(empresa,etapa):return oportunidades(empresa).filter(etapa=etapa)
def oportunidades_por_vendedor(empresa,vendedor):return oportunidades(empresa).filter(vendedor=vendedor)
def oportunidades_estancadas(empresa,dias=30):return oportunidades(empresa).exclude(etapa__in=["GANADA","PERDIDA","CANCELADA"]).filter(fecha_actualizacion__lt=timezone.now()-timedelta(days=dias))
def actividades_pendientes(empresa):return actividades(empresa).filter(estado__in=["PENDIENTE","EN_PROGRESO"])
def actividades_vencidas(empresa):return actividades(empresa).filter(Q(estado="VENCIDA")|Q(estado__in=["PENDIENTE","EN_PROGRESO"],fecha_inicio__lt=timezone.now()))
def agenda(empresa,desde,hasta,responsable=None):
    qs=actividades(empresa).filter(fecha_inicio__date__range=(desde,hasta));return qs.filter(responsable=responsable) if responsable else qs
def pipeline(empresa):return oportunidades(empresa).values("etapa","moneda_id").annotate(cantidad=Count("id"),monto=Sum("monto_estimado"),ponderado=Sum("monto_ponderado"),promedio=Avg("probabilidad")).order_by("etapa","moneda_id")
def resumen_crm(empresa):
    p=prospectos(empresa);o=oportunidades(empresa);a=actividades(empresa);convertidos=p.filter(estado="CONVERTIDO").count();total=p.count()
    return {"prospectos":total,"nuevos":p.filter(estado="NUEVO").count(),"contactados":p.filter(estado="CONTACTADO").count(),"calificados":p.filter(estado="CALIFICADO").count(),"convertidos":convertidos,"tasa_conversion":round(convertidos*100/total,2) if total else 0,"oportunidades_abiertas":o.exclude(etapa__in=["GANADA","PERDIDA","CANCELADA"]).count(),"ganadas":o.filter(etapa="GANADA").count(),"perdidas":o.filter(etapa="PERDIDA").count(),"actividades_pendientes":a.filter(estado__in=["PENDIENTE","EN_PROGRESO"]).count(),"actividades_vencidas":actividades_vencidas(empresa).count()}
