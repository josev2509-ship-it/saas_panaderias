from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from conduces.models import Empresa, EmpresaSaaS, PerfilUsuario, Plan, Suscripcion
from .models import DetalleRecetaProduccion, MovimientoInventario, ProductoInventario, RecetaProduccion
from .recipe_catalog import evaluar_ingrediente, resolver_ingrediente_aprobado
from .recipe_document_parser import IngredienteExtraido, ResultadoDocumentoRecetas, ResultadoRecetaDocumento


class RecetaCatalogoAutomaticoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("catalogo_receta", password="x")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Principal", activa=True)
        saas = EmpresaSaaS.objects.create(nombre="Principal", correo="catalogo@example.com", activa=True, requiere_pago=True)
        PerfilUsuario.objects.create(user=self.user, empresa=saas, rol="admin_empresa", activo=True, correo_validado=True)
        plan = Plan.objects.create(nombre="INABIE Catalogo", codigo="INABIE_CATALOGO", precio=100, modulo_inabie=True)
        hoy = timezone.localdate()
        Suscripcion.objects.create(empresa=saas, plan=plan, estado="activa", fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=30), periodo_actual_hasta=hoy + timedelta(days=30), en_prueba=False)
        self.pt = ProductoInventario.objects.create(empresa=self.empresa, nombre="Pan", tipo="producto_terminado", unidad_medida="unidad")
        self.client.force_login(self.user)

    def aprobar(self, nombre="Harina fuerte", codigo="REC-A", unidad="lb"):
        sesion = self.client.session
        sesion["recetas_importacion_lote"] = [{
            "empresa_id": self.empresa.pk, "estado": "LISTA", "codigo": codigo,
            "nombre": "Pan", "version": 1, "rendimiento_base": "100",
            "unidad_rendimiento": "unidad", "producto_id": self.pt.pk,
            "ingredientes": [{"producto_id": None, "nombre": nombre,
                "cantidad": "20", "unidad": unidad, "orden": 1}],
        }]
        sesion.save()
        return self.client.post(reverse("inventario:receta_crear"), {"accion": "aprobar_formula", "formula_index": "0"})

    def test_preview_no_crea_producto(self):
        formula = ResultadoRecetaDocumento(nombre="Pan", codigo="R-PREVIEW", revision="1",
            rendimiento_base=Decimal("100"), unidad_rendimiento="unidad", estado="LISTA",
            ingredientes=[IngredienteExtraido("Harina fuerte", Decimal("20"), "lb")])
        lote = ResultadoDocumentoRecetas(formulas=[formula], paginas=1)
        archivo = SimpleUploadedFile("formula.pdf", b"%PDF-1.4\n", content_type="application/pdf")
        with patch("inventario.produccion_views.RecipeDocumentParser") as parser:
            parser.return_value.parse_file.return_value = lote
            respuesta = self.client.post(reverse("inventario:receta_crear"), {"accion": "analizar", "archivo": archivo})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Se creará producto provisional")
        self.assertEqual(ProductoInventario.objects.filter(empresa=self.empresa).count(), 1)

    def test_aprobar_crea_provisional_y_referencia_receta_sin_movimiento(self):
        self.assertEqual(self.aprobar().status_code, 302)
        materia = ProductoInventario.objects.get(empresa=self.empresa, nombre="Harina fuerte")
        self.assertEqual(materia.tipo, "materia_prima")
        self.assertEqual(materia.clasificacion_operativa, "materia_prima")
        self.assertEqual(materia.stock_actual, 0)
        self.assertTrue(materia.afecta_produccion)
        self.assertTrue(materia.activo)
        self.assertTrue(materia.requiere_revision)
        self.assertEqual(materia.origen_catalogo, "RECETA")
        self.assertEqual(DetalleRecetaProduccion.objects.get(receta__codigo="REC-A").materia_prima_id, materia.pk)
        self.assertFalse(MovimientoInventario.objects.filter(producto=materia).exists())

    def test_reaprobar_no_duplica_receta_ni_producto(self):
        self.aprobar(); self.aprobar()
        self.assertEqual(RecetaProduccion.objects.filter(empresa=self.empresa, codigo="REC-A").count(), 1)
        self.assertEqual(ProductoInventario.objects.filter(empresa=self.empresa, nombre="Harina fuerte").count(), 1)

    def test_mismo_ingrediente_se_aisla_por_empresa(self):
        otra = Empresa.objects.create(nombre="Otra", activa=True)
        primero = resolver_ingrediente_aprobado(empresa=self.empresa, nombre="Harina fuerte", unidad="lb")
        segundo = resolver_ingrediente_aprobado(empresa=otra, nombre="Harina fuerte", unidad="lb")
        self.assertNotEqual(primero.pk, segundo.pk)
        self.assertEqual(segundo.empresa, otra)

    def test_harinas_calificadas_son_distintas(self):
        fuerte = resolver_ingrediente_aprobado(empresa=self.empresa, nombre="Harina fuerte", unidad="lb")
        normal = resolver_ingrediente_aprobado(empresa=self.empresa, nombre="Harina normal", unidad="lb")
        self.assertNotEqual(fuerte.pk, normal.pk)
        self.assertEqual(evaluar_ingrediente(empresa=self.empresa, nombre="Harina", unidad="lb").estado, "REVISAR")
        self.assertEqual(evaluar_ingrediente(empresa=self.empresa, nombre="Harina fuerte", unidad="lb").producto_id, fuerte.pk)

    def test_unidad_incompatible_requiere_revision(self):
        resolver_ingrediente_aprobado(empresa=self.empresa, nombre="Harina fuerte", unidad="litro")
        self.assertEqual(evaluar_ingrediente(empresa=self.empresa, nombre="Harina fuerte", unidad="lb").estado, "REVISAR")

    def test_edicion_completa_mismo_producto_y_referencia(self):
        self.aprobar()
        materia = ProductoInventario.objects.get(empresa=self.empresa, nombre="Harina fuerte")
        self.client.post(reverse("inventario:editar_producto_inventario", args=[materia.pk]), {
            "codigo": "HF-1", "nombre": "Harina fuerte", "tipo": "materia_prima",
            "clasificacion_operativa": "materia_prima", "unidad_medida": "lb", "unidad_compra": "saco",
            "cantidad_por_empaque": "120", "stock_minimo": "0", "precio_unitario_compra": "100",
            "porcentaje_itbis": "0", "proveedor": "Proveedor", "activo": "on", "afecta_produccion": "on",
        })
        materia.refresh_from_db()
        self.assertEqual(materia.codigo, "HF-1")
        self.assertFalse(materia.requiere_revision)
        self.assertTrue(materia.listo_para_compras)
        self.assertEqual(DetalleRecetaProduccion.objects.get(receta__codigo="REC-A").materia_prima_id, materia.pk)

    def test_listado_muestra_estado_y_origen(self):
        self.aprobar()
        respuesta = self.client.get(reverse("inventario:productos"))
        self.assertContains(respuesta, "Pendiente de completar")
        self.assertContains(respuesta, "Origen: Receta")

    def test_excel_completa_provisional_sin_duplicar(self):
        self.aprobar()
        materia = ProductoInventario.objects.get(empresa=self.empresa, nombre="Harina fuerte")
        libro = Workbook(); hoja = libro.active
        hoja.append(["codigo", "nombre", "tipo", "unidad_medida", "unidad_compra", "cantidad_por_empaque", "precio_unitario_compra"])
        hoja.append(["HF-X", "Harina fuerte", "materia_prima", "lb", "saco", 120, 100])
        salida = BytesIO(); libro.save(salida); salida.seek(0); salida.name = "catalogo.xlsx"
        self.assertEqual(self.client.post(reverse("inventario:cargar_excel"), {"archivo": salida}).status_code, 302)
        materia.refresh_from_db()
        self.assertEqual(materia.codigo, "HF-X")
        self.assertFalse(materia.requiere_revision)
        self.assertEqual(ProductoInventario.objects.filter(empresa=self.empresa, nombre="Harina fuerte").count(), 1)
        self.assertEqual(DetalleRecetaProduccion.objects.get(receta__codigo="REC-A").materia_prima_id, materia.pk)
        self.assertFalse(MovimientoInventario.objects.filter(producto=materia).exists())

    def test_excel_harina_generica_ambigua_no_se_asocia_ni_crea(self):
        resolver_ingrediente_aprobado(empresa=self.empresa, nombre="Harina fuerte", unidad="lb")
        resolver_ingrediente_aprobado(empresa=self.empresa, nombre="Harina normal", unidad="lb")
        libro = Workbook(); hoja = libro.active
        hoja.append(["codigo", "nombre", "tipo", "unidad_medida"])
        hoja.append(["H-AMB", "Harina", "materia_prima", "lb"])
        salida = BytesIO(); libro.save(salida); salida.seek(0); salida.name = "catalogo.xlsx"
        self.client.post(reverse("inventario:cargar_excel"), {"archivo": salida})
        self.assertFalse(ProductoInventario.objects.filter(empresa=self.empresa, codigo="H-AMB").exists())

    def test_transaccion_revierte_provisional_si_receta_invalida(self):
        # Rendimiento inválido falla después de resolver el ingrediente.
        sesion = self.client.session
        sesion["recetas_importacion_lote"] = [{
            "empresa_id": self.empresa.pk, "estado": "LISTA", "codigo": "REC-INVALIDA",
            "nombre": "Pan", "version": 1, "rendimiento_base": "0",
            "unidad_rendimiento": "unidad", "producto_id": self.pt.pk,
            "ingredientes": [{"nombre": "Sal especial", "cantidad": "1", "unidad": "lb", "orden": 1}],
        }]
        sesion.save()
        self.client.post(reverse("inventario:receta_crear"), {"accion": "aprobar_formula", "formula_index": "0"})
        self.assertFalse(ProductoInventario.objects.filter(empresa=self.empresa, nombre="Sal especial").exists())
        self.assertFalse(RecetaProduccion.objects.filter(codigo="REC-INVALIDA").exists())
