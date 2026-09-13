from django.test import SimpleTestCase
from django import forms

from .produccion_forms import IngredienteForm, RecetaProduccionForm
from .recipe_units import normalizar_unidad, unidad_reconocida


class RecipeUnitsTests(SimpleTestCase):
    def test_normaliza_kilogramos(self):
        self.assertEqual(normalizar_unidad("Kilogramos"), "kg")
        self.assertEqual(normalizar_unidad("KILOS"), "kg")

    def test_normaliza_gramos(self):
        self.assertEqual(normalizar_unidad("gramos"), "g")
        self.assertEqual(normalizar_unidad("grs"), "g")

    def test_normaliza_libras(self):
        self.assertEqual(normalizar_unidad("LIBRAS"), "lb")
        self.assertEqual(normalizar_unidad("lb"), "lb")

    def test_normaliza_onzas(self):
        self.assertEqual(normalizar_unidad("onzas"), "oz")

    def test_normaliza_litros(self):
        self.assertEqual(normalizar_unidad("litros"), "L")

    def test_normaliza_mililitros(self):
        self.assertEqual(normalizar_unidad("mililitros"), "ml")

    def test_unidad_desconocida_no_se_inventa(self):
        self.assertEqual(normalizar_unidad("sacos"), "")
        self.assertFalse(unidad_reconocida("sacos"))

    def test_formularios_usan_select_controlado(self):
        self.assertIsInstance(RecetaProduccionForm().fields["unidad_rendimiento"].widget, forms.Select)
        self.assertIsInstance(IngredienteForm().fields["unidad_medida"].widget, forms.Select)
