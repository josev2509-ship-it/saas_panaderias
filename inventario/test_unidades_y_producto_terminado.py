from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import MovimientoInventario, ProductoInventario, RecetaProduccion
from .recipe_document_parser import IngredienteExtraido, ResultadoDocumentoRecetas, ResultadoRecetaDocumento
from .units import convertir, desglosar_empaques, formatear_masa_lb, interpretar_cantidad, sumar, unidades_compatibles
from .test_receta_catalogo_automatico import RecetaCatalogoAutomaticoTests


class UnidadesTests(TestCase):
    def test_masa_exacta(self):
        self.assertEqual(convertir(16, "oz", "lb"), 1)
        self.assertEqual(sumar([(120, "lb"), (2, "oz")], "lb"), Decimal("120.125"))
        self.assertEqual(convertir(1, "kg", "g"), 1000)
        self.assertAlmostEqual(convertir(1, "lb", "kg"), Decimal("0.45359237"))
        self.assertEqual(interpretar_cantidad("120 libras 2 onzas", "lb"), Decimal("120.125"))
        self.assertEqual(interpretar_cantidad("1 kg 250 g", "g"), 1250)
        self.assertEqual(formatear_masa_lb(Decimal("250.0625")), "250 lb 1 oz")

    def test_conteo_y_familias_incompatibles(self):
        self.assertEqual(convertir(1, "docena", "unidad"), 12)
        self.assertFalse(unidades_compatibles("lb", "litro"))
        self.assertFalse(unidades_compatibles("oz", "fl_oz"))
        with self.assertRaises(ValidationError):
            convertir(1, "gal_us", "lb")

    def test_empaques_y_resto(self):
        self.assertEqual(desglosar_empaques(Decimal("250.125"), 120), (2, Decimal("10.125"), 3))
        self.assertEqual(desglosar_empaques(180, 120), (1, Decimal("60"), 2))


