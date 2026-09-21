from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from conduces.models import Empresa
from .models import AliasIngredienteReceta, DetalleRecetaProduccion, ProductoInventario, RecetaProduccion, SecuenciaProductoInventario
from .recipe_catalog import evaluar_ingrediente
from .recipe_document_parser import IngredienteExtraido, RecipeDocumentParser, ResultadoDocumentoRecetas, ResultadoRecetaDocumento
from .test_receta_catalogo_automatico import RecetaCatalogoAutomaticoTests


class AliasYCodigoRecetaTests(TestCase):
    def setUp(self):
        RecetaCatalogoAutomaticoTests.setUp(self)
        self.url = reverse("inventario:receta_crear")

    def analizar(self, *formulas):
        lote = ResultadoDocumentoRecetas(formulas=list(formulas), paginas=len(formulas))
        archivo = SimpleUploadedFile("formulas.pdf", b"%PDF-1.4\n", content_type="application/pdf")
        with patch("inventario.produccion_views.RecipeDocumentParser") as parser:
            parser.return_value.parse_file.return_value = lote
            return self.client.post(self.url, {"accion": "analizar", "archivo": archivo})

    @staticmethod
    def formula(nombre="Pan", ingrediente="Canela en polvo", codigo=""):
        return ResultadoRecetaDocumento(
            nombre=nombre, codigo=codigo, revision="1", rendimiento_base=Decimal("1658"),
            unidad_rendimiento="unidad", total=Decimal("228"), columna_base=0, estado="LISTA",
            ingredientes=[IngredienteExtraido(ingrediente, Decimal("2"), "lb")],
        )

    def test_codigo_vacio_no_bloquea_ni_numera_preview_y_reaprobar_no_duplica(self):
        self.analizar(self.formula())
        self.assertFalse(SecuenciaProductoInventario.objects.filter(empresa=self.empresa, prefijo="REC").exists())
        self.client.post(self.url, {"accion": "aprobar_formula", "formula_index": "0"})
        receta = RecetaProduccion.objects.get(empresa=self.empresa)
        self.assertEqual(receta.codigo, "REC-000001")
        self.client.post(self.url, {"accion": "aprobar_formula", "formula_index": "0"})
        self.assertEqual(RecetaProduccion.objects.filter(empresa=self.empresa).count(), 1)
        self.assertEqual(SecuenciaProductoInventario.objects.get(empresa=self.empresa, prefijo="REC").ultimo_numero, 1)

    def test_codigo_oficial_se_conserva(self):
        self.analizar(self.formula(codigo="INABIE-OFICIAL"))
        self.client.post(self.url, {"accion": "aprobar_formula", "formula_index": "0"})
        self.assertEqual(RecetaProduccion.objects.get(empresa=self.empresa).codigo, "INABIE-OFICIAL")
        self.assertFalse(SecuenciaProductoInventario.objects.filter(empresa=self.empresa, prefijo="REC").exists())

    def test_codigo_automatico_salta_codigo_oficial_ya_ocupado(self):
        RecetaProduccion.objects.create(empresa=self.empresa, codigo="REC-000001", nombre="Pan previo",
            producto_terminado=self.pt, version=2, rendimiento_base=1,
            unidad_rendimiento="unidad", fecha_vigencia_desde=timezone.localdate())
        self.analizar(self.formula())
        self.client.post(self.url, {"accion": "aprobar_formula", "formula_index": "0"})
        self.assertEqual(RecetaProduccion.objects.get(empresa=self.empresa, version=1).codigo, "REC-000002")

    def test_masivo_reutiliza_un_provisional_y_numera_dos_recetas(self):
        self.analizar(self.formula("Galleta de avena", "Canela molida"), self.formula("Muffin de maíz", "Canela molida"))
        with patch("inventario.recipe_catalog.encontrar_ingrediente", side_effect=AssertionError("No recalcular fuzzy")):
            self.client.post(self.url, {"accion": "aprobar_listas"})
        self.assertEqual(RecetaProduccion.objects.filter(empresa=self.empresa).count(), 2)
        self.assertEqual(set(RecetaProduccion.objects.filter(empresa=self.empresa).values_list("codigo", flat=True)), {"REC-000001", "REC-000002"})
        self.assertEqual(ProductoInventario.objects.filter(empresa=self.empresa, nombre="Canela molida").count(), 1)
        self.assertEqual(len(set(DetalleRecetaProduccion.objects.filter(receta__empresa=self.empresa).values_list("materia_prima_id", flat=True))), 1)

    def test_canela_confirmada_crea_alias_y_siguiente_preview_lo_reutiliza(self):
        canela = ProductoInventario.objects.create(empresa=self.empresa, nombre="Canela molida", tipo="materia_prima", unidad_medida="lb")
        respuesta = self.analizar(self.formula(ingrediente="Canela en polvo"))
        self.assertContains(respuesta, "Resolver ingrediente: Canela en polvo")
        self.assertFalse(AliasIngredienteReceta.objects.exists())
        self.client.post(self.url, {"accion": "aprobar_formula", "formula_index": "0",
            "ingrediente_accion_0_0": "existente", "ingrediente_id_0_0": str(canela.pk)})
        alias = AliasIngredienteReceta.objects.get(empresa=self.empresa, alias_normalizado="canela en polvo")
        self.assertEqual(alias.producto_id, canela.pk)
        self.assertEqual(DetalleRecetaProduccion.objects.get(receta__empresa=self.empresa).materia_prima_id, canela.pk)
        self.assertEqual(evaluar_ingrediente(empresa=self.empresa, nombre="Canela en polvo", unidad="lb").estado, "ALIAS_CONFIRMADO")

    def test_leches_y_preparaciones_no_se_fusionan_silenciosamente(self):
        for nombre in ("Leche entera en polvo", "Avena entera", "Zanahoria"):
            ProductoInventario.objects.create(empresa=self.empresa, nombre=nombre, tipo="materia_prima", unidad_medida="lb")
        for detectado in ("Leche en polvo", "Avena molida", "Zanahoria Rallada"):
            match = evaluar_ingrediente(empresa=self.empresa, nombre=detectado, unidad="lb")
            self.assertFalse(match.producto_id, detectado)
        self.analizar(self.formula(ingrediente="Leche en polvo"))
        self.client.post(self.url, {"accion": "aprobar_formula", "formula_index": "0",
            "ingrediente_accion_0_0": "crear"})
        self.assertTrue(ProductoInventario.objects.filter(empresa=self.empresa, nombre="Leche en polvo").exists())
        self.assertFalse(AliasIngredienteReceta.objects.filter(empresa=self.empresa, alias_normalizado="leche en polvo").exists())

    def test_alias_aislado_por_empresa_y_existente_no_recalcula_fuzzy(self):
        canela = ProductoInventario.objects.create(empresa=self.empresa, nombre="Canela molida", tipo="materia_prima", unidad_medida="lb")
        self.analizar(self.formula(ingrediente="Canela molida"))
        ProductoInventario.objects.create(empresa=self.empresa, nombre="Canela molida especial", tipo="materia_prima", unidad_medida="lb")
        with patch("inventario.recipe_catalog.encontrar_ingrediente", side_effect=AssertionError("No recalcular fuzzy")):
            self.client.post(self.url, {"accion": "aprobar_formula", "formula_index": "0"})
        self.assertEqual(DetalleRecetaProduccion.objects.get(receta__empresa=self.empresa).materia_prima_id, canela.pk)
        otra = Empresa.objects.create(nombre="Otra")
        self.assertFalse(AliasIngredienteReceta.objects.filter(empresa=otra).exists())


