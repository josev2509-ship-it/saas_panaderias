from pathlib import Path
from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase

class Enterprise360ContractTests(SimpleTestCase):
    def test_template_compiles_and_contract_is_complete(self):
        get_template("core/experience/enterprise_360.html")
        source = (Path(settings.BASE_DIR) / "core/experience_views.py").read_text(encoding="utf-8")
        for kind in ("cliente", "proveedor", "pedido", "orden", "factura-cliente", "factura-proveedor"):
            self.assertIn(f'"{kind}"', source)
        for tab in ("Documentos", "Actividad", "Auditoría", "Recepciones", "Contabilidad"):
            self.assertIn(tab, source)
        self.assertIn("empresa=empresa", source)
        self.assertIn("has_perm", source)
