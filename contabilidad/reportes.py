from decimal import Decimal
from django.db.models import Sum
from .models import AsientoContable,LineaAsientoContable

def diario(*,empresa,desde=None,hasta=None,moneda=None,**dimensiones):
 qs=AsientoContable.objects.filter(empresa=empresa,estado="CONTABILIZADO").select_related("diario","periodo")
 if desde:qs=qs.filter(fecha__gte=desde)
 if hasta:qs=qs.filter(fecha__lte=hasta)
 if moneda:qs=qs.filter(moneda_id=getattr(moneda,"pk",moneda))
 return [{"id":x.pk,"numero":x.numero,"fecha":str(x.fecha),"concepto":x.concepto,"origen_tipo":x.origen_tipo,"origen_id":x.origen_id,"moneda_id":x.moneda_id,"tasa_cambio":str(x.tasa_cambio),"debito":str(x.total_debito),"credito":str(x.total_credito),"debito_base":str(x.total_debito*x.tasa_cambio),"credito_base":str(x.total_credito*x.tasa_cambio)} for x in qs.order_by("fecha","numero")]
def _dimensiones(qs, dimensiones):
 for codigo,valor in dimensiones.items():
  if valor is not None:qs=qs.filter(**{f"dimensiones__{codigo.upper()}":getattr(valor,"pk",valor)})
 return qs
def mayor(*,empresa,cuenta=None,desde=None,hasta=None,moneda=None,centro=None,proyecto=None,sucursal=None,**extra):
 qs=LineaAsientoContable.objects.filter(asiento__empresa=empresa,asiento__estado="CONTABILIZADO").select_related("cuenta","asiento")
 if cuenta:qs=qs.filter(cuenta__codigo=cuenta)
 if desde:qs=qs.filter(asiento__fecha__gte=desde)
 if hasta:qs=qs.filter(asiento__fecha__lte=hasta)
 if moneda:qs=qs.filter(asiento__moneda_id=getattr(moneda,"pk",moneda))
 qs=_dimensiones(qs,{"CENTRO_COSTO":centro,"PROYECTO":proyecto,"SUCURSAL":sucursal,**extra})
 return [{"asiento":x.asiento.numero,"fecha":str(x.asiento.fecha),"cuenta":x.cuenta.codigo,"nombre":x.cuenta.nombre,"moneda_id":x.asiento.moneda_id,"tasa_cambio":str(x.asiento.tasa_cambio),"dimensiones":x.dimensiones,"debito":str(x.debito),"credito":str(x.credito),"debito_base":str(x.debito*x.asiento.tasa_cambio),"credito_base":str(x.credito*x.asiento.tasa_cambio)} for x in qs.order_by("cuenta__codigo","asiento__fecha","pk")]
def saldos(*,empresa,desde=None,hasta=None,moneda=None,centro=None,proyecto=None,sucursal=None,**extra):
 qs=LineaAsientoContable.objects.filter(asiento__empresa=empresa,asiento__estado="CONTABILIZADO")
 if desde:qs=qs.filter(asiento__fecha__gte=desde)
 if hasta:qs=qs.filter(asiento__fecha__lte=hasta)
 if moneda:qs=qs.filter(asiento__moneda_id=getattr(moneda,"pk",moneda))
 qs=_dimensiones(qs,{"CENTRO_COSTO":centro,"PROYECTO":proyecto,"SUCURSAL":sucursal,**extra})
 return list(qs.values("cuenta__codigo","cuenta__nombre","cuenta__tipo").annotate(debito=Sum("debito"),credito=Sum("credito")).order_by("cuenta__codigo"))
def estado_resultados(**filtros):
 rows=saldos(**filtros);ing=sum((x["credito"]-x["debito"] for x in rows if x["cuenta__tipo"]=="INGRESO"),Decimal(0));gasto=sum((x["debito"]-x["credito"] for x in rows if x["cuenta__tipo"] in {"GASTO","COSTO"}),Decimal(0));return {"ingresos":str(ing),"gastos":str(gasto),"resultado":str(ing-gasto)}
def balance_general(**filtros):
 rows=saldos(**filtros);tot={t:Decimal(0) for t in ("ACTIVO","PASIVO","PATRIMONIO")}
 for x in rows:
  if x["cuenta__tipo"] in tot:tot[x["cuenta__tipo"]]+=x["debito"]-x["credito"] if x["cuenta__tipo"]=="ACTIVO" else x["credito"]-x["debito"]
 return {k.lower():str(v) for k,v in tot.items()}
