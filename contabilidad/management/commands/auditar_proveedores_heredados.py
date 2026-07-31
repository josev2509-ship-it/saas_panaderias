import csv
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from contabilidad.models import Proveedor


def normalizar_rnc(value):
    return re.sub(r"\D", "", value or "")


class Command(BaseCommand):
    help = "Audita proveedores contables sin modificar datos."

    def add_arguments(self, parser):
        parser.add_argument("--empresa", type=int, help="Reservado para el mapeo futuro; el modelo legado no tiene empresa.")
        parser.add_argument("--formato", choices=("text", "json", "csv"), default="text")
        parser.add_argument("--salida")
        parser.add_argument("--solo-conflictos", action="store_true")

    def handle(self, *args, **options):
        if options["empresa"]:
            self.stderr.write("Advertencia: el proveedor legado no tiene empresa; el filtro solo se registra como requisito de asignación.")
        usados = set(Proveedor.objects.filter(factura606__isnull=False).values_list("pk", flat=True))
        rows = []
        counts = {}
        for proveedor in Proveedor.objects.all().order_by("pk"):
            rnc = normalizar_rnc(proveedor.rnc)
            counts[rnc] = counts.get(rnc, 0) + 1 if rnc else 0
            rows.append({"id": proveedor.pk, "nombre": proveedor.nombre, "rnc_original": proveedor.rnc or "", "rnc_normalizado": rnc, "requiere_empresa": True, "rnc_ausente": not bool(rnc), "consumidor_activo": proveedor.pk in usados})
        for row in rows:
            row["duplicado_probable"] = bool(row["rnc_normalizado"] and counts[row["rnc_normalizado"]] > 1)
            row["clasificacion"] = "DUPLICADO_PROBABLE" if row["duplicado_probable"] else ("RNC_AUSENTE" if row["rnc_ausente"] else "REQUIERE_EMPRESA")
        if options["solo_conflictos"]:
            rows = [r for r in rows if r["duplicado_probable"] or r["rnc_ausente"]]
        output = self._render(rows, options["formato"])
        if options["salida"]:
            Path(options["salida"]).write_text(output, encoding="utf-8")
        else:
            self.stdout.write(output)

    def _render(self, rows, formato):
        if formato == "json":
            return json.dumps(rows, ensure_ascii=False, indent=2)
        if formato == "csv":
            import io
            stream = io.StringIO()
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys() if rows else ["id"])
            writer.writeheader(); writer.writerows(rows)
            return stream.getvalue()
        return "\n".join(f"{r['id']} | {r['nombre']} | {r['clasificacion']} | usado={r['consumidor_activo']}" for r in rows) or "Sin proveedores."
