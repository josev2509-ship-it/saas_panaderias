from django.utils import timezone
from .models import PlanMantenimiento,OrdenMantenimiento
def generar_mantenimientos(*,empresa,fecha=None):
 fecha=fecha or timezone.localdate();out=[]
 for p in PlanMantenimiento.objects.filter(empresa=empresa,activo_plan=True,proxima_fecha__lte=fecha):
  o,created=OrdenMantenimiento.objects.get_or_create(empresa=empresa,activo=p.activo,plan=p,programada_para=p.proxima_fecha,defaults={"numero":f"OM-{p.pk}-{p.proxima_fecha:%Y%m%d}","tipo":p.tipo,"estado":"PROGRAMADA"})
  if created:out.append(o)
 return out
