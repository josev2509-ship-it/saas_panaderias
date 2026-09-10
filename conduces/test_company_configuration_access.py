from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sessions.middleware import SessionMiddleware
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .models import Empresa, EmpresaSaaS, PerfilUsuario


User = get_user_model()


class CompanyConfigurationAccessTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.normal = User.objects.create_user(username="cliente_config", password="Test123!")
        self.support = User.objects.create_user(
            username="soporte_config", password="Test123!", is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username="super_config", email="super@example.com", password="Test123!"
        )
        group = Group.objects.create(name="Soporte SASTRE")
        self.support.groups.add(group)
        self.saas = EmpresaSaaS.objects.create(
            nombre="Cliente Config",
            correo="cliente@example.com",
            activa=True,
            requiere_pago=False,
        )
        PerfilUsuario.objects.create(
            user=self.normal,
            empresa=self.saas,
            rol="admin_empresa",
            activo=True,
            correo_validado=True,
        )
        self.empresa = Empresa.objects.create(
            usuario=self.normal,
            nombre="Cliente Config",
            correo="cliente@example.com",
        )

    def render_shell(self, user):
        request = self.factory.get("/")
        SessionMiddleware(lambda current_request: None).process_request(request)
        request.session.save()
        request.user = user
        return render_to_string(
            "base.html", {"empresa": self.empresa}, request=request
        )

    def test_superusuario_ve_configuracion_global_de_empresas(self):
        html = self.render_shell(self.superuser)
        self.assertIn("Configuración de empresas", html)
        self.assertIn(reverse("soporte_empresas"), html)

    def test_soporte_sastre_ve_configuracion_global_de_empresas(self):
        html = self.render_shell(self.support)
        self.assertIn("Configuración de empresas", html)
        self.assertIn(reverse("soporte_empresas"), html)

    def test_cliente_normal_no_ve_configuracion_global_de_empresas(self):
        self.assertNotIn("Configuración de empresas", self.render_shell(self.normal))

    def test_cliente_normal_no_puede_abrir_administracion_global(self):
        self.client.force_login(self.normal)
        response = self.client.get(reverse("soporte_empresas"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("soporte_login")))

    def test_superusuario_puede_abrir_administracion_global(self):
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(reverse("soporte_empresas")).status_code, 200)

    def test_soporte_sastre_puede_abrir_administracion_global(self):
        self.client.force_login(self.support)
        self.assertEqual(self.client.get(reverse("soporte_empresas")).status_code, 200)

    def test_cliente_accede_solo_a_configuracion_de_su_empresa(self):
        self.client.force_login(self.normal)
        response = self.client.get(reverse("mi_empresa"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["empresa"], self.empresa)
        self.assertNotContains(response, "Configuración de empresas")
