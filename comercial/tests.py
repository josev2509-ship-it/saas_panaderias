from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from conduces.models import Empresa
from .models import Cliente


class ComercialTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user("empresa-a", password="clave-segura")
        self.user_b = User.objects.create_user("empresa-b", password="clave-segura")
        self.empresa_a = Empresa.objects.create(usuario=self.user_a, nombre="Empresa A")
        self.empresa_b = Empresa.objects.create(usuario=self.user_b, nombre="Empresa B")
        self.cliente_a = self.crear_cliente(self.empresa_a, "A-001", "Cliente A")
        self.cliente_b = self.crear_cliente(self.empresa_b, "B-001", "Cliente B")

    def crear_cliente(self, empresa, codigo, nombre, **kwargs):
        valores = {
            "empresa": empresa, "codigo": codigo, "nombre_comercial": nombre,
            "tipo_cliente": Cliente.Tipo.CLIENTE_PRIVADO,
            "condicion_pago": Cliente.CondicionPago.CONTADO,
        }
        valores.update(kwargs)
        return Cliente.objects.create(**valores)

    def test_usuario_solo_ve_clientes_de_su_empresa(self):
        self.client.force_login(self.user_a)
        respuesta = self.client.get(reverse("comercial:clientes_lista"))
        self.assertContains(respuesta, "Cliente A")
        self.assertNotContains(respuesta, "Cliente B")

    def test_no_abre_detalle_de_otra_empresa(self):
        self.client.force_login(self.user_a)
        respuesta = self.client.get(reverse("comercial:cliente_detalle", args=[self.cliente_b.pk]))
        self.assertEqual(respuesta.status_code, 404)

    def test_no_edita_cliente_de_otra_empresa(self):
        self.client.force_login(self.user_a)
        respuesta = self.client.get(reverse("comercial:cliente_editar", args=[self.cliente_b.pk]))
        self.assertEqual(respuesta.status_code, 404)

    def test_codigo_es_unico_por_empresa(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.crear_cliente(self.empresa_a, "A-001", "Duplicado")
        self.crear_cliente(self.empresa_b, "A-001", "Permitido en otra empresa")

    def test_limite_negativo_es_invalido(self):
        cliente = self.crear_cliente(self.empresa_a, "A-002", "Inválido")
        cliente.limite_credito = Decimal("-1")
        with self.assertRaises(ValidationError):
            cliente.full_clean()

    def test_descuento_mayor_cien_es_invalido(self):
        cliente = self.crear_cliente(self.empresa_a, "A-003", "Inválido")
        cliente.descuento_maximo = Decimal("100.01")
        with self.assertRaises(ValidationError):
            cliente.full_clean()

    def test_contado_no_admite_dias_credito(self):
        cliente = self.crear_cliente(self.empresa_a, "A-004", "Inválido")
        cliente.dias_credito = 15
        with self.assertRaises(ValidationError):
            cliente.full_clean()

    def test_cambio_estado_no_funciona_por_get(self):
        self.client.force_login(self.user_a)
        respuesta = self.client.get(reverse("comercial:cliente_cambiar_estado", args=[self.cliente_a.pk]))
        self.assertEqual(respuesta.status_code, 405)
        self.cliente_a.refresh_from_db()
        self.assertEqual(self.cliente_a.estado, Cliente.Estado.ACTIVO)

    def test_vistas_requieren_autenticacion(self):
        urls = [
            reverse("comercial:dashboard"), reverse("comercial:clientes_lista"),
            reverse("comercial:cliente_crear"),
            reverse("comercial:cliente_detalle", args=[self.cliente_a.pk]),
            reverse("comercial:cliente_editar", args=[self.cliente_a.pk]),
            reverse("comercial:direccion_crear", args=[self.cliente_a.pk]),
            reverse("comercial:contacto_crear", args=[self.cliente_a.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)

    def test_navegacion_basica_autenticada(self):
        self.client.force_login(self.user_a)
        urls = [
            reverse("comercial:dashboard"),
            reverse("comercial:clientes_lista"),
            reverse("comercial:cliente_crear"),
            reverse("comercial:cliente_detalle", args=[self.cliente_a.pk]),
            reverse("comercial:cliente_editar", args=[self.cliente_a.pk]),
            reverse("comercial:direccion_crear", args=[self.cliente_a.pk]),
            reverse("comercial:contacto_crear", args=[self.cliente_a.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
