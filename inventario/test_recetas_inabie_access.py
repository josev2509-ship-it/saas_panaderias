from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import Group, Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from reportlab.pdfgen import canvas

from conduces.models import Empresa, EmpresaSaaS, PerfilUsuario, Plan, Suscripcion
from conduces.tenant_context import (
    SESSION_SOPORTE_ACTOR,
    SESSION_SOPORTE_INICIADO,
    SESSION_SOPORTE_MOTIVO,
    SESSION_SOPORTE_OPERATIVA,
    SESSION_SOPORTE_SAAS,
)

from .models import ProductoInventario, RecetaProduccion


class RecetasInabieAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("cliente_inabie", password="x")
        self.empresa = Empresa.objects.create(
            usuario=self.user,
            nombre="Tenant A",
            activa=True,
        )
        self.saas = EmpresaSaaS.objects.create(
            nombre="Tenant A",
            correo="tenant-a@example.com",
            activa=True,
            requiere_pago=True,
        )
        PerfilUsuario.objects.create(
            user=self.user,
            empresa=self.saas,
            rol="admin_empresa",
            activo=True,
            correo_validado=True,
        )
        self.plan = Plan.objects.create(
            nombre="INABIE",
            codigo="INABIE_TEST",
            precio=Decimal("1500.00"),
            modulo_inabie=True,
        )
        hoy = timezone.localdate()
        self.suscripcion = Suscripcion.objects.create(
            empresa=self.saas,
            plan=self.plan,
            estado="activa",
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=30),
            periodo_actual_hasta=hoy + timedelta(days=30),
            en_prueba=False,
        )
        self.producto = ProductoInventario.objects.create(
            empresa=self.empresa,
            codigo="PT-A",
            nombre="Producto A",
            tipo="producto_terminado",
            unidad_medida="unidad",
            activo=True,
        )
        self.receta = RecetaProduccion.objects.create(
            empresa=self.empresa,
            codigo="REC-A",
            nombre="Receta A",
            producto_terminado=self.producto,
            rendimiento_base=1,
            unidad_rendimiento="unidad",
            activa=True,
            fecha_vigencia_desde=hoy,
        )
        self.url = reverse("inventario:recetas_lista")
        self.crear_url = reverse("inventario:receta_crear")

    def test_cliente_inabie_sin_permiso_inventario_puede_abrir_recetas(self):
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.has_perm("inventario.view_recetaproduccion"))
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REC-A")

    def test_empresa_sin_modulo_inabie_es_bloqueada(self):
        self.plan.modulo_inabie = False
        self.plan.save(update_fields=["modulo_inabie"])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_empresa_operativa_inactiva_es_bloqueada(self):
        self.empresa.activa = False
        self.empresa.save(update_fields=["activa"])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_suscripcion_vencida_es_bloqueada(self):
        ayer = timezone.localdate() - timedelta(days=1)
        self.suscripcion.estado = "vencida"
        self.suscripcion.fecha_fin = ayer
        self.suscripcion.periodo_actual_hasta = ayer
        self.suscripcion.save(
            update_fields=["estado", "fecha_fin", "periodo_actual_hasta"]
        )
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_listado_no_expone_recetas_de_otro_tenant(self):
        otro = User.objects.create_user("cliente_otro", password="x")
        empresa_b = Empresa.objects.create(usuario=otro, nombre="Tenant B")
        producto_b = ProductoInventario.objects.create(
            empresa=empresa_b,
            codigo="PT-B",
            nombre="Producto B",
            tipo="producto_terminado",
            unidad_medida="unidad",
            activo=True,
        )
        RecetaProduccion.objects.create(
            empresa=empresa_b,
            codigo="REC-B",
            nombre="Receta B",
            producto_terminado=producto_b,
            rendimiento_base=1,
            unidad_rendimiento="unidad",
            fecha_vigencia_desde=timezone.localdate(),
        )
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "REC-A")
        self.assertNotContains(response, "REC-B")

    def test_soporte_autorizado_puede_abrir_recetas_del_tenant(self):
        soporte = User.objects.create_user("soporte_recetas", password="x", is_staff=True)
        grupo, _ = Group.objects.get_or_create(name="Soporte SASTRE")
        soporte.groups.add(grupo)
        self.client.force_login(soporte)
        session = self.client.session
        session[SESSION_SOPORTE_SAAS] = self.saas.pk
        session[SESSION_SOPORTE_OPERATIVA] = self.empresa.pk
        session[SESSION_SOPORTE_MOTIVO] = "Prueba recetas"
        session[SESSION_SOPORTE_INICIADO] = timezone.now().isoformat()
        session[SESSION_SOPORTE_ACTOR] = soporte.pk
        session.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REC-A")

    def test_anonimo_es_redirigido_al_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_admin_empresa_inabie_puede_abrir_nueva_receta_sin_permiso_directo(self):
        self.assertFalse(self.user.has_perm("inventario.add_recetaproduccion"))
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.crear_url).status_code, 200)

    def test_nueva_receta_exige_modulo_inabie(self):
        self.plan.modulo_inabie = False
        self.plan.save(update_fields=["modulo_inabie"])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.crear_url).status_code, 403)

    def test_nueva_receta_exige_suscripcion_vigente(self):
        ayer = timezone.localdate() - timedelta(days=1)
        self.suscripcion.estado = "vencida"
        self.suscripcion.fecha_fin = ayer
        self.suscripcion.periodo_actual_hasta = ayer
        self.suscripcion.save(
            update_fields=["estado", "fecha_fin", "periodo_actual_hasta"]
        )
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.crear_url).status_code, 403)

    def test_operador_no_admin_necesita_permiso_add_recetaproduccion(self):
        perfil = PerfilUsuario.objects.get(user=self.user)
        perfil.rol = "operaciones"
        perfil.save(update_fields=["rol"])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.crear_url).status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="inventario",
            codename="add_recetaproduccion",
        ))
        self.assertEqual(self.client.get(self.crear_url).status_code, 200)

    def test_soporte_sastre_no_puede_crear_sin_permiso_explicito(self):
        soporte = User.objects.create_user("soporte_crear_receta", password="x", is_staff=True)
        grupo, _ = Group.objects.get_or_create(name="Soporte SASTRE")
        soporte.groups.add(grupo)
        self.client.force_login(soporte)
        session = self.client.session
        session[SESSION_SOPORTE_SAAS] = self.saas.pk
        session[SESSION_SOPORTE_OPERATIVA] = self.empresa.pk
        session[SESSION_SOPORTE_MOTIVO] = "Validar creación de receta"
        session[SESSION_SOPORTE_INICIADO] = timezone.now().isoformat()
        session[SESSION_SOPORTE_ACTOR] = soporte.pk
        session.save()
        self.assertEqual(self.client.get(self.crear_url).status_code, 403)

    def _pdf_formula(self):
        salida = BytesIO()
        pdf = canvas.Canvas(salida)
        for y, texto in enumerate((
            "PRODUCTO: Producto A", "CODIGO: PDF-01", "REVISION: 2",
            "RENDIMIENTO BASE: 100 UNIDADES", "Harina 20 LIBRAS",
        )):
            pdf.drawString(40, 800 - y * 20, texto)
        pdf.save()
        return SimpleUploadedFile("formula.pdf", salida.getvalue(), content_type="application/pdf")

    def test_pdf_valido_analiza_y_prellena_sin_guardar(self):
        materia = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="HAR", nombre="Harina", tipo="materia_prima",
            unidad_medida="lb", activo=True,
        )
        antes = RecetaProduccion.objects.count()
        self.client.force_login(self.user)
        respuesta = self.client.post(self.crear_url, {"accion": "analizar", "archivo": self._pdf_formula()})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "PDF-01")
        self.assertContains(respuesta, materia.nombre)
        self.assertEqual(RecetaProduccion.objects.count(), antes)

    def test_archivo_invalido_es_rechazado(self):
        self.client.force_login(self.user)
        archivo = SimpleUploadedFile("falso.pdf", b"no-es-pdf", content_type="application/pdf")
        respuesta = self.client.post(self.crear_url, {"accion": "analizar", "archivo": archivo})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no corresponde a un PDF")

    def test_formatos_de_imagen_validos_llegan_al_fallback_ocr(self):
        self.client.force_login(self.user)
        casos = (
            ("formula.jpg", b"\xff\xd8\xff\xe0resto", "image/jpeg"),
            ("formula.jpeg", b"\xff\xd8\xff\xe0resto", "image/jpeg"),
            ("formula.png", b"\x89PNG\r\n\x1a\nresto", "image/png"),
        )
        for nombre, contenido, mime in casos:
            with self.subTest(nombre=nombre):
                respuesta = self.client.post(self.crear_url, {
                    "accion": "analizar", "archivo": SimpleUploadedFile(nombre, contenido, content_type=mime),
                })
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, "OCR local no instalado")

    def test_aprobar_formula_lista_crea_detalles_en_orden_y_es_idempotente(self):
        harina = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="HAR-ORD", nombre="Harina", tipo="materia_prima", activo=True,
        )
        sal = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="SAL-ORD", nombre="Sal", tipo="materia_prima", activo=True,
        )
        self.client.force_login(self.user)
        self.client.post(self.crear_url, {"accion": "analizar", "archivo": self._pdf_formula()})
        # El PDF auxiliar solo contiene Harina; prueba la aprobación e idempotencia del lote.
        primera = self.client.post(self.crear_url, {"accion": "aprobar_formula", "formula_index": "0"})
        segunda = self.client.post(self.crear_url, {"accion": "aprobar_formula", "formula_index": "0"})
        self.assertEqual(primera.status_code, 302)
        self.assertEqual(segunda.status_code, 302)
        self.assertEqual(RecetaProduccion.objects.filter(empresa=self.empresa, codigo="PDF-01").count(), 1)
        receta = RecetaProduccion.objects.get(empresa=self.empresa, codigo="PDF-01")
        self.assertFalse(receta.activa)
        self.assertEqual(list(receta.ingredientes.values_list("orden", flat=True)), [1])

    def test_confirmar_crea_una_receta_y_reenvio_no_duplica(self):
        materia = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="HAR2", nombre="Harina 2", tipo="materia_prima",
            unidad_medida="lb", activo=True,
        )
        datos = {
            "accion": "guardar", "codigo": "CONF-01", "nombre": "Confirmada",
            "producto_terminado": self.producto.pk, "version": "2", "rendimiento_base": "100",
            "unidad_rendimiento": "unidad", "porcentaje_merma_estimada": "0",
            "fecha_vigencia_desde": timezone.localdate().isoformat(), "instrucciones": "Mezclar",
            "ingredientes-TOTAL_FORMS": "1", "ingredientes-INITIAL_FORMS": "0",
            "ingredientes-MIN_NUM_FORMS": "0", "ingredientes-MAX_NUM_FORMS": "1000",
            "ingredientes-0-materia_prima": materia.pk, "ingredientes-0-cantidad": "20",
            "ingredientes-0-unidad_medida": "lb", "ingredientes-0-porcentaje_merma": "0",
            "ingredientes-0-observaciones": "", "ingredientes-0-orden": "1",
        }
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(self.crear_url, datos).status_code, 302)
        self.assertEqual(RecetaProduccion.objects.filter(codigo="CONF-01").count(), 1)
        self.assertEqual(self.client.post(self.crear_url, datos).status_code, 200)
        self.assertEqual(RecetaProduccion.objects.filter(codigo="CONF-01").count(), 1)
