from django.test import SimpleTestCase
from django.template.loader import get_template

from core.rc1_audit import route_inventory, template_inventory


class RC1InventoryContracts(SimpleTestCase):
    def test_every_resolved_route_is_classified(self):
        routes = route_inventory()
        self.assertGreaterEqual(len(routes), 200)
        self.assertTrue(all(row["class"] for row in routes))
        self.assertTrue(all(row["callback"] for row in routes))

    def test_every_template_and_control_is_classified(self):
        templates, buttons, forms = template_inventory()
        self.assertGreaterEqual(len(templates), 150)
        self.assertGreaterEqual(len(buttons), 250)
        self.assertGreaterEqual(len(forms), 50)
        self.assertTrue(all(row["class"] for row in templates))
        self.assertTrue(all(row["method"] in {"GET", "POST"} for row in forms))

    def test_visible_inabie_editors_use_enterprise_shell(self):
        names = (
            "editar_conduce.html", "editar_factura.html", "editar_menu.html",
            "editar_producto_facturacion.html",
        )
        for name in names:
            template = get_template(name)
            self.assertIsNotNone(template)
            source = template.origin.loader.get_contents(template.origin)
            self.assertIn('{% extends "base.html" %}', source)
            self.assertIn("{% csrf_token %}", source)
            self.assertNotIn("<aside", source)
