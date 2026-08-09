from pathlib import Path

from django.core.management.base import BaseCommand

from core.rc1_audit import ROOT, markdown_table, summary


class Command(BaseCommand):
    help = "Genera los inventarios reproducibles del RC1 Pase A."

    def handle(self, *args, **options):
        data = summary()
        target = ROOT / "docs" / "rc1" / "pase_a"
        target.mkdir(parents=True, exist_ok=True)

        route_rows = [{
            "Ruta": row["route"], "Nombre": row["name"], "Clasificación": row["class"],
            "Dinámica": row["dynamic"], "Callback": row["callback"],
        } for row in data["routes"]]
        (target / "INVENTARIO_RUTAS.md").write_text(
            "# Inventario de rutas\n\n"
            f"Total: {len(route_rows)}. Fuente: resolver Django, sin exclusiones.\n\n"
            + markdown_table(["Ruta", "Nombre", "Clasificación", "Dinámica", "Callback"], route_rows)
            + "\n", encoding="utf-8",
        )

        template_rows = [{
            "Template": row["path"], "Nombre lógico": row["logical"],
            "Clasificación": row["class"], "Render detectado": row["rendered"],
            "Extiende": row["extends"], "Inline style": row["inline"],
        } for row in data["templates"]]
        (target / "INVENTARIO_PANTALLAS.md").write_text(
            "# Inventario de pantallas y templates\n\n"
            f"Total: {len(template_rows)} templates. La detección de render se deriva de llamadas Python explícitas; includes y nombres dinámicos se clasifican conservadoramente.\n\n"
            + markdown_table(["Template", "Nombre lógico", "Clasificación", "Render detectado", "Extiende", "Inline style"], template_rows)
            + "\n", encoding="utf-8",
        )

        button_rows = [{
            "Template": row["template"], "Línea": row["line"], "Elemento": row["tag"],
            "Tipo": row["type"], "Etiqueta": row["label"], "Destino": row["target"],
        } for row in data["buttons"]]
        (target / "INVENTARIO_BOTONES.md").write_text(
            "# Inventario de botones y acciones visibles\n\n"
            f"Total estático: {len(button_rows)} controles `a`, `button` e `input` accionables. La validación runtime complementaria cubre enlaces, métodos, CSRF y resolución.\n\n"
            + markdown_table(["Template", "Línea", "Elemento", "Tipo", "Etiqueta", "Destino"], button_rows)
            + "\n", encoding="utf-8",
        )

        form_rows = [{
            "Template": row["template"], "Línea": row["line"], "Método": row["method"],
            "Action": row["action"], "CSRF": row["csrf"],
        } for row in data["forms"]]
        (target / "INVENTARIO_FORMULARIOS.md").write_text(
            "# Inventario de formularios\n\n"
            f"Total estático: {len(form_rows)} formularios. Los POST visibles son además verificados por el crawler QA.\n\n"
            + markdown_table(["Template", "Línea", "Método", "Action", "CSRF"], form_rows)
            + "\n", encoding="utf-8",
        )
        self.stdout.write(self.style.SUCCESS(
            f"RC1: {len(route_rows)} rutas, {len(template_rows)} templates, "
            f"{len(button_rows)} controles y {len(form_rows)} formularios."
        ))
