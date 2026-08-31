from datetime import date
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from auditoria.models import EventoAuditoria
from conduces.models import CentroEducativo, Conduce, Empresa, EmpresaSaaS, PerfilUsuario
from conduces.utils import dibujar_conduce


class ConduceEliminacionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operador-conduces",
            password="test-password",
        )
        self.empresa = Empresa.objects.create(
            usuario=self.user,
            nombre="Empresa Operativa",
            rnc="101010101",
            direccion="Santo Domingo",
            telefono="809-555-0101",
            ciudad="Santo Domingo",
            correo="operaciones@example.com",
            modulo_conduces=True,
        )
        self.centro = CentroEducativo.objects.create(
            empresa=self.empresa,
            codigo="CE-001",
            nombre="Centro Uno",
            director="Directora Uno",
            telefono="809-555-0202",
            direccion="Distrito Nacional",
            provincia="Santo Domingo",
            regional_distrito="10-01",
            matricula=100,
        )
        self.conduce = Conduce.objects.create(
            empresa=self.empresa,
            fecha=date(2026, 8, 31),
            centro=self.centro,
            producto="Raciones",
            cantidad=100,
        )
        self.delete_permission = Permission.objects.get(codename="delete_conduce")
        self.client.force_login(self.user)

    def grant_delete(self, user=None):
        (user or self.user).user_permissions.add(self.delete_permission)

    def make_company_admin(self, user=None):
        user = user or self.user
        empresa_saas = EmpresaSaaS.objects.create(
            nombre=f"Cuenta SaaS {user.username}",
            rnc=f"RNC-{user.pk}",
            correo=f"{user.username}@example.com",
        )
        return PerfilUsuario.objects.create(
            user=user,
            empresa=empresa_saas,
            rol="admin_empresa",
            correo_validado=True,
            activo=True,
        )

    def test_administrador_empresa_ve_eliminar_sin_permiso_django_manual(self):
        self.make_company_admin()

        response = self.client.get(reverse("buscar_conduces"))

        self.assertFalse(self.user.has_perm("conduces.delete_conduce"))
        self.assertContains(response, "Eliminar")
        self.assertContains(response, f'eliminar-conduce-{self.conduce.pk}')

    def test_administrador_empresa_puede_realizar_baja_logica(self):
        self.make_company_admin()

        response = self.client.post(reverse("eliminar_conduce", args=[self.conduce.pk]))

        self.assertRedirects(response, reverse("buscar_conduces"))
        self.assertFalse(Conduce.objects.filter(pk=self.conduce.pk).exists())
        self.assertEqual(Conduce.all_objects.get(pk=self.conduce.pk).eliminado_por, self.user)

    def test_usuario_sin_permiso_no_ve_eliminar(self):
        response = self.client.get(reverse("buscar_conduces"))

        self.assertNotContains(response, f'eliminar-conduce-{self.conduce.pk}')

    def test_eliminacion_exitosa_es_logica_y_auditada(self):
        self.grant_delete()

        response = self.client.post(
            reverse("eliminar_conduce", args=[self.conduce.pk]),
            follow=True,
        )

        self.assertRedirects(response, reverse("buscar_conduces"))
        self.assertFalse(Conduce.objects.filter(pk=self.conduce.pk).exists())
        eliminado = Conduce.all_objects.get(pk=self.conduce.pk)
        self.assertIsNotNone(eliminado.eliminado_en)
        self.assertEqual(eliminado.eliminado_por, self.user)
        self.assertIn(
            f"Conduce {self.conduce.numero} eliminado correctamente.",
            [str(message) for message in get_messages(response.wsgi_request)],
        )
        evento = EventoAuditoria.objects.get(object_id=self.conduce.pk, modulo="conduces")
        self.assertEqual(evento.usuario, self.user)
        self.assertEqual(evento.accion, EventoAuditoria.Accion.CAMBIAR_ESTADO)

    def test_get_no_elimina(self):
        self.grant_delete()

        response = self.client.get(reverse("eliminar_conduce", args=[self.conduce.pk]))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Conduce.objects.filter(pk=self.conduce.pk).exists())

    def test_post_requiere_csrf(self):
        self.grant_delete()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = csrf_client.post(reverse("eliminar_conduce", args=[self.conduce.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Conduce.objects.filter(pk=self.conduce.pk).exists())

    def test_aislamiento_por_empresa(self):
        self.make_company_admin()
        otro_usuario = get_user_model().objects.create_user(username="otro-operador")
        otra_empresa = Empresa.objects.create(
            usuario=otro_usuario,
            nombre="Empresa Ajena",
            modulo_conduces=True,
        )
        self.make_company_admin(otro_usuario)
        self.client.force_login(otro_usuario)

        response = self.client.post(reverse("eliminar_conduce", args=[self.conduce.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Conduce.objects.filter(pk=self.conduce.pk).exists())
        self.assertNotEqual(otra_empresa.pk, self.empresa.pk)

    def test_administrador_existente_resuelve_permiso_por_rol_sin_sincronizacion(self):
        perfil = self.make_company_admin()

        self.assertFalse(self.user.has_perm("conduces.delete_conduce"))
        response = self.client.post(reverse("eliminar_conduce", args=[self.conduce.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(perfil.activo)
        self.assertFalse(Conduce.objects.filter(pk=self.conduce.pk).exists())

    def test_usuario_sin_permiso_no_elimina(self):
        response = self.client.post(reverse("eliminar_conduce", args=[self.conduce.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Conduce.objects.filter(pk=self.conduce.pk).exists())

    def test_eliminado_no_aparece_en_listado(self):
        self.grant_delete()
        self.client.post(reverse("eliminar_conduce", args=[self.conduce.pk]))

        response = self.client.get(reverse("buscar_conduces"))

        self.assertEqual(list(response.context["conduces"]), [])
        self.assertNotContains(response, reverse("vista_conduce", args=[self.conduce.pk]))

    def test_numeracion_eliminada_no_se_reutiliza(self):
        self.grant_delete()
        numero_eliminado = int(self.conduce.numero)
        self.client.post(reverse("eliminar_conduce", args=[self.conduce.pk]))

        siguiente = Conduce.objects.create(
            empresa=self.empresa,
            fecha=date(2026, 9, 1),
            centro=self.centro,
            producto="Raciones",
            cantidad=100,
        )

        self.assertEqual(int(siguiente.numero), numero_eliminado + 1)
        self.assertTrue(Conduce.all_objects.filter(pk=self.conduce.pk).exists())

    def test_boton_usa_formulario_post_con_csrf(self):
        self.grant_delete()

        response = self.client.get(reverse("buscar_conduces"))

        self.assertContains(response, 'method="post"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertNotContains(
            response,
            f'href="{reverse("eliminar_conduce", args=[self.conduce.pk])}"',
        )

    def test_observaciones_nulas_no_renderizan_none_en_edicion_o_pdf(self):
        response = self.client.get(reverse("editar_conduce", args=[self.conduce.pk]))
        self.assertNotContains(response, ">None</textarea>")

        canvas = Mock()
        dibujar_conduce(canvas, self.conduce)
        textos = [str(arg) for call in canvas.drawString.call_args_list for arg in call.args]
        self.assertNotIn("None", textos)
