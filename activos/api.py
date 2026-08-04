from .models import ActivoFijo
def activos(*,empresa):return [{"id":x.pk,"codigo":x.codigo,"costo":str(x.costo),"depreciacion":str(x.depreciacion_acumulada),"valor_libros":str(x.costo-x.depreciacion_acumulada)} for x in ActivoFijo.objects.filter(empresa=empresa)]
