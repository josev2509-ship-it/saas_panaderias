from django.db.models import Sum
from .models import Presupuesto,LineaPresupuesto,EjecucionPresupuestaria
def resumen(*,empresa,presupuesto_id):
 p=Presupuesto.objects.get(pk=presupuesto_id,empresa=empresa);plan=LineaPresupuesto.objects.filter(escenario__presupuesto=p).aggregate(v=Sum("monto"))["v"] or 0;real=EjecucionPresupuestaria.objects.filter(linea__escenario__presupuesto=p).aggregate(v=Sum("monto"))["v"] or 0;return {"id":p.pk,"plan":str(plan),"real":str(real),"variacion":str(plan-real)}
