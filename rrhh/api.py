from .models import Empleado
def empleados(*,empresa):return [{"id":x.pk,"codigo":x.codigo,"nombre":f"{x.nombres} {x.apellidos}","estado":x.estado} for x in Empleado.objects.filter(empresa=empresa)]
