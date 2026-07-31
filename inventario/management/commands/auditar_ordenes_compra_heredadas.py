import json
from collections import Counter

from django.core.management.base import BaseCommand

from inventario.models import OrdenCompra


class Command(BaseCommand):
    help = "Audita órdenes de compra heredadas sin modificar datos."

    def add_arguments(self, parser):
        parser.add_argument("--empresa", type=int)
        parser.add_argument("--formato", choices=("text", "json"), default="text")
        parser.add_argument("--solo-conflictos", action="store_true")

    def handle(self, *args, **options):
        qs = OrdenCompra.objects.prefetch_related("detalles").order_by("pk")
        if options["empresa"]:
            qs = qs.filter(empresa_id=options["empresa"])
        numeros = Counter(qs.values_list("empresa_id", "numero"))
        rows = []
        for orden in qs:
            sin_producto = orden.detalles.filter(producto__isnull=True).count()
            inconsistencias = []
            if numeros[(orden.empresa_id, orden.numero)] > 1: inconsistencias.append("NUMERO_DUPLICADO")
            if not orden.proveedor: inconsistencias.append("PROVEEDOR_VACIO")
            if sin_producto: inconsistencias.append("PRODUCTO_MANUAL")
            rows.append({
                "id": orden.pk, "empresa_id": orden.empresa_id, "numero": orden.numero,
                "proveedor_textual": orden.proveedor or "", "estado": orden.estado,
                "recibida": orden.inventario_actualizado, "lineas": orden.detalles.count(),
                "lineas_manuales": sin_producto, "inconsistencias": inconsistencias,
                "migracion": "REQUIERE_INTERVENCION" if inconsistencias else "CANDIDATA",
            })
        if options["solo_conflictos"]: rows = [r for r in rows if r["inconsistencias"]]
        if options["formato"] == "json":
            self.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            self.stdout.write("\n".join(f"{r['numero']} | empresa={r['empresa_id']} | {r['estado']} | {r['migracion']}" for r in rows) or "Sin órdenes.")
