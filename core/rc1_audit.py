"""Inventario reproducible de superficie UI/HTTP para RC1 Pase A."""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path

from django.urls import URLPattern, URLResolver, get_resolver


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {"venv", ".git", "staticfiles", "media"}
MUTABLE_WORDS = {
    "accion", "activar", "actualizar", "anular", "aprobar", "cancelar",
    "cerrar", "completar", "crear", "desactivar", "desembolsar", "duplicar",
    "editar", "eliminar", "emitir", "enviar", "estado", "facturar", "generar",
    "importar", "iniciar", "integrar", "pagar", "registrar", "rechazar",
    "reintentar", "revertir", "solicitar", "toggle", "validar",
}
DOWNLOAD_WORDS = {"descargar", "download", "pdf", "imprimir", "plantilla"}
EXPORT_WORDS = {"exportar", "exportacion", "csv", "xlsx", "excel"}
API_WORDS = {"api", "ajax", "autocomplete", "buscar-productos", "lookup"}
LEGACY_WORDS = {"legacy", "legado", "antiguo"}


def _words(route: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", route.lower().replace("_", "-")))


def classify_route(route: str, name: str | None) -> str:
    words = _words(f"{route} {name or ''}")
    if route.startswith("admin/"):
        return "ADMIN"
    if words & DOWNLOAD_WORDS:
        return "DESCARGA"
    if words & EXPORT_WORDS:
        return "EXPORTACIÓN"
    if words & API_WORDS:
        return "API"
    if words & MUTABLE_WORDS:
        return "POST/MUTABLE"
    if words & LEGACY_WORDS:
        return "LEGACY"
    return "GET SEGURA"


def route_inventory():
    rows = []
    stack = [("", "", get_resolver().url_patterns)]
    while stack:
        prefix, namespace, patterns = stack.pop()
        for entry in patterns:
            route = prefix + str(entry.pattern)
            if isinstance(entry, URLResolver):
                child_ns = ":".join(filter(None, (namespace, entry.namespace)))
                stack.append((route, child_ns, entry.url_patterns))
                continue
            if not isinstance(entry, URLPattern):
                continue
            full_name = ":".join(filter(None, (namespace, entry.name))) or "—"
            callback = getattr(entry.callback, "__module__", "") + "." + getattr(
                entry.callback, "__name__", entry.callback.__class__.__name__
            )
            rows.append({
                "route": "/" + route,
                "name": full_name,
                "callback": callback.strip("."),
                "class": classify_route(route, full_name),
                "dynamic": "Sí" if "<" in route else "No",
            })
    return sorted(rows, key=lambda row: (row["route"], row["name"]))


def _rendered_template_names() -> set[str]:
    names = set()
    for path in ROOT.rglob("*.py"):
        if EXCLUDED_PARTS.intersection(path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            called = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
            if called not in {"render", "render_to_string", "TemplateResponse"}:
                continue
            for arg in node.args[:2]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.endswith(".html"):
                    names.add(arg.value)
    return names


def _template_logical_path(path: Path) -> str:
    parts = list(path.parts)
    if "templates" in parts:
        return "/".join(parts[parts.index("templates") + 1 :])
    return path.name


def classify_template(path: Path, text: str, rendered: bool) -> str:
    rel = path.relative_to(ROOT).as_posix().lower()
    name = path.name.lower()
    if any(word in rel for word in ("print", "impresion", "pdf", "email", "documento", "vista_conduce")):
        return "IMPRESIÓN/DOCUMENTO"
    if name in {"login.html", "registro.html", "password_reset.html", "verificar_correo.html"}:
        return "ENTERPRISE"
    if rel.startswith("design_system/templates/"):
        return "INTERNA"
    if any(part in rel for part in ("/partials/", "/includes/", "/components/")) or name.startswith("_"):
        return "PARCIAL"
    if not rendered:
        return "LEGACY NO VISIBLE" if "legacy" in rel or "backup" in rel else "NO APLICA DEMO"
    if "base.html" in text or "base_public.html" in text or "ds-app" in text:
        return "ENTERPRISE"
    return "LEGACY VISIBLE"


TAG_RE = re.compile(r"<(a|button|input|select|textarea|form)\b([^>]*)>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+)))?", re.S)


def _attrs(raw: str) -> dict[str, str]:
    return {m.group(1).lower(): next((v for v in m.groups()[1:] if v is not None), "") for m in ATTR_RE.finditer(raw)}


def template_inventory():
    rendered_names = _rendered_template_names()
    templates, buttons, forms = [], [], []
    for path in ROOT.rglob("*.html"):
        if EXCLUDED_PARTS.intersection(path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        logical = _template_logical_path(path)
        rendered = logical in rendered_names
        templates.append({
            "path": path.relative_to(ROOT).as_posix(),
            "logical": logical,
            "class": classify_template(path, text, rendered),
            "rendered": "Sí" if rendered else "No",
            "extends": "Sí" if "{% extends" in text else "No",
            "inline": len(re.findall(r"\sstyle\s*=", text, re.I)),
        })
        for match in TAG_RE.finditer(text):
            tag, raw = match.group(1).lower(), match.group(2)
            attrs = _attrs(raw)
            line = text.count("\n", 0, match.start()) + 1
            if tag == "form":
                forms.append({
                    "template": logical,
                    "line": line,
                    "method": attrs.get("method", "GET").upper(),
                    "action": attrs.get("action", "actual"),
                    "csrf": "Sí" if "csrf_token" in text[match.end(): text.find("</form>", match.end()) if "</form>" in text[match.end():] else len(text)] else "No/NA",
                })
            if tag in {"a", "button", "input"}:
                kind = attrs.get("type", "link" if tag == "a" else "submit")
                if tag == "input" and kind not in {"submit", "button", "reset"}:
                    continue
                label = attrs.get("aria-label") or attrs.get("title") or attrs.get("value") or attrs.get("name") or "(texto interno)"
                buttons.append({
                    "template": logical,
                    "line": line,
                    "tag": tag,
                    "type": kind,
                    "target": attrs.get("href") or attrs.get("formaction") or "formulario/JS",
                    "label": re.sub(r"\s+", " ", label)[:80],
                })
    return (
        sorted(templates, key=lambda row: row["path"]),
        sorted(buttons, key=lambda row: (row["template"], row["line"])),
        sorted(forms, key=lambda row: (row["template"], row["line"])),
    )


def markdown_table(headers, rows):
    def clean(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(clean(row[key]) for key in headers) + " |" for row in rows)
    return "\n".join(lines)


def summary():
    routes = route_inventory()
    templates, buttons, forms = template_inventory()
    return {
        "routes": routes,
        "templates": templates,
        "buttons": buttons,
        "forms": forms,
        "route_classes": Counter(row["class"] for row in routes),
        "template_classes": Counter(row["class"] for row in templates),
    }
