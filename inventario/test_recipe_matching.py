from django.contrib.auth.models import User
from django.test import TestCase

from conduces.models import Empresa

from .models import ProductoInventario
from .recipe_matching import encontrar_ingrediente, encontrar_producto_terminado, encontrar_producto_terminado_match


class RecipeMatchingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("matching")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Empresa A")
        self.otra = Empresa.objects.create(usuario=User.objects.create_user("matching-b"), nombre="Empresa B")

    def producto(self, nombre, empresa=None, tipo="materia_prima"):
        return ProductoInventario.objects.create(
            empresa=empresa or self.empresa, codigo=f"P-{ProductoInventario.objects.count()}",
            nombre=nombre, tipo=tipo, unidad_medida="lb", activo=True,
        )

    def test_match_exacto_normalizado_misma_empresa(self):
        producto = self.producto("Azúcar refinada")
        resultado = encontrar_ingrediente(empresa=self.empresa, nombre="AZUCAR   REFINADA")
        self.assertEqual(resultado.estado, "EXACTA_NORMALIZADA")
        self.assertEqual(resultado.producto_id, producto.pk)

    def test_no_cruza_empresa_ni_usa_producto_terminado(self):
        self.producto("Harina especial", empresa=self.otra)
        self.producto("Harina especial", tipo="producto_terminado")
        resultado = encontrar_ingrediente(empresa=self.empresa, nombre="Harina especial")
        self.assertEqual(resultado.estado, "SIN_COINCIDENCIA")
        self.assertIsNone(resultado.producto_id)

    def test_ambiguo_requiere_revision(self):
        self.producto("Harina de trigo suave")
        self.producto("Harina de trigo integral")
        resultado = encontrar_ingrediente(empresa=self.empresa, nombre="Harina de trigo")
        self.assertEqual(resultado.estado, "REVISAR")
        self.assertIsNone(resultado.producto_id)
        self.assertEqual(len(resultado.candidatos), 2)

    def test_producto_terminado_respeta_empresa(self):
        esperado = self.producto("Muffin", tipo="producto_terminado")
        self.producto("Muffin", empresa=self.otra, tipo="producto_terminado")
        self.assertEqual(encontrar_producto_terminado(empresa=self.empresa, nombre="muffin"), esperado)

    def test_orden_plural_y_palabras_funcionales_son_alta_confianza(self):
        esperado = self.producto("Muffin de avena y guineo", tipo="producto_terminado")
        resultado = encontrar_producto_terminado_match(empresa=self.empresa, nombre="Muffin de guineo y avena")
        self.assertEqual(resultado.estado, "ALTA_CONFIANZA")
        self.assertEqual(resultado.producto_id, esperado.pk)

    def test_texto_pypdf_con_caracter_reemplazado_puede_relacionarse(self):
        esperado = self.producto("Muffin de maíz", tipo="producto_terminado")
        resultado = encontrar_producto_terminado_match(empresa=self.empresa, nombre="Muffin de Ma�z")
        self.assertEqual(resultado.estado, "ALTA_CONFIANZA")
        self.assertEqual(resultado.producto_id, esperado.pk)

    def test_pan_con_harina_de_maiz_solo_requiere_revision_con_pan(self):
        self.producto("Pan", tipo="producto_terminado")
        resultado = encontrar_producto_terminado_match(empresa=self.empresa, nombre="Pan con harina de maíz")
        self.assertEqual(resultado.estado, "REVISAR")
