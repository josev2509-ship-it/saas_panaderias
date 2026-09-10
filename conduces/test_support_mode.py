from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .models import (
    CentroEducativo,
    Empresa,
    EmpresaSaaS,
    PerfilUsuario,
    Suscripcion,
)
from .tenant_context import (
    SESSION_SOPORTE_SAAS,
    SESSION_SOPORTE_OPERATIVA,
    SESSION_SOPORTE_MOTIVO,
    SESSION_SOPORTE_INICIADO,
    SESSION_SOPORTE_ACTOR,
)

from django.utils import timezone


User = get_user_model()


class ModoSoporteIsolationTests(TestCase):

    def setUp(self):
        self.soporte = User.objects.create_user(
            username="soporte_test",
            password="Soporte123!",
            is_staff=True,
            is_active=True,
        )

        grupo, _ = Group.objects.get_or_create(
            name="Soporte SASTRE"
        )

        self.soporte.groups.add(
            grupo
        )

        self.owner_a = User.objects.create_user(
            username="owner_a",
            password="Test123!",
            is_active=True,
        )

        self.owner_b = User.objects.create_user(
            username="owner_b",
            password="Test123!",
            is_active=True,
        )

        self.saas_a = EmpresaSaaS.objects.create(
            nombre="Empresa A",
            correo="a@example.com",
            activa=True,
            requiere_pago=False,
        )

        self.saas_b = EmpresaSaaS.objects.create(
            nombre="Empresa B",
            correo="b@example.com",
            activa=True,
            requiere_pago=False,
        )

        PerfilUsuario.objects.create(
            user=self.owner_a,
            empresa=self.saas_a,
            rol="admin_empresa",
            activo=True,
            correo_validado=True,
        )

        PerfilUsuario.objects.create(
            user=self.owner_b,
            empresa=self.saas_b,
            rol="admin_empresa",
            activo=True,
            correo_validado=True,
        )

        self.empresa_a = Empresa.objects.create(
            usuario=self.owner_a,
            nombre="Empresa A",
            correo="a@example.com",
            modulo_centros=True,
            activa=True,
        )

        self.empresa_b = Empresa.objects.create(
            usuario=self.owner_b,
            nombre="Empresa B",
            correo="b@example.com",
            modulo_centros=True,
            activa=True,
        )

        self.centro_a = CentroEducativo.objects.create(
            empresa=self.empresa_a,
            codigo="A001",
            nombre="Centro A",
        )

        self.centro_b = CentroEducativo.objects.create(
            empresa=self.empresa_b,
            codigo="B001",
            nombre="Centro B",
        )

        self.client.force_login(
            self.soporte
        )

    def activar_soporte_a(self):
        session = self.client.session

        session[
            SESSION_SOPORTE_SAAS
        ] = self.saas_a.pk

        session[
            SESSION_SOPORTE_OPERATIVA
        ] = self.empresa_a.pk

        session[
            SESSION_SOPORTE_MOTIVO
        ] = "Prueba aislamiento"

        session[
            SESSION_SOPORTE_INICIADO
        ] = timezone.now().isoformat()

        session[
            SESSION_SOPORTE_ACTOR
        ] = self.soporte.pk

        session.save()

    def entrar_soporte(self, empresa):
        return self.client.post(
            reverse("soporte_entrar_empresa", args=[empresa.pk]),
            {"motivo": "Diagnostico autorizado"},
        )

    def assert_sin_contexto_soporte(self):
        session = self.client.session
        for key in (
            SESSION_SOPORTE_SAAS,
            SESSION_SOPORTE_OPERATIVA,
            SESSION_SOPORTE_MOTIVO,
            SESSION_SOPORTE_INICIADO,
            SESSION_SOPORTE_ACTOR,
        ):
            self.assertNotIn(key, session)

    def test_empresa_activa_sin_pago_permite_entrada_soporte(self):
        Suscripcion.objects.create(
            empresa=self.saas_a,
            estado="vencida",
            fecha_inicio=timezone.localdate() - timedelta(days=60),
            fecha_fin=timezone.localdate() - timedelta(days=1),
            en_prueba=False,
        )
        response = self.entrar_soporte(self.saas_a)
        self.assertRedirects(response, reverse("inicio"))
        session = self.client.session
        self.assertEqual(session[SESSION_SOPORTE_SAAS], self.saas_a.pk)
        self.assertEqual(session[SESSION_SOPORTE_MOTIVO], "Diagnostico autorizado")
        self.assertEqual(session[SESSION_SOPORTE_ACTOR], self.soporte.pk)

    def test_empresa_suspendida_no_permite_entrada_y_limpia_contexto(self):
        self.activar_soporte_a()
        self.saas_b.suspendida_manualmente = True
        self.saas_b.save(update_fields=["suspendida_manualmente"])
        response = self.entrar_soporte(self.saas_b)
        self.assertRedirects(
            response,
            reverse("soporte_empresa_detalle", args=[self.saas_b.pk]),
        )
        self.assert_sin_contexto_soporte()

    def test_empresa_con_pago_y_suscripcion_vencida_no_permite_entrada(self):
        self.saas_a.requiere_pago = True
        self.saas_a.save(update_fields=["requiere_pago"])
        Suscripcion.objects.create(
            empresa=self.saas_a,
            estado="vencida",
            fecha_inicio=timezone.localdate() - timedelta(days=60),
            fecha_fin=timezone.localdate() - timedelta(days=1),
            en_prueba=False,
        )
        response = self.entrar_soporte(self.saas_a)
        self.assertRedirects(
            response,
            reverse("soporte_empresa_detalle", args=[self.saas_a.pk]),
        )
        self.assert_sin_contexto_soporte()

    def test_empresa_inactiva_no_permite_entrada(self):
        self.saas_a.activa = False
        self.saas_a.save(update_fields=["activa"])
        response = self.entrar_soporte(self.saas_a)
        self.assertRedirects(
            response,
            reverse("soporte_empresa_detalle", args=[self.saas_a.pk]),
        )
        self.assert_sin_contexto_soporte()

    def test_cuenta_estado_usa_empresa_efectiva_de_soporte(self):
        self.entrar_soporte(self.saas_a)
        response = self.client.get(reverse("cuenta_estado"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["empresa_saas"], self.saas_a)
        self.assertTrue(response.context["tiene_acceso"])
        self.assertTrue(response.context["modo_soporte"])

    def test_cuenta_bloqueada_normal_no_ofrece_bucle_a_inicio(self):
        self.client.force_login(self.owner_a)
        self.saas_a.activa = False
        self.saas_a.save(update_fields=["activa"])
        response = self.client.get(reverse("cuenta_estado"))
        self.assertNotContains(
            response,
            f'href="{reverse("inicio")}"',
        )
        self.assertContains(response, reverse("logout_usuario"))

    def test_salir_soporte_elimina_todas_las_claves_y_regresa_centro(self):
        self.activar_soporte_a()
        response = self.client.post(reverse("soporte_salir_empresa"))
        self.assertRedirects(
            response,
            reverse("soporte_empresa_detalle", args=[self.saas_a.pk]),
        )
        self.assert_sin_contexto_soporte()

    def test_soporte_empresa_a_no_puede_abrir_centro_b(self):
        self.activar_soporte_a()

        response = self.client.get(
            reverse(
                "editar_centro",
                args=[self.centro_b.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_soporte_empresa_a_si_puede_abrir_centro_a(self):
        self.activar_soporte_a()

        response = self.client.get(
            reverse(
                "editar_centro",
                args=[self.centro_a.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

    def test_actor_distinto_invalida_contexto(self):
        self.activar_soporte_a()

        session = self.client.session
        session[
            SESSION_SOPORTE_ACTOR
        ] = 999999
        session.save()

        response = self.client.get(
            reverse(
                "editar_centro",
                args=[self.centro_a.pk],
            )
        )

        self.assertIn(
            response.status_code,
            (302, 403),
        )
