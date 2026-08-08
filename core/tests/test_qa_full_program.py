"""Contratos QA-1 para navegación, acciones visibles y shell Enterprise."""

from html.parser import HTMLParser
import re
from collections import Counter
from urllib.parse import urlsplit

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import Resolver404, URLPattern, URLResolver, get_resolver, resolve, reverse

from conduces.models import Empresa
from core.tests.test_full_demo_routes import _static_safe_routes


class InteractiveInventoryParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.forms = []
        self.buttons = []
        self._form = None

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "a" and data.get("href"):
            self.links.append(data["href"])
        elif tag == "form":
            self._form = {
                "action": data.get("action", ""),
                "method": data.get("method", "get").lower(),
                "csrf": False,
            }
            self.forms.append(self._form)
        elif tag == "input" and self._form and data.get("name") == "csrfmiddlewaretoken":
            self._form["csrf"] = True
        elif tag == "button":
            self.buttons.append(data)

    def handle_endtag(self, tag):
        if tag == "form":
            self._form = None


class FullProgramInteractionQATests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            "qa-full", "qa-full@example.test", "test-only"
        )
        Empresa.objects.create(
            usuario=cls.user,
            nombre="Empresa QA Full",
            modulo_conduces=True,
            modulo_facturacion=True,
            modulo_inventario=True,
            modulo_compras=True,
            modulo_catalogos=True,
            modulo_workflow=True,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _responses(self):
        for _, url in _static_safe_routes():
            response = self.client.get(url)
            if response.status_code == 200 and response.get("Content-Type", "").startswith("text/html"):
                yield url, response

    def test_all_visible_local_links_resolve(self):
        broken = []
        checked = set()
        for page, response in self._responses():
            parser = InteractiveInventoryParser()
            parser.feed(response.content.decode(response.charset or "utf-8"))
            for href in parser.links:
                path = urlsplit(href).path
                if not path or not path.startswith("/") or path.startswith(("/static/", "/media/")):
                    continue
                key = (page, path)
                if key in checked:
                    continue
                checked.add(key)
                try:
                    resolve(path)
                except Resolver404:
                    broken.append(f"{page} -> {path}")
        self.assertGreaterEqual(len(checked), 100)
        self.assertFalse(broken, "Enlaces visibles sin resolver:\n" + "\n".join(broken))

    def test_visible_forms_have_valid_actions_and_post_csrf(self):
        failures = []
        forms_seen = 0
        for page, response in self._responses():
            parser = InteractiveInventoryParser()
            parser.feed(response.content.decode(response.charset or "utf-8"))
            for form in parser.forms:
                forms_seen += 1
                action = urlsplit(form["action"] or page).path
                try:
                    resolve(action)
                except Resolver404:
                    failures.append(f"{page}: action sin resolver {action}")
                if form["method"] == "post" and not form["csrf"]:
                    failures.append(f"{page}: POST sin CSRF ({action})")
                if form["method"] not in ("get", "post"):
                    failures.append(f"{page}: método no soportado {form['method']}")
        self.assertGreaterEqual(forms_seen, 20)
        self.assertFalse(failures, "Contratos de formulario inválidos:\n" + "\n".join(failures))

    def test_sidebar_and_topbar_are_shared_across_erp_domains(self):
        routes = (
            reverse("inicio"), reverse("core:workspace_home"),
            reverse("comercial:dashboard"), reverse("comercial:crm_dashboard"),
            reverse("compras:dashboard"), reverse("inventario:dashboard"),
            reverse("inventario:produccion_dashboard"),
            reverse("contabilidad:dashboard_enterprise"), reverse("workflow:dashboard"),
        )
        required = (
            'aria-label="Navegación principal"', 'class="app-sidebar"',
            'class="ds-topbar', 'data-group="comercial"',
            'data-group="inventario"', 'data-group="finanzas"',
        )
        expected_groups = None
        for url in routes:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                html = response.content.decode(response.charset or "utf-8")
                for marker in required:
                    self.assertIn(marker, html)
                groups = tuple(re.findall(r'data-group="([^"]+)"', html))
                if expected_groups is None:
                    expected_groups = groups
                self.assertEqual(groups, expected_groups)

    def test_visible_buttons_are_semantic_and_not_inline_styled(self):
        failures = []
        count = 0
        for page, response in self._responses():
            parser = InteractiveInventoryParser()
            parser.feed(response.content.decode(response.charset or "utf-8"))
            for button in parser.buttons:
                count += 1
                if "style" in button:
                    failures.append(f"{page}: botón con CSS inline")
                button_type = button.get("type", "submit")
                if button_type not in ("button", "submit", "reset"):
                    failures.append(f"{page}: type inválido {button_type}")
        self.assertGreaterEqual(count, 25)
        self.assertFalse(failures, "Botones inconsistentes:\n" + "\n".join(failures))

    def test_route_aliases_are_explicit_and_documented(self):
        paths = []
        stack = [("", get_resolver().url_patterns)]
        while stack:
            prefix, patterns = stack.pop()
            for entry in patterns:
                path = prefix + str(entry.pattern)
                if path.startswith(("admin/", "media/")):
                    continue
                if isinstance(entry, URLResolver):
                    stack.append((path, entry.url_patterns))
                elif isinstance(entry, URLPattern):
                    paths.append("/" + path)
        aliases = {path for path, total in Counter(paths).items() if total > 1}
        documented = {
            "/comercial/o2c/",
            "/comercial/o2c/exportar/<str:tipo>/<str:formato>/",
        }
        self.assertEqual(aliases, documented)

    def test_o2c_export_alias_dispatches_legacy_and_full_types(self):
        cases = (("clientes", "o2c_exportar"), ("facturas", "o2c_full_exportar"))
        for resource, route_name in cases:
            with self.subTest(resource=resource):
                response = self.client.get(
                    reverse(f"comercial:{route_name}", args=[resource, "csv"])
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/csv", response["Content-Type"])
