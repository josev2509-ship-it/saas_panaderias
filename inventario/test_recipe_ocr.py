from io import BytesIO
from decimal import Decimal
import sys
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from .recipe_document_parser import RecipeDocumentParser
from PIL import Image

from .recipe_ocr import (
    AzureDocumentIntelligenceProvider, EstadoOCRLocal, LocalTesseractRecipeOCRProvider,
    OCRFallo, RecipeOCRProvider, extraer_rendimiento_desde_datos, verificar_ocr_local,
)


class FakeOCR(RecipeOCRProvider):
    def __init__(self, texto="", error=None): self.texto = texto; self.error = error; self.llamadas = 0; self.paginas = []
    def extract_text(self, archivo):
        self.llamadas += 1
        if self.error: raise self.error
        return self.texto
    def extract_pdf_page(self, archivo, page_number):
        self.llamadas += 1; self.paginas.append(page_number)
        if self.error: raise self.error
        return self.texto[page_number] if isinstance(self.texto, dict) else self.texto


class RecipeOCRTests(SimpleTestCase):
    def _imagen(self, nombre="formula.png"):
        salida = BytesIO(); Image.new("RGB", (100, 50), "white").save(salida, format="PNG")
        return SimpleUploadedFile(nombre, salida.getvalue(), content_type="image/png")

    def _datos_tabla_local(self):
        lineas = [
            ["PRODUCTO:", "Muffin", "de", "Zanahoria"], ["CODIGO:", "MZ-01"],
            ["Harina", "de", "trigo", "suave", "100", "lb", "80", "lb", "60", "lb"],
            ["Zanahoria", "50", "lb", "40", "lb", "30", "lb"],
            ["Cantidad", "en", "unidades", "2519", "2015", "1511"],
        ]
        datos = {k: [] for k in ("text", "conf", "page_num", "block_num", "par_num", "line_num", "left")}
        for numero, linea in enumerate(lineas, 1):
            for posicion, token in enumerate(linea):
                datos["text"].append(token); datos["conf"].append("95"); datos["page_num"].append(1)
                datos["block_num"].append(1); datos["par_num"].append(1); datos["line_num"].append(numero)
                datos["left"].append(posicion * 50)
        return datos

    def test_ocr_local_imagen_reconstruye_tabla_utilizable(self):
        falso = SimpleNamespace(Output=SimpleNamespace(DICT="DICT"), pytesseract=SimpleNamespace(tesseract_cmd=""),
                                image_to_data=lambda *a, **k: self._datos_tabla_local())
        with patch.dict(sys.modules, {"pytesseract": falso}), patch(
            "inventario.recipe_ocr.verificar_ocr_local", return_value=EstadoOCRLocal(True, True, True, "tesseract")
        ):
            texto = LocalTesseractRecipeOCRProvider().extract_text(self._imagen())
        formula = RecipeDocumentParser().parse_text(texto).formulas[0]
        self.assertEqual(formula.nombre, "Muffin de Zanahoria")
        self.assertEqual(formula.columna_base, 0)
        self.assertEqual([i.nombre for i in formula.ingredientes], ["Harina de trigo suave", "Zanahoria"])
        self.assertEqual(str(formula.rendimiento_base), "2519")

    def test_ocr_local_pdf_rasteriza_y_usa_tesseract(self):
        falso_ocr = SimpleNamespace(Output=SimpleNamespace(DICT="DICT"), pytesseract=SimpleNamespace(tesseract_cmd=""),
                                    image_to_data=lambda *a, **k: self._datos_tabla_local())
        falso_pdf = SimpleNamespace(convert_from_bytes=lambda *a, **k: [Image.new("RGB", (100, 50), "white")])
        with patch.dict(sys.modules, {"pytesseract": falso_ocr, "pdf2image": falso_pdf}), patch(
            "inventario.recipe_ocr.verificar_ocr_local", return_value=EstadoOCRLocal(True, True, True, "tesseract")
        ):
            texto = LocalTesseractRecipeOCRProvider().extract_text(SimpleUploadedFile("scan.pdf", b"%PDF-falso"))
        self.assertIn("Harina de trigo suave | 100 lb | 80 lb | 60 lb", texto)

    def test_ocr_local_pagina_pdf_rasteriza_solo_pagina_solicitada(self):
        falso_ocr = SimpleNamespace(Output=SimpleNamespace(DICT="DICT"), pytesseract=SimpleNamespace(tesseract_cmd=""),
                                    image_to_data=lambda *a, **k: self._datos_tabla_local())
        convertir = __import__("unittest.mock").mock.Mock(return_value=[Image.new("RGB", (100, 50), "white")])
        falso_pdf = SimpleNamespace(convert_from_bytes=convertir)
        with patch.dict(sys.modules, {"pytesseract": falso_ocr, "pdf2image": falso_pdf}), patch(
            "inventario.recipe_ocr.verificar_ocr_local", return_value=EstadoOCRLocal(True, True, True, "tesseract")
        ):
            LocalTesseractRecipeOCRProvider().extract_pdf_page(SimpleUploadedFile("scan.pdf", b"%PDF-falso"), 5)
        self.assertEqual(convertir.call_args.kwargs["first_page"], 5)
        self.assertEqual(convertir.call_args.kwargs["last_page"], 5)

    def test_extrae_rendimiento_por_geometria_debajo_de_total(self):
        textos = ["Total", "346.38", "277.10", "Cantidad", "en", "unidades", "2,519", "2,015", "1,511", "1,008", "504", "252"]
        datos = {k: [] for k in ("text", "conf", "block_num", "par_num", "line_num", "left", "top")}
        for i, texto in enumerate(textos):
            fila = 1 if i < 3 else 2
            datos["text"].append(texto); datos["conf"].append("92"); datos["block_num"].append(1)
            datos["par_num"].append(1); datos["line_num"].append(fila)
            datos["left"].append((i if fila == 1 else i - 3) * 100); datos["top"].append(500 if fila == 1 else 560)
        resultado = extraer_rendimiento_desde_datos(datos, 0, 6)
        self.assertEqual(resultado["numeros"], [Decimal("2519"), Decimal("2015"), Decimal("1511"), Decimal("1008"), Decimal("504"), Decimal("252")])
        self.assertEqual(resultado["valor"], Decimal("2519"))

    def test_extrae_fila_solo_numerica_en_recorte_inferior(self):
        valores = ["1571", "1309", "1047", "785", "524", "262", "131"]
        datos = {"text": valores, "conf": ["88"] * 7, "block_num": [1] * 7, "par_num": [1] * 7,
                 "line_num": [1] * 7, "left": [i * 100 for i in range(7)], "top": [80] * 7}
        resultado = extraer_rendimiento_desde_datos(datos, 0, 7, permitir_sin_total=True)
        self.assertEqual(resultado["valor"], Decimal("1571"))

    @patch("inventario.recipe_ocr.subprocess.run")
    @patch("inventario.recipe_ocr.shutil.which")
    def test_health_binarios_e_idioma_disponibles(self, which, run):
        which.side_effect = lambda comando: f"/usr/bin/{comando}"; run.return_value = SimpleNamespace(returncode=0, stdout="List of languages\neng\nspa\n")
        estado = verificar_ocr_local()
        self.assertTrue(estado.disponible)
        run.assert_called_once_with(["/usr/bin/tesseract", "--list-langs"], capture_output=True, text=True, timeout=10, check=False)

    @patch("inventario.recipe_ocr.shutil.which", return_value=None)
    def test_health_tesseract_y_poppler_faltantes(self, which):
        estado = verificar_ocr_local()
        self.assertFalse(estado.tesseract_disponible); self.assertFalse(estado.poppler_disponible)

    @patch("inventario.recipe_ocr.subprocess.run")
    @patch("inventario.recipe_ocr.shutil.which")
    def test_health_idioma_spa_faltante(self, which, run):
        which.side_effect = lambda comando: f"/usr/bin/{comando}"; run.return_value = SimpleNamespace(returncode=0, stdout="eng\n")
        self.assertFalse(verificar_ocr_local(lang="spa").idioma_disponible)

    @patch("inventario.recipe_ocr.subprocess.run")
    @patch("inventario.recipe_ocr.shutil.which")
    def test_tesseract_cmd_configurado_se_respeta(self, which, run):
        which.side_effect = lambda comando: "C:/OCR/tesseract.exe" if comando == "C:/OCR/tesseract.exe" else "/usr/bin/pdftoppm"
        run.return_value = SimpleNamespace(returncode=0, stdout="spa\n")
        estado = verificar_ocr_local(tesseract_cmd="C:/OCR/tesseract.exe")
        self.assertEqual(estado.comando_tesseract, "C:/OCR/tesseract.exe")
        self.assertEqual(which.call_args_list[0].args[0], "C:/OCR/tesseract.exe")

    @patch("inventario.recipe_ocr.subprocess.run")
    @patch("inventario.recipe_ocr.shutil.which")
    def test_linux_sin_override_busca_tesseract_en_path(self, which, run):
        which.side_effect = lambda comando: f"/usr/bin/{comando}"; run.return_value = SimpleNamespace(returncode=0, stdout="spa\n")
        verificar_ocr_local(tesseract_cmd="", requiere_poppler=False)
        self.assertEqual(which.call_args_list[0].args[0], "tesseract")

    def test_binario_faltante_es_advertencia_controlada(self):
        falso = SimpleNamespace(Output=SimpleNamespace(DICT="DICT"), pytesseract=SimpleNamespace(tesseract_cmd=""))
        with patch.dict(sys.modules, {"pytesseract": falso}), patch(
            "inventario.recipe_ocr.verificar_ocr_local", return_value=EstadoOCRLocal(False, False, False, "")
        ):
            resultado = RecipeDocumentParser(LocalTesseractRecipeOCRProvider()).parse_file(self._imagen("formula.jpg"))
        self.assertEqual(resultado.formulas, []); self.assertIn("binario tesseract", resultado.advertencias[0])

    def test_poppler_faltante_en_pdf_es_advertencia_controlada(self):
        falso = SimpleNamespace(Output=SimpleNamespace(DICT="DICT"), pytesseract=SimpleNamespace(tesseract_cmd=""))
        salida = BytesIO(); writer = PdfWriter(); writer.add_blank_page(width=100, height=100); writer.write(salida)
        with patch.dict(sys.modules, {"pytesseract": falso}), patch(
            "inventario.recipe_ocr.verificar_ocr_local", return_value=EstadoOCRLocal(True, True, False, "tesseract")
        ):
            resultado = RecipeDocumentParser(LocalTesseractRecipeOCRProvider()).parse_pdf(SimpleUploadedFile("scan.pdf", salida.getvalue()))
        self.assertIn("Poppler", resultado.advertencias[0])

    def test_idioma_faltante_es_advertencia_controlada(self):
        falso = SimpleNamespace(Output=SimpleNamespace(DICT="DICT"), pytesseract=SimpleNamespace(tesseract_cmd=""))
        with patch.dict(sys.modules, {"pytesseract": falso}), patch(
            "inventario.recipe_ocr.verificar_ocr_local", return_value=EstadoOCRLocal(True, False, True, "tesseract")
        ):
            resultado = RecipeDocumentParser(LocalTesseractRecipeOCRProvider()).parse_file(self._imagen("formula.png"))
        self.assertIn("idioma spa", resultado.advertencias[0])
    def test_pdf_digital_no_llama_ocr(self):
        salida = BytesIO(); pdf = canvas.Canvas(salida)
        pdf.drawString(20, 800, "PRODUCTO: Pan escolar"); pdf.drawString(20, 780, "CODIGO: PAN-1")
        pdf.save(); ocr = FakeOCR(error=AssertionError("No debe llamarse"))
        RecipeDocumentParser(ocr).parse_pdf(SimpleUploadedFile("pan.pdf", salida.getvalue()))
        self.assertEqual(ocr.llamadas, 0)

    def test_pdf_sin_texto_llama_ocr(self):
        salida = BytesIO(); writer = PdfWriter(); writer.add_blank_page(width=100, height=100); writer.write(salida)
        ocr = FakeOCR("PRODUCTO: Pan\nCODIGO: P-1\nRENDIMIENTO: 10 UNIDADES\nHarina 1 LIBRA")
        resultado = RecipeDocumentParser(ocr).parse_pdf(SimpleUploadedFile("scan.pdf", salida.getvalue()))
        self.assertEqual(ocr.llamadas, 1); self.assertEqual(resultado.nombre, "Pan")

    def test_jpg_y_png_llaman_ocr(self):
        for nombre in ("formula.jpg", "formula.png"):
            with self.subTest(nombre=nombre):
                ocr = FakeOCR("PRODUCTO: Pan"); RecipeDocumentParser(ocr).parse_file(SimpleUploadedFile(nombre, b"imagen"))
                self.assertEqual(ocr.llamadas, 1)

    def test_imagen_sin_formula_util_muestra_advertencia_y_no_crea_vacia(self):
        resultado = RecipeDocumentParser(FakeOCR("PRODUCTO: Pan")).parse_file(
            SimpleUploadedFile("formula.png", b"imagen")
        )
        self.assertEqual(resultado.formulas, [])
        self.assertIn("No se pudieron interpretar", resultado.advertencias[0])

    def test_fallo_ocr_genera_advertencia_controlada(self):
        resultado = RecipeDocumentParser(FakeOCR(error=OCRFallo("Servicio OCR temporalmente no disponible"))).parse_file(
            SimpleUploadedFile("formula.jpg", b"imagen")
        )
        self.assertEqual(resultado.formulas, []); self.assertIn("temporalmente", resultado.advertencias[0])

    def test_azure_reconstruye_tabla_y_parser_obtiene_caso_muffin(self):
        celdas = []
        filas = [
            ["Harina de trigo suave", "100 lb", "80 lb", "60 lb", "40 lb", "20 lb", "10 lb"],
            ["Zanahoria", "50 lb", "40 lb", "30 lb", "20 lb", "10 lb", "5 lb"],
            ["Azúcar crema", "60 lb", "48 lb", "36 lb", "24 lb", "12 lb", "6 lb"],
            ["Total", "346.38 lb", "277 lb", "208 lb", "139 lb", "69 lb", "35 lb"],
            ["Cantidad en unidades", "2519", "2015", "1511", "1008", "504", "252"],
        ]
        for r, fila in enumerate(filas):
            for c, valor in enumerate(fila): celdas.append({"rowIndex": r, "columnIndex": c, "content": valor})
        respuestas = iter([
            (202, {"Operation-Location": "https://result"}, {}),
            (200, {}, {"status": "succeeded", "analyzeResult": {
                "content": "PRODUCTO: Muffin de Zanahoria\nCODIGO: MZ-01\nREVISION: 02PAGINA: 1/1",
                "tables": [{"cells": celdas}],
            }}),
        ])
        proveedor = AzureDocumentIntelligenceProvider("https://azure.example", "secret", transport=lambda *args: next(respuestas), poll_interval=0)
        texto = proveedor.extract_text(SimpleUploadedFile("muffin.jpg", b"imagen"))
        formula = RecipeDocumentParser().parse_text(texto).formulas[0]
        self.assertEqual(formula.nombre, "Muffin de Zanahoria")
        self.assertEqual(formula.columna_base, 0)
        self.assertEqual([i.nombre for i in formula.ingredientes], ["Harina de trigo suave", "Zanahoria", "Azúcar crema"])
        self.assertEqual(str(formula.rendimiento_base), "2519")
        self.assertEqual(len(RecipeDocumentParser().parse_text(texto).formulas), 1)
