import shutil
import tempfile
from datetime import date

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from auditoria.models import EventoAuditoria
from comercial.models import Cliente
from conduces.models import Empresa

from .models import Documento, TipoDocumento
from .services import anular_documento, crear_documento_asociado, reemplazar_documento


TEST_MEDIA = tempfile.mkdtemp(prefix="documentos-tests-")


@override_settings(MEDIA_ROOT=TEST_MEDIA, DOCUMENTOS_MAX_UPLOAD_SIZE=128)
class DocumentosTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user_a = User.objects.create_user("doc-a", password="clave")
        self.user_b = User.objects.create_user("doc-b", password="clave")
        self.empresa_a = Empresa.objects.create(usuario=self.user_a, nombre="Empresa A")
        self.empresa_b = Empresa.objects.create(usuario=self.user_b, nombre="Empresa B")
        self.cliente_a = Cliente.objects.create(
            empresa=self.empresa_a, codigo="A1", nombre_comercial="Cliente A",
            tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,
        )
        self.cliente_b = Cliente.objects.create(
            empresa=self.empresa_b, codigo="B1", nombre_comercial="Cliente B",
            tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,
        )
        self.tipo_a = TipoDocumento.objects.create(empresa=self.empresa_a, codigo="RNC", nombre="RNC")

    def pdf(self, nombre="archivo.pdf", relleno=b"contenido"):
        return SimpleUploadedFile(nombre, b"%PDF-1.4\n" + relleno, content_type="application/pdf")

    def crear(self, empresa=None, cliente=None, usuario=None, **datos):
        return crear_documento_asociado(
            empresa=empresa or self.empresa_a, objeto=cliente or self.cliente_a,
            archivo=datos.pop("archivo", self.pdf()), usuario=usuario or self.user_a,
            titulo=datos.pop("titulo", "Contrato"), tipo_documento=datos.pop("tipo_documento", self.tipo_a),
            **datos,
        )

    def test_usuario_solo_ve_documentos_empresa(self):
        self.crear()
        tipo_b = TipoDocumento.objects.create(empresa=self.empresa_b, codigo="RNC", nombre="RNC")
        self.crear(empresa=self.empresa_b, cliente=self.cliente_b, usuario=self.user_b, tipo_documento=tipo_b, titulo="Secreto B")
        self.client.force_login(self.user_a)
        respuesta = self.client.get(reverse("documentos:lista"))
        self.assertContains(respuesta, "Contrato")
        self.assertNotContains(respuesta, "Secreto B")

    def test_no_descarga_documento_otra_empresa(self):
        tipo_b = TipoDocumento.objects.create(empresa=self.empresa_b, codigo="RNC", nombre="RNC")
        documento = self.crear(empresa=self.empresa_b, cliente=self.cliente_b, usuario=self.user_b, tipo_documento=tipo_b)
        self.client.force_login(self.user_a)
        self.assertEqual(self.client.get(reverse("documentos:descargar", args=[documento.pk])).status_code, 404)

    def test_no_vincula_documento_con_cliente_otra_empresa(self):
        with self.assertRaises(ValidationError):
            self.crear(cliente=self.cliente_b)

    def test_extension_no_autorizada(self):
        with self.assertRaises(ValidationError):
            self.crear(archivo=SimpleUploadedFile("malware.exe", b"MZcontenido"))

    def test_archivo_supera_limite(self):
        with self.assertRaises(ValidationError):
            self.crear(archivo=self.pdf(relleno=b"x" * 200))

    def test_tipo_requiere_vencimiento(self):
        tipo = TipoDocumento.objects.create(
            empresa=self.empresa_a, codigo="LIC", nombre="Licencia", requiere_vencimiento=True
        )
        with self.assertRaises(ValidationError):
            self.crear(tipo_documento=tipo)

    def test_reemplazo_conserva_anterior(self):
        anterior = self.crear()
        nuevo = reemplazar_documento(documento=anterior, archivo=self.pdf("nuevo.pdf"), usuario=self.user_a)
        anterior.refresh_from_db()
        self.assertEqual(anterior.estado, Documento.Estado.REEMPLAZADO)
        self.assertEqual(nuevo.documento_anterior, anterior)
        self.assertEqual(nuevo.version, 2)

    def test_anular_no_elimina_registro_ni_archivo(self):
        documento = self.crear()
        nombre = documento.archivo.name
        anular_documento(documento=documento, usuario=self.user_a)
        documento.refresh_from_db()
        self.assertEqual(documento.estado, Documento.Estado.ANULADO)
        self.assertTrue(documento.archivo.storage.exists(nombre))

    def test_carga_genera_auditoria(self):
        self.crear()
        self.assertTrue(EventoAuditoria.objects.filter(accion=EventoAuditoria.Accion.CARGAR_DOCUMENTO).exists())

    def test_descarga_genera_auditoria(self):
        documento = self.crear()
        self.client.force_login(self.user_a)
        respuesta = self.client.get(reverse("documentos:descargar", args=[documento.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(EventoAuditoria.objects.filter(accion=EventoAuditoria.Accion.DESCARGAR_DOCUMENTO).exists())

    def test_edicion_cliente_genera_evento(self):
        self.client.force_login(self.user_a)
        datos = {
            "codigo": "A1", "tipo_cliente": Cliente.Tipo.CLIENTE_PRIVADO,
            "nombre_comercial": "Cliente actualizado", "razon_social": "",
            "rnc_cedula": "", "telefono": "", "whatsapp": "", "correo": "",
            "direccion_fiscal": "", "provincia": "", "municipio": "", "sector": "",
            "condicion_pago": Cliente.CondicionPago.CONTADO, "dias_credito": 0,
            "limite_credito": "0", "descuento_maximo": "0", "estado": Cliente.Estado.ACTIVO,
        }
        respuesta = self.client.post(reverse("comercial:cliente_editar", args=[self.cliente_a.pk]), datos)
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(EventoAuditoria.objects.filter(accion=EventoAuditoria.Accion.EDITAR).exists())

    def test_cambio_estado_genera_evento(self):
        self.client.force_login(self.user_a)
        self.client.post(reverse("comercial:cliente_cambiar_estado", args=[self.cliente_a.pk]), {"estado": Cliente.Estado.SUSPENDIDO})
        self.assertTrue(EventoAuditoria.objects.filter(accion=EventoAuditoria.Accion.CAMBIAR_ESTADO).exists())

    def test_reemplazar_y_anular_rechazan_get(self):
        documento = self.crear()
        self.client.force_login(self.user_a)
        self.assertEqual(self.client.get(reverse("documentos:reemplazar", args=[documento.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("documentos:anular", args=[documento.pk])).status_code, 405)

    def test_vistas_requieren_autenticacion(self):
        documento = self.crear()
        urls = [
            reverse("documentos:lista"), reverse("documentos:detalle", args=[documento.pk]),
            reverse("documentos:descargar", args=[documento.pk]),
            reverse("documentos:cargar", args=["comercial", "cliente", self.cliente_a.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)

    def test_ficha_filtra_documentos_y_eventos_por_empresa(self):
        self.crear()
        ct = ContentType.objects.get_for_model(self.cliente_a)
        EventoAuditoria.objects.create(
            empresa=self.empresa_b, usuario=self.user_b, modulo="comercial",
            accion=EventoAuditoria.Accion.OTRO, descripcion="Evento ajeno",
            content_type=ct, object_id=self.cliente_a.pk,
        )
        self.client.force_login(self.user_a)
        respuesta = self.client.get(reverse("comercial:cliente_detalle", args=[self.cliente_a.pk]))
        self.assertContains(respuesta, "Contrato")
        self.assertNotContains(respuesta, "Evento ajeno")

    def test_flujo_completo_desde_interfaz_y_layout_movil(self):
        self.client.force_login(self.user_a)
        carga = self.client.post(
            reverse("documentos:cargar", args=["comercial", "cliente", self.cliente_a.pk]),
            {
                "tipo_documento": self.tipo_a.pk, "titulo": "Expediente manual",
                "descripcion": "Prueba funcional", "fecha_documento": date.today().isoformat(),
                "archivo": self.pdf("expediente.pdf"),
            },
        )
        self.assertEqual(carga.status_code, 302)
        documento = Documento.objects.get(titulo="Expediente manual")
        descarga = self.client.get(reverse("documentos:descargar", args=[documento.pk]))
        self.assertEqual(descarga.status_code, 200)
        reemplazo = self.client.post(
            reverse("documentos:reemplazar", args=[documento.pk]),
            {"archivo": self.pdf("expediente-v2.pdf")},
        )
        self.assertEqual(reemplazo.status_code, 302)
        nuevo = Documento.objects.get(documento_anterior=documento)
        anulacion = self.client.post(reverse("documentos:anular", args=[nuevo.pk]))
        self.assertEqual(anulacion.status_code, 302)
        ficha = self.client.get(reverse("comercial:cliente_detalle", args=[self.cliente_a.pk]))
        self.assertContains(ficha, "Expediente manual")
        self.assertContains(ficha, "Se anuló el documento")
        self.assertContains(ficha, 'class="mobile-list"')
