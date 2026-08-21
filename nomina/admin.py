from django.contrib import admin
from .models import (ConceptoNomina, DetalleNominaEmpleado, LiquidacionLaboral, Nomina,
 PeriodoNomina, PrestacionLaboral, TipoNomina, ParametroLegalNomina,
 PlantillaDocumentoRRHH, NovedadNomina, ReciboNomina)
from .models import PrestamoEmpleado, CuotaPrestamoEmpleado

@admin.register(Nomina)
class NominaAdmin(admin.ModelAdmin):
 list_display=("numero","empresa","periodo","estado","total_neto");list_filter=("empresa","estado")

@admin.register(ParametroLegalNomina)
class ParametroLegalNominaAdmin(admin.ModelAdmin):
 list_display=("nombre","empresa","version","vigente_desde","vigente_hasta","activo");list_filter=("empresa","activo")

@admin.register(LiquidacionLaboral)
class LiquidacionLaboralAdmin(admin.ModelAdmin):
 list_display=("empleado","fecha_salida","tipo_terminacion","total","estado","requiere_revision");list_filter=("empresa","estado","requiere_revision")

admin.site.register([TipoNomina,PeriodoNomina,ConceptoNomina,DetalleNominaEmpleado,PrestacionLaboral,PlantillaDocumentoRRHH,NovedadNomina,ReciboNomina,PrestamoEmpleado,CuotaPrestamoEmpleado])
