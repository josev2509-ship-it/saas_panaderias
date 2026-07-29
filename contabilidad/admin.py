from django.contrib import admin
from .models import *


admin.site.register(Socio)
admin.site.register(AporteSocio)
admin.site.register(DeudaSocio)

admin.site.register(Gasto)

admin.site.register(Factoring)
admin.site.register(PagoFactoring)

admin.site.register(CuentaPorPagar)
admin.site.register(CuentaPorCobrar)

admin.site.register(Presupuesto)

admin.site.register(Proveedor)
admin.site.register(TipoBienesServicios)
admin.site.register(Factura606)