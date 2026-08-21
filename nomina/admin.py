from django.contrib import admin
from .models import ConceptoNomina,DetalleNominaEmpleado,LiquidacionLaboral,Nomina,PeriodoNomina,PrestacionLaboral,TipoNomina

@admin.register(Nomina)
class NominaAdmin(admin.ModelAdmin):
 list_display=("numero","empresa","periodo","estado","total_neto");list_filter=("empresa","estado")

admin.site.register([TipoNomina,PeriodoNomina,ConceptoNomina,DetalleNominaEmpleado,LiquidacionLaboral,PrestacionLaboral])