class PdfRealEquivalenteTests(TestCase):
    def test_seis_formulas_sin_codigo_y_rendimiento_unidad(self):
        paginas = [
            ("Pan con harina de maíz", "Harina de trigo fuerte", "120 100", "Harina de maíz", "108 90", "228 190", "1658 1382"),
            ("Galleta de avena con agua", "Harina de trigo suave", "100 80", "Avena molida", "20 16", "120 96", "1982 1585"),
            ("Muffin de guineo y avena", "Harina de trigo suave", "100 80", "Avena molida", "20 16", "120 96", "2792 2233"),
            ("Muffin de Maíz", "Harina de trigo suave", "100 220", "Harina de maíz", "20 4", "120 24", "2494 499"),
            ("Muffin de Zanahorias", "Harina de trigo suave", "100 80", "Zanahoria Rallada", "20 16", "120 96", "2519 2015"),
            ("Pan de Zanahorias", "Harina de trigo fuerte", "120 100", "Zanahoria", "20 16", "140 116", "1571 1309"),
        ]
        texto = "\n".join(
            f"Formulación de {nombre}\nIngredientes Libras Libras\n{harina} {val_harina}\n{otro} {val_otro}\nTotal {total}\nCantidad en unidades (Onzas) {rendimiento}"
            for nombre, harina, val_harina, otro, val_otro, total, rendimiento in paginas
        )
        lote = RecipeDocumentParser().parse_text(texto)
        self.assertEqual(len(lote.formulas), 6)
        self.assertTrue(all(formula.codigo == "" for formula in lote.formulas))
        self.assertEqual(lote.formulas[0].rendimiento_base, Decimal("1658"))
        self.assertEqual(lote.formulas[0].unidad_rendimiento, "unidad")
        self.assertEqual(lote.formulas[3].columna_base, 0)
        self.assertEqual(lote.formulas[3].ingredientes[0].cantidad, Decimal("100"))

    def test_ninguna_columna_inconsistente_se_selecciona(self):
        lote = RecipeDocumentParser().parse_text(
            "Formulación de Muffin de Maíz\nIngredientes Libras Libras\n"
            "Harina de trigo suave 220 100\nHarina de maíz 4 20\n"
            "Total 68.59 50\nCantidad en unidades (Onzas) 499 2494")
        formula = lote.formulas[0]
        self.assertIsNone(formula.columna_base)
        self.assertEqual(formula.estado, "INCOMPLETA")