class ProductoTerminadoDesdeRecetaTests(TestCase):
    def setUp(self):
        RecetaCatalogoAutomaticoTests.setUp(self)

    def _analizar_sin_pt(self):
        formula = ResultadoRecetaDocumento(nombre="Pan con harina de maíz", codigo="REC-NUEVA", revision="1",
            rendimiento_base=Decimal("100"), unidad_rendimiento="unidad", estado="LISTA",
            ingredientes=[IngredienteExtraido("Harina de maíz", Decimal("20"), "lb")])
        lote = ResultadoDocumentoRecetas(formulas=[formula], paginas=1)
        archivo = SimpleUploadedFile("formula.pdf", b"%PDF-1.4\n", content_type="application/pdf")
        with patch("inventario.produccion_views.RecipeDocumentParser") as parser:
            parser.return_value.parse_file.return_value = lote
            return self.client.post(reverse("inventario:receta_crear"), {"accion": "analizar", "archivo": archivo})

    def test_preview_y_aprobacion_crean_pt_e_ingrediente_atomicamente(self):
        respuesta = self._analizar_sin_pt()
        self.assertContains(respuesta, 'Crear «Pan con harina de maíz»')
        self.assertFalse(ProductoInventario.objects.filter(nombre="Pan con harina de maíz").exists())
        self.client.post(reverse("inventario:receta_crear"), {"accion": "aprobar_formula", "formula_index": "0",
            "producto_accion_0": "crear"})
        pt = ProductoInventario.objects.get(empresa=self.empresa, nombre="Pan con harina de maíz")
        self.assertTrue(pt.codigo.startswith("PT-"))
        receta = RecetaProduccion.objects.get(empresa=self.empresa, codigo="REC-NUEVA")
        self.assertEqual(receta.producto_terminado_id, pt.pk)
        ingrediente = receta.ingredientes.get().materia_prima
        self.assertTrue(ingrediente.codigo.startswith("MP-"))
        self.assertFalse(MovimientoInventario.objects.filter(producto__in=[pt, ingrediente]).exists())
        self.client.post(reverse("inventario:receta_crear"), {"accion": "aprobar_formula", "formula_index": "0",
            "producto_accion_0": "crear"})
        self.assertEqual(ProductoInventario.objects.filter(empresa=self.empresa, nombre="Pan con harina de maíz").count(), 1)

    def test_seleccionar_pt_existente_de_empresa_actual(self):
        self._analizar_sin_pt()
        self.client.post(reverse("inventario:receta_crear"), {"accion": "aprobar_formula", "formula_index": "0",
            "producto_accion_0": "existente", "producto_id_0": str(self.pt.pk)})
        self.assertEqual(RecetaProduccion.objects.get(codigo="REC-NUEVA").producto_terminado_id, self.pt.pk)

    def test_pt_de_otra_empresa_no_se_puede_asociar(self):
        from conduces.models import Empresa
        otro = ProductoInventario.objects.create(empresa=Empresa.objects.create(nombre="Otro"), nombre="Otro pan", tipo="producto_terminado")
        self._analizar_sin_pt()
        self.client.post(reverse("inventario:receta_crear"), {"accion": "aprobar_formula", "formula_index": "0",
            "producto_accion_0": "existente", "producto_id_0": str(otro.pk)})
        self.assertFalse(RecetaProduccion.objects.filter(codigo="REC-NUEVA").exists())

    def test_codigo_manual_opcional_y_codigo_proveedor(self):
        url = reverse("inventario:crear_producto_inventario")
        datos = {"nombre": "Sal", "tipo": "materia_prima", "unidad_contenido_compra": "lb",
            "contenido_compra": "25", "unidad_compra": "saco", "stock_inicial": "0", "activo": "on"}
        self.client.post(url, datos)
        sal = ProductoInventario.objects.get(empresa=self.empresa, nombre="Sal")
        self.assertEqual(sal.codigo, "MP-000001")
        self.assertEqual(sal.unidad_medida, "lb")
        self.assertEqual(sal.unidad_contenido_compra, "lb")
        self.client.post(url, {**datos, "nombre": "Azúcar", "codigo": "PROV-1"})
        self.assertEqual(ProductoInventario.objects.get(nombre="Azúcar").codigo, "PROV-1")

    def test_codigos_por_empresa_y_sin_repeticion(self):
        from conduces.models import Empresa
        from .product_codes import siguiente_codigo_producto
        otro = Empresa.objects.create(nombre="Otra empresa")
        a = siguiente_codigo_producto(empresa=self.empresa, tipo="empaque")
        b = siguiente_codigo_producto(empresa=self.empresa, tipo="empaque")
        c = siguiente_codigo_producto(empresa=otro, tipo="empaque")
        self.assertEqual((a, b, c), ("EMP-000001", "EMP-000002", "EMP-000001"))

    def test_movimiento_compuesto_convierte_antes_del_motor(self):
        materia = ProductoInventario.objects.create(empresa=self.empresa, nombre="Harina", tipo="materia_prima", unidad_medida="lb")
        respuesta = self.client.post(reverse("inventario:registrar_movimiento_manual"), {
            "producto_id": materia.pk, "tipo": "entrada", "cantidad": "120", "unidad_cantidad": "lb",
            "cantidad_adicional": "2", "unidad_adicional": "oz", "referencia": "COMP-1",
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(MovimientoInventario.objects.get(producto=materia).cantidad, Decimal("120.1250"))

    def test_movimiento_rechaza_masa_volumen(self):
        materia = ProductoInventario.objects.create(empresa=self.empresa, nombre="Aceite", tipo="materia_prima", unidad_medida="lb")
        self.client.post(reverse("inventario:registrar_movimiento_manual"), {
            "producto_id": materia.pk, "tipo": "entrada", "cantidad": "1", "unidad_cantidad": "gal_us",
        })
        self.assertFalse(MovimientoInventario.objects.filter(producto=materia).exists())
