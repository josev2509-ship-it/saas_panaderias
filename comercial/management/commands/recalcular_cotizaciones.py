from django.db.models import Sum
from comercial.models import CotizacionVenta
from ._o2c_base import EmpresaCommand
class Command(EmpresaCommand):
    mutates=True
    def handle(self,*a,**o):
        e=self.empresa(o);q=CotizacionVenta.objects.filter(empresa=e);n=q.count()
        if not o["dry_run"]:
            for c in q:
                t=c.detalles.aggregate(s=Sum("subtotal"),d=Sum("descuento"),i=Sum("impuesto"),t=Sum("total"));c.subtotal=t["s"] or 0;c.descuento_total=t["d"] or 0;c.impuesto_total=t["i"] or 0;c.total=t["t"] or 0;c.save(update_fields=["subtotal","descuento_total","impuesto_total","total"])
        self.stdout.write(f"Cotizaciones a recalcular: {n}." if o["dry_run"] else self.style.SUCCESS(f"Cotizaciones recalculadas: {n}."))
