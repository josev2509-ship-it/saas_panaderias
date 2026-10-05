from datetime import date

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from conduces.models import Empresa, EmpresaSaaS
from conduces.tenant_context import (
    SESSION_SOPORTE_ACTOR,
    SESSION_SOPORTE_INICIADO,
    SESSION_SOPORTE_MOTIVO,
    SESSION_SOPORTE_OPERATIVA,
    SESSION_SOPORTE_SAAS,
)
from rrhh.forms import DescripcionPuestoForm
from rrhh.models import DescripcionPuesto, Puesto


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PuestosYFuncionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_a = User.objects.create_superuser("puestos-a", "a@example.com", "x")
        cls.user_b = User.objects.create_superuser("puestos-b", "b@example.com", "x")
        cls.empresa_a = Empresa.objects.create(
            usuario=cls.user_a, nombre="Empresa A", modulo_nomina=True
        )
        cls.empresa_b = Empresa.objects.create(
            usuario=cls.user_b, nombre="Empresa B", modulo_nomina=True
        )
        cls.puesto_a = Puesto.objects.create(
            empresa=cls.empresa_a, codigo="PA", nombre="Puesto A"
        )
        cls.puesto_b = Puesto.objects.create(
            empresa=cls.empresa_b, codigo="PB", nombre="Puesto B"
        )

    def setUp(self):
        self.client.force_login(self.user_a)

    def datos_funcion(self, puesto=None, **cambios):
        datos = {
            "puesto": (puesto or self.puesto_a).pk,
            "objetivo": "Objetivo",
            "funciones": "Funciones principales",
            "responsabilidades": "Responsabilidades",
            "procedimientos": "",
            "herramientas": "",
            "controles": "",
            "documentos_relacionados": "",
            "version": 1,
            "vigente_desde": date.today(),
        }
        datos.update(cambios)
        return datos

    def test_crear_puesto_lo_asocia_al_tenant_efectivo(self):
        respuesta = self.client.post(reverse("rrhh:puesto_crear"), {
            "codigo": "NUEVO", "nombre": "Nuevo puesto", "descripcion": "Descripción",
            "empresa": self.empresa_b.pk,
        })
        self.assertEqual(respuesta.status_code, 302)
        puesto = Puesto.objects.get(codigo="NUEVO")
        self.assertEqual(puesto.empresa, self.empresa_a)
        self.assertTrue(puesto.activo)

    def test_listado_de_puestos_esta_aislado(self):
        respuesta = self.client.get(reverse("rrhh:puestos"))
        self.assertContains(respuesta, "Puesto A")
        self.assertNotContains(respuesta, "Puesto B")

    def test_no_puede_editar_puesto_de_otra_empresa(self):
        respuesta = self.client.post(reverse("rrhh:puesto_editar", args=[self.puesto_b.pk]), {
            "codigo": "ATAQUE", "nombre": "Ataque", "descripcion": "",
        })
        self.assertEqual(respuesta.status_code, 404)
        self.puesto_b.refresh_from_db()
        self.assertEqual(self.puesto_b.codigo, "PB")

    def test_pk_cross_tenant_no_puede_cambiar_estado(self):
        respuesta = self.client.post(reverse("rrhh:puesto_estado", args=[self.puesto_b.pk]))
        self.assertEqual(respuesta.status_code, 404)
        self.puesto_b.refresh_from_db()
        self.assertTrue(self.puesto_b.activo)

    def test_codigo_puede_repetirse_entre_empresas(self):
        Puesto.objects.create(empresa=self.empresa_a, codigo="COMPARTIDO", nombre="A")
        puesto_b = Puesto.objects.create(empresa=self.empresa_b, codigo="COMPARTIDO", nombre="B")
        self.assertEqual(puesto_b.codigo, "COMPARTIDO")

    def test_codigo_no_puede_duplicarse_en_misma_empresa(self):
        respuesta = self.client.post(reverse("rrhh:puesto_crear"), {
            "codigo": "PA", "nombre": "Duplicado", "descripcion": "",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ya existe un puesto con este código")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Puesto.objects.create(empresa=self.empresa_a, codigo="PA", nombre="Duplicado")

    def test_puesto_inactivo_no_aparece_en_nueva_descripcion(self):
        self.puesto_a.activo = False
        self.puesto_a.save(update_fields=["activo"])
        form = DescripcionPuestoForm(empresa=self.empresa_a)
        self.assertNotIn(self.puesto_a, form.fields["puesto"].queryset)
        respuesta = self.client.get(reverse("rrhh:funcion_crear"))
        self.assertContains(respuesta, "No existen puestos activos registrados")
        self.assertContains(respuesta, reverse("rrhh:puesto_crear"))

    def test_descripcion_existente_conserva_puesto_inactivado(self):
        descripcion = DescripcionPuesto.objects.create(
            empresa=self.empresa_a, puesto=self.puesto_a, objetivo="Histórico",
            funciones="Históricas", version=1, vigente_desde=date.today(),
        )
        self.puesto_a.activo = False
        self.puesto_a.save(update_fields=["activo"])
        form = DescripcionPuestoForm(instance=descripcion, empresa=self.empresa_a)
        self.assertIn(self.puesto_a, form.fields["puesto"].queryset)
        self.assertEqual(descripcion.puesto, self.puesto_a)
        respuesta = self.client.post(
            reverse("rrhh:funcion_editar", args=[descripcion.pk]),
            self.datos_funcion(self.puesto_a, objetivo="Histórico actualizado"),
        )
        self.assertEqual(respuesta.status_code, 302)
        descripcion.refresh_from_db()
        self.assertEqual(descripcion.puesto, self.puesto_a)

    def test_no_cambia_descripcion_a_otro_puesto_inactivo(self):
        descripcion = DescripcionPuesto.objects.create(
            empresa=self.empresa_a, puesto=self.puesto_a, objetivo="Original",
            funciones="Funciones", version=1, vigente_desde=date.today(),
        )
        otro_inactivo = Puesto.objects.create(
            empresa=self.empresa_a, codigo="INACTIVO", nombre="Otro inactivo", activo=False,
        )
        respuesta = self.client.post(
            reverse("rrhh:funcion_editar", args=[descripcion.pk]),
            self.datos_funcion(otro_inactivo, objetivo="No aplicar"),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no está entre las disponibles")
        descripcion.refresh_from_db()
        self.assertEqual(descripcion.puesto, self.puesto_a)

    def test_relacion_historica_impide_eliminacion_fisica_del_puesto(self):
        DescripcionPuesto.objects.create(
            empresa=self.empresa_a, puesto=self.puesto_a, objetivo="Histórico",
            funciones="Funciones", version=1, vigente_desde=date.today(),
        )
        with self.assertRaises(ProtectedError):
            self.puesto_a.delete()

    def test_no_crea_descripcion_con_puesto_de_otra_empresa(self):
        respuesta = self.client.post(
            reverse("rrhh:funcion_crear"), self.datos_funcion(self.puesto_b)
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no está entre las disponibles")
        self.assertFalse(DescripcionPuesto.objects.exists())

    def test_editar_descripcion_de_funciones(self):
        descripcion = DescripcionPuesto.objects.create(
            empresa=self.empresa_a, puesto=self.puesto_a, objetivo="Anterior",
            funciones="Funciones", version=1, vigente_desde=date.today(),
        )
        respuesta = self.client.post(
            reverse("rrhh:funcion_editar", args=[descripcion.pk]),
            self.datos_funcion(objetivo="Actualizado"),
        )
        self.assertEqual(respuesta.status_code, 302)
        descripcion.refresh_from_db()
        self.assertEqual(descripcion.objetivo, "Actualizado")

    def test_activar_e_inactivar_descripcion_usa_activa(self):
        descripcion = DescripcionPuesto.objects.create(
            empresa=self.empresa_a, puesto=self.puesto_a, objetivo="Objetivo",
            funciones="Funciones", version=1, vigente_desde=date.today(),
        )
        url = reverse("rrhh:funcion_estado", args=[descripcion.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        descripcion.refresh_from_db()
        self.assertFalse(descripcion.activa)
        self.client.post(url)
        descripcion.refresh_from_db()
        self.assertTrue(descripcion.activa)

    def test_soporte_con_contexto_respeta_tenant(self):
        soporte = User.objects.create_superuser("soporte-puestos", "soporte@example.com", "x")
        saas = EmpresaSaaS.objects.create(
            nombre="Empresa A", correo="saas-a@example.com", rnc="",
            requiere_pago=False, empresa_operativa=self.empresa_a,
        )
        self.client.force_login(soporte)
        session = self.client.session
        session[SESSION_SOPORTE_ACTOR] = soporte.pk
        session[SESSION_SOPORTE_SAAS] = saas.pk
        session[SESSION_SOPORTE_OPERATIVA] = self.empresa_a.pk
        session[SESSION_SOPORTE_MOTIVO] = "Prueba"
        session[SESSION_SOPORTE_INICIADO] = timezone.now().isoformat()
        session.save()
        self.assertEqual(self.client.get(reverse("rrhh:puestos")).status_code, 200)
        self.assertEqual(
            self.client.post(reverse("rrhh:puesto_editar", args=[self.puesto_b.pk]), {
                "codigo": "X", "nombre": "X", "descripcion": "",
            }).status_code,
            404,
        )
