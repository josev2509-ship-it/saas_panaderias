from decimal import Decimal
from django.db import transaction
from .models import ActivoFijo,DepreciacionActivo
@transaction.atomic
def ejecutar_depreciacion(*,empresa,periodo):
 out=[]
 for a in ActivoFijo.objects.select_for_update().filter(empresa=empresa,estado="ACTIVO",metodo="LINEA_RECTA"):
  if a.depreciaciones.filter(periodo=periodo).exists():continue
  base=a.costo-a.valor_residual;m=(base/Decimal(a.vida_util_meses)).quantize(Decimal("0.01"));acum=min(base,a.depreciacion_acumulada+m);d=DepreciacionActivo.objects.create(empresa=empresa,activo=a,periodo=periodo,monto=acum-a.depreciacion_acumulada,acumulada=acum,valor_libros=a.costo-acum);a.depreciacion_acumulada=acum;a.save();out.append(d)
 return out
