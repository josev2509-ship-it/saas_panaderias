from io import BytesIO
import os
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch, Mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from .recipe_document_parser import RecipeDocumentParser


class RecipeDocumentParserTests(SimpleTestCase):
    def setUp(self):
        self.parser = RecipeDocumentParser()

    def test_extrae_cabecera_ingredientes_decimales_y_unidades(self):
        resultado = self.parser.parse_text("""
        PRODUCTO: MUFFIN DE ZANAHORIA
        CÓDIGO: MZ-001
        REVISIÓN: 02
        FECHA: 08/12/2025
        RENDIMIENTO BASE: 100 LIBRAS
        Harina de trigo suave 100 LIBRAS
        Azúcar 60,5 LIBRAS
        Sal 0.44 LIBRA
        """)
        self.assertEqual(resultado.nombre, "MUFFIN DE ZANAHORIA")
        self.assertEqual(resultado.codigo, "MZ-001")
        self.assertEqual(resultado.revision, "02")
        self.assertEqual(resultado.fecha_actualizacion.isoformat(), "2025-12-08")
        self.assertEqual(resultado.rendimiento_base, 100)
        self.assertEqual(resultado.unidad_rendimiento, "lb")
        self.assertEqual(
            [x.cantidad for x in resultado.ingredientes],
            [Decimal("100"), Decimal("60.5"), Decimal("0.44")],
        )
        self.assertTrue(all(x.unidad == "lb" for x in resultado.ingredientes))

    def test_no_inventa_codigo_rendimiento_ni_ingredientes(self):
        resultado = self.parser.parse_text("PRODUCTO: Pan escolar")
        self.assertEqual(resultado.formulas, [])

    def test_texto_no_interpretable_no_crea_formula_vacia(self):
        resultado = self.parser.parse_text("Documento administrativo sin una tabla de formulación")
        self.assertEqual(resultado.formulas, [])

    def test_debug_de_faltantes_solo_con_flag_y_sin_cambiar_resultado(self):
        pagina = (
            "Formulación de Pan\nIngredientes Libras Libras\nHarina 120 100\n"
            "Total 120 100"
        )
        lector = SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda: pagina)])
        class OCRVacio:
            def extract_pdf_page(self, archivo, numero): return ""
        parser = RecipeDocumentParser(OCRVacio())
        log = Mock()
        with patch("inventario.recipe_document_parser.PdfReader", return_value=lector), patch(
            "inventario.recipe_document_parser.ocr_debug_logger.warning", log
        ):
            with patch.dict(os.environ, {"RECIPE_OCR_DEBUG": "0"}):
                apagado = parser.parse_pdf(SimpleUploadedFile("formula.pdf", b"%PDF-falso"))
            log.assert_not_called()
            with patch.dict(os.environ, {"RECIPE_OCR_DEBUG": "1"}):
                encendido = parser.parse_pdf(SimpleUploadedFile("formula.pdf", b"%PDF-falso"))
        self.assertEqual(apagado.formulas, encendido.formulas)
        log.assert_called_once()
        self.assertIn("parser_page=%s", log.call_args.args[0])
        self.assertEqual(log.call_args.args[-1], ["rendimiento_base"])
        self.assertEqual(log.call_args.args[2], 1)

    def test_unidad_desconocida_se_marca_para_revision(self):
        resultado = self.parser.parse_text("PRODUCTO: Pan\nAvena 2 SACOS")
        self.assertEqual(resultado.ingredientes[0].unidad, "")
        self.assertEqual(resultado.ingredientes[0].estado, "REVISAR")

    def test_pdf_con_texto_se_extrae(self):
        salida = BytesIO()
        pdf = canvas.Canvas(salida)
        pdf.drawString(40, 800, "PRODUCTO: Pan escolar")
        pdf.drawString(40, 780, "CODIGO: PAN-01")
        pdf.drawString(40, 760, "Harina 100 LIBRAS")
        pdf.save()
        archivo = SimpleUploadedFile("formula.pdf", salida.getvalue(), content_type="application/pdf")
        resultado = self.parser.parse_pdf(archivo)
        self.assertEqual(resultado.codigo, "PAN-01")
        self.assertEqual(len(resultado.ingredientes), 1)

    def test_pdf_sin_texto_advierte_ocr(self):
        salida = BytesIO()
        escritor = PdfWriter()
        escritor.add_blank_page(width=200, height=200)
        escritor.write(salida)
        archivo = SimpleUploadedFile("escaneado.pdf", salida.getvalue(), content_type="application/pdf")
        resultado = self.parser.parse_pdf(archivo)
        self.assertTrue(any("OCR" in aviso for aviso in resultado.advertencias))

    def test_varias_formulas_no_mezclan_ingredientes(self):
        lote = self.parser.parse_text("PRODUCTO: Pan A\nCODIGO: A-01\nRENDIMIENTO: 10 UNIDADES\nHarina 2 LIBRAS\nSal 1 ONZA\nPRODUCTO: Pan B\nCODIGO: B-01\nRENDIMIENTO: 20 UNIDADES\nAvena 3 LIBRAS")
        self.assertEqual(len(lote.formulas), 2)
        self.assertEqual([i.nombre for i in lote.formulas[0].ingredientes], ["Harina", "Sal"])
        self.assertEqual([i.nombre for i in lote.formulas[1].ingredientes], ["Avena"])

    def test_tabla_elige_mayor_harina_y_misma_columna(self):
        lote = self.parser.parse_text("PRODUCTO: Muffin\nCODIGO: MZ-01\nHarina de trigo suave | 80 lb | 100 lb | 60 lb\nZanahoria | 40 lb | 50 lb | 30 lb\nAzucar | 48 lb | 60 lb | 36 lb\nTotal | 276.8 lb | 346.38 lb | 208 lb\nCantidad en unidades | 2015 | 2519 | 1511")
        formula = lote.formulas[0]
        self.assertEqual(formula.columna_base, 1)
        self.assertEqual([i.cantidad for i in formula.ingredientes], [Decimal("100"), Decimal("50"), Decimal("60")])
        self.assertEqual(formula.total, Decimal("346.38"))
        self.assertEqual(formula.rendimiento_base, Decimal("2519"))

    def test_revision_no_se_contamina_con_pagina(self):
        resultado = self.parser.parse_text("PRODUCTO: Pan\nCODIGO: P-1\nREVISION: 02PAGINA: 1/1\nHarina 1 LIBRA")
        self.assertEqual(resultado.revision, "02")

    def test_encabezados_no_se_convierten_en_ingredientes(self):
        resultado = self.parser.parse_text("PRODUCTO: Pan\nCODIGO: P-1\nPAGINA 1 LIBRA\nTOTAL 20 LIBRAS\nHarina 10 LIBRAS")
        self.assertEqual([i.nombre for i in resultado.ingredientes], ["Harina"])

    def test_documento_real_seis_paginas_y_outliers(self):
        paginas = [
            "Formulación:\nIngredientes Libras Libras\nHarina de trigo fuerte 120 100\nHarina de maíz 12 10\nTotal: 132 110\nCantidad en\nunidades (Onzas) 1,658 1,382\nPan con harina de maíz",
            "Formulación de galleta de avena con agua:\nIngredientes Libras Libras Libras\nHarina de trigo suave 100 80 110\nAzúcar crema 37 29.6 3.7\nTotal: 137 109.6 13.7\nCantidad en\nunidades (Onzas) 1,982 1,585 198",
            "Formulación de Muffin de guineo y avena\nIngredientes Libras Libras\nHarina de trigo suave 100 80\nAvena molida 20 16\nTotal: 120 96\nCantidad en\nunidades (Onzas) 2,792 2,233",
            "Formulación de Muffin de Maíz\nIngredientes Libras Libras Libras\nHarina de trigo suave 100 80 220\nHarina de maíz 20 16 4\nTotal: 120 96 24\nCantidad en\nunidades (Onzas) 2,494 1,995 499",
            "Formulación de Muffin de Zanahorias\nIngredientes Libras Libras\nHarina de trigo suave 100 80\nZanahoria 50 40\nAzúcar crema 60 48\nCanela molida 0.22 0.18\nPolvo de hornear 4.50 3.60\nLeche en polvo 5 4\nAgua 27 21.60\nAceite de soya o girasol 35 28\nHuevos 60 48\nVainilla 4 3.20\nSal 0.44 0.35\nNuez moscada molida 0.22 0.18\nTotal: 346.38 277.10\nCantidad en\nunidades (Onzas) 2,519 2,015",
            "Formulación de Pan de Zanahorias\nIngredientes Libras Libras\nHarina de trigo fuerte 120 100\nAzúcar crema 7.2 6\nTotal: 127.2 106\nCantidad en\nunidades (Onzas) 1,571 1,309",
        ]
        lector = SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda texto=texto: texto) for texto in paginas])
        with patch("inventario.recipe_document_parser.PdfReader", return_value=lector):
            lote = self.parser.parse_pdf(SimpleUploadedFile("formulaciones.pdf", b"%PDF-falso"))
        self.assertEqual(len(lote.formulas), 6)
        self.assertEqual([f.nombre for f in lote.formulas], [
            "Pan con harina de maíz", "galleta de avena con agua", "Muffin de guineo y avena",
            "Muffin de Maíz", "Muffin de Zanahorias", "Pan de Zanahorias",
        ])
        self.assertEqual([f.rendimiento_base for f in lote.formulas], [
            Decimal("1658"), Decimal("1982"), Decimal("2792"), Decimal("2494"), Decimal("2519"), Decimal("1571"),
        ])
        self.assertEqual([lote.formulas[i].ingredientes[0].cantidad for i in range(6)], [
            Decimal("120"), Decimal("100"), Decimal("100"), Decimal("100"), Decimal("100"), Decimal("120"),
        ])
        self.assertEqual(len(lote.formulas[4].ingredientes), 12)
        self.assertEqual([i.nombre for i in lote.formulas[4].ingredientes[:3]], ["Harina de trigo suave", "Zanahoria", "Azúcar crema"])
        self.assertTrue(any("110" in a for a in lote.formulas[1].advertencias))
        self.assertTrue(any("220" in a for a in lote.formulas[3].advertencias))

    def test_fallback_ocr_solo_en_pagina_incompleta_y_completa_rendimiento(self):
        pagina_completa = "Formulación de Pan\nIngredientes Libras Libras\nHarina 100 80\nTotal 100 80\nCantidad en\nunidades 1000 800"
        pagina_incompleta = "Formulación de Muffin\nIngredientes Libras Libras\nHarina 100 80\nTotal 100 80"
        pagina_ocr = pagina_incompleta + "\nCantidad en\nunidades 2519 2015"

        class OCRPagina:
            def __init__(self): self.paginas = []
            def extract_pdf_page(self, archivo, numero): self.paginas.append(numero); return pagina_ocr

        ocr = OCRPagina()
        lector = SimpleNamespace(pages=[
            SimpleNamespace(extract_text=lambda: pagina_completa),
            SimpleNamespace(extract_text=lambda: pagina_incompleta),
        ])
        with patch("inventario.recipe_document_parser.PdfReader", return_value=lector):
            lote = RecipeDocumentParser(ocr).parse_pdf(SimpleUploadedFile("formulas.pdf", b"%PDF-falso"))
        self.assertEqual(ocr.paginas, [2])
        self.assertEqual(lote.formulas[1].rendimiento_base, Decimal("2519"))
        self.assertEqual(lote.formulas[1].ingredientes[0].cantidad, Decimal("100"))

    def test_ocr_de_rendimiento_no_sobrescribe_campos_digitales(self):
        digital = "Formulación de Muffin\nIngredientes Libras Libras\nHarina 100 80\nTotal 100 80"
        ocr_texto = "Formulación de Muffin\nIngredientes Libras Libras\nHarina 90 70\nTotal 90 70\nCantidad en\nunidades 2519 2015"

        class OCRPagina:
            def extract_pdf_page(self, archivo, numero): return ocr_texto

        lector = SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda: digital)])
        with patch("inventario.recipe_document_parser.PdfReader", return_value=lector):
            formula = RecipeDocumentParser(OCRPagina()).parse_pdf(
                SimpleUploadedFile("formula.pdf", b"%PDF-falso")
            ).formulas[0]
        self.assertEqual(formula.ingredientes[0].cantidad, Decimal("100"))
        self.assertEqual(formula.rendimiento_base, Decimal("2519"))
        self.assertFalse(any("harina" in aviso.lower() for aviso in formula.advertencias))
