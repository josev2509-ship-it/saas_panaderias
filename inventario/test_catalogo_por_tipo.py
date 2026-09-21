from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from conduces.models import Empresa
from .models import ProductoInventario, RecetaProduccion


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CatalogoPorTipoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("catalogo-tipos", password="x")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Empresa A", activa=True)
        self.client.force_login(self.user)
        self.pt = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="PT-000001", nombre="Pan de maíz",
            tipo="producto_terminado", unidad_medida="unidad", origen_catalogo="RECETA",
            requiere_revision=True, activo=True,
        )
        self.materia = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="MP-000001", nombre="Harina",
            tipo="materia_prima", unidad_medida="lb", requiere_revision=True,
        )

    def test_producto_terminado_no_aplica_a_compras_y_muestra_configurado(self):
        self.assertFalse(self.pt.es_articulo_comprable)
        self.assertFalse(self.pt.listo_para_compras)
        respuesta = self.client.get(reverse("inventario:productos") + "?vista=terminados")
        self.assertContains(respuesta, "Configurado")
        self.assertNotContains(respuesta, "Pendiente de completar")

    def test_producto_terminado_no_muestra_campos_comerciales(self):
        respuesta = self.client.get(reverse("inventario:productos") + "?vista=terminados")
        for texto in ("Precio presentación", "Proveedor", "Presentación de compra", "ITBIS"):
            self.assertNotContains(respuesta, texto)

    def test_materia_provisional_muestra_pendiente(self):
        respuesta = self.client.get(reverse("inventario:productos") + "?vista=materias")
        self.assertContains(respuesta, "Pendiente de completar")

    def test_materia_completa_muestra_lista_para_compras(self):
        self.materia.unidad_compra = "saco"
        self.materia.unidad_contenido_compra = "lb"
        self.materia.cantidad_por_empaque = 120
        self.materia.precio_unitario_compra = 2000
        self.materia.requiere_revision = False
        self.materia.save()
        respuesta = self.client.get(reverse("inventario:productos") + "?vista=materias")
        self.assertContains(respuesta, "Lista para compras")

    def test_minimo_cero_no_es_bajo_minimo(self):
        self.materia.stock_actual = 0
        self.materia.stock_minimo = 0
        self.assertFalse(self.materia.esta_bajo_minimo())

    def test_stock_dos_minimo_tres_es_bajo_minimo(self):
        self.materia.stock_actual = 2
        self.materia.stock_minimo = 3
        self.assertTrue(self.materia.esta_bajo_minimo())

    def test_stock_cuatro_minimo_tres_no_es_bajo_minimo(self):
        self.materia.stock_actual = 4
        self.materia.stock_minimo = 3
        self.assertFalse(self.materia.esta_bajo_minimo())

    def test_filtro_terminados(self):
        respuesta = self.client.get(reverse("inventario:productos") + "?vista=terminados")
        self.assertContains(respuesta, self.pt.nombre)
        self.assertNotContains(respuesta, self.materia.nombre)

    def test_filtro_materias(self):
        respuesta = self.client.get(reverse("inventario:productos") + "?vista=materias")
        self.assertContains(respuesta, self.materia.nombre)
        self.assertNotContains(respuesta, self.pt.nombre)

    def test_catalogo_respeta_empresa(self):
        otra = Empresa.objects.create(nombre="Empresa B", activa=True)
        ProductoInventario.objects.create(empresa=otra, nombre="Producto secreto", tipo="producto_terminado")
        respuesta = self.client.get(reverse("inventario:productos"))
        self.assertNotContains(respuesta, "Producto secreto")

    def test_terminado_muestra_receta_mas_reciente(self):
        for version, codigo in ((1, "REC-000001"), (2, "REC-000002")):
            RecetaProduccion.objects.create(
                empresa=self.empresa, codigo=codigo, nombre="Pan", producto_terminado=self.pt,
                version=version, rendimiento_base=Decimal("1658"), unidad_rendimiento="unidad",
                fecha_vigencia_desde=date.today(),
            )
        respuesta = self.client.get(reverse("inventario:productos") + "?vista=terminados")
        self.assertContains(respuesta, "REC-000002 · v2")
        self.assertNotContains(respuesta, "REC-000001 · v1")

    def test_listado_prefetch_no_crece_por_cada_receta(self):
        for indice in range(3):
            producto = ProductoInventario.objects.create(
                empresa=self.empresa, nombre=f"Terminado {indice}", tipo="producto_terminado"
            )
            RecetaProduccion.objects.create(
                empresa=self.empresa, codigo=f"REC-X{indice}", nombre="Pan", producto_terminado=producto,
                version=1, rendimiento_base=1, unidad_rendimiento="unidad", fecha_vigencia_desde=date.today(),
            )
        # Incluye sesión, tenant, permisos y exactamente dos consultas de catálogo
        # (productos + recetas); el número no crece con cada producto.
        with self.assertNumQueries(9):
            respuesta = self.client.get(reverse("inventario:productos") + "?vista=terminados")
            self.assertEqual(respuesta.status_code, 200)

    def test_editar_terminado_preserva_datos_de_compra(self):
        self.pt.unidad_compra = "caja"
        self.pt.unidad_contenido_compra = "unidad"
        self.pt.cantidad_por_empaque = 24
        self.pt.precio_unitario_compra = 99
        self.pt.porcentaje_itbis = 18
        self.pt.proveedor = "Histórico"
        self.pt.stock_minimo = 5
        self.pt.save()
        respuesta = self.client.post(reverse("inventario:editar_producto_inventario", args=[self.pt.pk]), {
            "codigo": self.pt.codigo, "nombre": "Pan actualizado", "unidad_medida": "unidad", "activo": "on",
        })
        self.assertEqual(respuesta.status_code, 302)
        self.pt.refresh_from_db()
        self.assertEqual((self.pt.unidad_compra, self.pt.cantidad_por_empaque, self.pt.precio_unitario_compra,
                          self.pt.porcentaje_itbis, self.pt.proveedor, self.pt.stock_minimo),
                         ("caja", Decimal("24"), Decimal("99"), Decimal("18"), "Histórico", Decimal("5")))

    def test_editar_terminado_oculta_compra_y_mantiene_kardex(self):
        respuesta = self.client.get(reverse("inventario:editar_producto_inventario", args=[self.pt.pk]))
        self.assertContains(respuesta, "Unidad de producción")
        self.assertContains(respuesta, "Kardex")
        self.assertNotContains(respuesta, "¿Cómo lo compras?")
        self.assertNotContains(respuesta, "Precio de la presentación")

    def test_crear_terminado_no_exige_presentacion(self):
        respuesta = self.client.post(reverse("inventario:crear_producto_inventario"), {
            "nombre": "Muffin", "tipo": "producto_terminado", "unidad_medida": "unidad", "activo": "on",
        })
        self.assertEqual(respuesta.status_code, 302)
        producto = ProductoInventario.objects.get(empresa=self.empresa, nombre="Muffin")
        self.assertTrue(producto.codigo.startswith("PT-"))
        self.assertEqual(producto.unidad_compra, "")
        self.assertFalse(producto.requiere_revision)

    def test_excel_y_catalogo_no_exigen_compra_a_terminado(self):
        self.assertFalse(self.pt.configuracion_compra_completa)
        respuesta = self.client.get(reverse("inventario:descargar_plantilla"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertGreater(len(respuesta.content), 0)
