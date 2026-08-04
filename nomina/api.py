from .models import Nomina
def nominas(*,empresa):return [{"id":x.pk,"numero":x.numero,"estado":x.estado,"neto":str(x.total_neto)} for x in Nomina.objects.filter(empresa=empresa)]
