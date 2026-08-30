import shutil
import tempfile
from datetime import date
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from conduces.models import Empresa
from rrhh.models import CentroTrabajo, Departamento, DocumentoEmpleado, Empleado, Puesto


class ProtectedMediaTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = Path(tempfile.mkdtemp(prefix="sastre-media-tests-"))
        cls.settings_override = override_settings(
            MEDIA_ROOT=cls.media_root,
            DEBUG=False,
            ROOT_URLCONF="panaderia_saas.test_urls_media",
        )
        cls.settings_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.settings_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("media-owner", password="test")
        self.other_user = User.objects.create_user("media-other", password="test")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Empresa Media")
        self.other_empresa = Empresa.objects.create(usuario=self.other_user, nombre="Otra Empresa")
        department = Departamento.objects.create(empresa=self.empresa, codigo="D", nombre="Departamento")
        position = Puesto.objects.create(empresa=self.empresa, codigo="P", nombre="Puesto")
        workplace = CentroTrabajo.objects.create(empresa=self.empresa, codigo="L", nombre="Lugar")
        employee = Empleado.objects.create(
            empresa=self.empresa, codigo="EMP-1", nombres="Ada", apellidos="Prueba",
            identificacion="TEST-1", puesto=position, departamento=department,
            centro=workplace, fecha_ingreso=date.today(), salario=1000,
        )
        self.document = DocumentoEmpleado.objects.create(
            empresa=self.empresa, empleado=employee, tipo="CV",
            archivo=SimpleUploadedFile("cv.pdf", b"%PDF-1.4\nmedia test"),
        )
        self.url = f"/media/{self.document.archivo.name}"

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_tenant_user_needs_document_permission(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.user.user_permissions.add(Permission.objects.get(codename="view_documentoempleado"))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        response.close()

    def test_other_tenant_cannot_access_document(self):
        self.other_user.user_permissions.add(Permission.objects.get(codename="view_documentoempleado"))
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_path_traversal_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.get("/media/%2e%2e/manage.py")
        self.assertEqual(response.status_code, 404)
