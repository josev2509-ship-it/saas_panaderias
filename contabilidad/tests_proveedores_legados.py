from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from contabilidad.models import Proveedor


class AuditoriaProveedorLegadoTest(TestCase):
    def test_normaliza_sin_modificar(self):
        proveedor = Proveedor.objects.create(nombre="Proveedor", rnc="1-01 12345-6")
        salida = StringIO()
        call_command("auditar_proveedores_heredados", formato="json", stdout=salida)
        self.assertIn("101123456", salida.getvalue())
        proveedor.refresh_from_db()
        self.assertEqual(proveedor.rnc, "1-01 12345-6")
