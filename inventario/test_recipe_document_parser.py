from io import BytesIO
from decimal import Decimal

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
        self.assertEqual(resultado.codigo, "")
        self.assertIsNone(resultado.rendimiento_base)
        self.assertEqual(resultado.ingredientes, [])
        self.assertEqual(resultado.estado_campo("codigo"), "NO_DETECTADO")

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
        resultado = self.parser.parse_text("PRODUCTO: Pan\nCODIGO: P-1\nREVISION: 02PAGINA: 1/1")
        self.assertEqual(resultado.revision, "02")

    def test_encabezados_no_se_convierten_en_ingredientes(self):
        resultado = self.parser.parse_text("PRODUCTO: Pan\nCODIGO: P-1\nPAGINA 1 LIBRA\nTOTAL 20 LIBRAS\nHarina 10 LIBRAS")
        self.assertEqual([i.nombre for i in resultado.ingredientes], ["Harina"])
