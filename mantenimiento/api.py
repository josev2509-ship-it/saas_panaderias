from .models import OrdenMantenimiento
def ordenes(*,empresa):return [{"id":x.pk,"numero":x.numero,"activo":x.activo.codigo,"estado":x.estado} for x in OrdenMantenimiento.objects.filter(empresa=empresa).select_related("activo")]
