from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from conduces.models import Empresa
from auditoria.models import EventoAuditoria
from core.models import EventoDominio


class O2CHttpSecurityTest(TestCase):
    endpoints = (
        "fin_factura_emitir", "fin_factura_contabilizar", "fin_nota_credito",
        "fin_nota_debito", "fin_factura_anular", "fin_cobro_aplicar",
        "fin_cobro_integrar", "fin_cobro_revertir", "fin_factoring_desembolsar",
        "fin_factoring_aprobar", "fin_conciliacion_aplicar", "fin_conciliacion_revertir",
        "fin_reintentar",
    )

    def url(self, name): return reverse("comercial:" + name, kwargs={"pk": 999999})

    def test_01_acciones_criticas_rechazan_get(self):
        user=User.objects.create_user("http-method");self.client.force_login(user)
        for name in self.endpoints:self.assertEqual(self.client.get(self.url(name)).status_code,405,name)

    def test_02_acciones_criticas_exigen_autenticacion(self):
        for name in self.endpoints:self.assertEqual(self.client.post(self.url(name)).status_code,302,name)

    def test_03_post_sin_csrf_es_rechazado(self):
        user=User.objects.create_superuser("csrf-user","csrf@example.invalid","x");client=Client(enforce_csrf_checks=True);client.force_login(user)
        for name in self.endpoints:self.assertEqual(client.post(self.url(name)).status_code,403,name)
        self.assertFalse(EventoDominio.objects.exists());self.assertFalse(EventoAuditoria.objects.exists())

    def test_04_token_de_otra_sesion_es_rechazado(self):
        user=User.objects.create_superuser("csrf-other","other@example.invalid","x");source=Client(enforce_csrf_checks=True);source.force_login(user);source.cookies["csrftoken"]="a"*32
        target=Client(enforce_csrf_checks=True);target.force_login(user);target.cookies["csrftoken"]="b"*32
        self.assertEqual(target.post(self.url("fin_factura_emitir"),HTTP_X_CSRFTOKEN="a"*32).status_code,403)

    def test_05_usuario_sin_permiso_con_csrf_valido(self):
        user=User.objects.create_user("csrf-no-perm");client=Client(enforce_csrf_checks=True);client.force_login(user);client.cookies["csrftoken"]="a"*32
        self.assertEqual(client.post(self.url("fin_factura_emitir"),HTTP_X_CSRFTOKEN="a"*32).status_code,403)

    def test_06_exportacion_post_con_csrf_valido(self):
        user=User.objects.create_superuser("csrf-valid","valid@example.invalid","x");Empresa.objects.create(usuario=user,nombre="CSRF valid");client=Client(enforce_csrf_checks=True);client.force_login(user);client.cookies["csrftoken"]="a"*32
        url=reverse("comercial:fin_exportar",kwargs={"tipo":"facturas","formato":"csv"});response=client.post(url,HTTP_X_CSRFTOKEN="a"*32)
        self.assertEqual(response.status_code,200);self.assertEqual(EventoAuditoria.objects.count(),1);self.assertEqual(EventoDominio.objects.count(),1)

    def test_07_exportacion_get_rechazado(self):
        user=User.objects.create_superuser("export-get","get@example.invalid","x");Empresa.objects.create(usuario=user,nombre="Export GET");self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("comercial:fin_exportar",kwargs={"tipo":"facturas","formato":"csv"})).status_code,405)

    def test_08_sesion_expirada_no_tiene_efectos(self):
        user=User.objects.create_superuser("expired","expired@example.invalid","x");Empresa.objects.create(usuario=user,nombre="Expired");client=Client(enforce_csrf_checks=True);client.force_login(user);client.cookies["csrftoken"]="a"*32;client.logout()
        response=client.post(reverse("comercial:fin_exportar",kwargs={"tipo":"facturas","formato":"csv"}),HTTP_X_CSRFTOKEN="a"*32)
        self.assertEqual(response.status_code,403);self.assertFalse(EventoAuditoria.objects.exists());self.assertFalse(EventoDominio.objects.exists())
