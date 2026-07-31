from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from conduces.models import Empresa
from inventario.models import OrdenCompra


class OrdenCompraLegadaTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("legado", password="x")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Empresa")
        self.orden = OrdenCompra.objects.create(empresa=self.empresa, proveedor="Proveedor legado")
        self.client.force_login(self.user)

    def test_consulta_historica_se_conserva(self):
        self.assertEqual(self.client.get(reverse("inventario:ordenes_compra")).status_code, 200)
        response = self.client.get(reverse("inventario:detalle_orden_compra", args=[self.orden.pk]))
        self.assertContains(response, "edición congelada")

    def test_creacion_y_edicion_quedan_bloqueadas(self):
        self.assertEqual(self.client.get(reverse("inventario:generar_orden_compra")).status_code, 403)
        self.assertEqual(self.client.get(reverse("inventario:calcular_orden_compra", args=[self.orden.pk])).status_code, 403)

    def test_comando_es_diagnostico(self):
        call_command("auditar_ordenes_compra_heredadas", formato="json")
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.proveedor, "Proveedor legado")
