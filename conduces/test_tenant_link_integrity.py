import importlib
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from .models import Empresa, EmpresaSaaS, PerfilUsuario, Suscripcion
from .tenant_context import empresa_operativa_desde_saas, empresa_operativa_usuario


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TenantLinkIntegrityTests(TestCase):
    def ejecutar_backfill(self):
        migration = importlib.import_module(
            "conduces.migrations.0047_empresasaas_empresa_operativa"
        )
        migration.vincular_empresas_historicas(apps, None)

    def test_relacion_explicita_tiene_prioridad(self):
        user = User.objects.create_user("owner")
        operativa = Empresa.objects.create(usuario=user, nombre="Operativa")
        saas = EmpresaSaaS.objects.create(nombre="SaaS", correo="saas@example.com", rnc="", empresa_operativa=operativa)
        PerfilUsuario.objects.create(user=user, empresa=saas, activo=True)
        self.assertEqual(empresa_operativa_desde_saas(saas), operativa)
        self.assertEqual(empresa_operativa_usuario(user), operativa)

    def test_contradiccion_no_se_resuelve_arbitrariamente(self):
        owner = User.objects.create_user("owner-a")
        member = User.objects.create_user("member-a")
        vinculada = Empresa.objects.create(usuario=owner, nombre="Vinculada")
        directa = Empresa.objects.create(usuario=member, nombre="Directa")
        saas = EmpresaSaaS.objects.create(nombre="SaaS", correo="a@example.com", rnc="", empresa_operativa=vinculada)
        PerfilUsuario.objects.create(user=member, empresa=saas, activo=True)
        self.assertIsNone(empresa_operativa_usuario(member))

    def test_backfill_por_perfil_y_repara_placeholder(self):
        user = User.objects.create_user("legacy")
        operativa = Empresa.objects.create(usuario=user, nombre="Panadería Demo SRL", rnc="123", correo="demo@example.com")
        saas = EmpresaSaaS.objects.create(nombre="Mi empresa", correo="legacy@example.com", rnc="")
        PerfilUsuario.objects.create(user=user, empresa=saas, activo=True)
        self.ejecutar_backfill()
        saas.refresh_from_db()
        self.assertEqual(saas.empresa_operativa, operativa)
        self.assertEqual(saas.nombre, operativa.nombre)
        self.assertEqual(saas.rnc, "123")

    def test_backfill_no_inventa_vinculo_ambiguo(self):
        saas = EmpresaSaaS.objects.create(nombre="Ambigua", correo="ambigua@example.com", rnc="DUP")
        for indice in range(2):
            user = User.objects.create_user(f"amb-{indice}")
            Empresa.objects.create(usuario=user, nombre=f"Empresa {indice}", rnc="DUP")
            PerfilUsuario.objects.create(user=user, empresa=saas, activo=True)
        self.ejecutar_backfill()
        saas.refresh_from_db()
        self.assertIsNone(saas.empresa_operativa)

    def test_backfill_por_rnc_unico(self):
        user = User.objects.create_user("rnc-owner")
        operativa = Empresa.objects.create(usuario=user, nombre="Por RNC", rnc="101999999")
        saas = EmpresaSaaS.objects.create(
            nombre="SaaS RNC", correo="otro@example.com", rnc="101999999"
        )
        self.ejecutar_backfill()
        saas.refresh_from_db()
        self.assertEqual(saas.empresa_operativa, operativa)

    def test_backfill_por_correo_normalizado_unico(self):
        user = User.objects.create_user("correo-owner")
        operativa = Empresa.objects.create(
            usuario=user, nombre="Por correo", correo="tenant@example.com"
        )
        saas = EmpresaSaaS.objects.create(
            nombre="SaaS correo", correo="  TENANT@EXAMPLE.COM  ", rnc=""
        )
        self.ejecutar_backfill()
        saas.refresh_from_db()
        self.assertEqual(saas.empresa_operativa, operativa)

    def test_backfill_sin_candidato_no_crea_empresa(self):
        saas = EmpresaSaaS.objects.create(
            nombre="Sin operativa", correo="nadie@example.com", rnc="SINCOINCIDENCIA"
        )
        empresas_antes = Empresa.objects.count()
        self.ejecutar_backfill()
        saas.refresh_from_db()
        self.assertIsNone(saas.empresa_operativa)
        self.assertEqual(Empresa.objects.count(), empresas_antes)

    @patch("conduces.views.enviar_codigo_correo")
    def test_registro_crea_vinculo_explicito(self, enviar):
        respuesta = self.client.post("/registro/", {
            "nombre": "Admin Demo", "correo": "registro@example.com",
            "password": "Segura123!", "confirmar_password": "Segura123!",
        })
        self.assertEqual(respuesta.status_code, 302)
        perfil = PerfilUsuario.objects.select_related("empresa__empresa_operativa").get(
            user__username="registro@example.com"
        )
        self.assertEqual(perfil.empresa.empresa_operativa.usuario, perfil.user)
        self.assertTrue(Suscripcion.objects.filter(empresa=perfil.empresa).exists())

    def test_mi_empresa_sincroniza_identidad_saas(self):
        user = User.objects.create_user("identidad", password="x")
        operativa = Empresa.objects.create(usuario=user, nombre="Mi empresa", correo="old@example.com")
        saas = EmpresaSaaS.objects.create(
            nombre="Mi empresa", correo="old@example.com", rnc="", empresa_operativa=operativa
        )
        PerfilUsuario.objects.create(user=user, empresa=saas, rol="admin_empresa", activo=True)
        self.client.force_login(user)
        respuesta = self.client.post("/mi-empresa/", {
            "nombre": "Panadería Demo SRL", "rnc": "101", "correo": "new@example.com",
            "numero_inicial_conduce": "0001",
        })
        self.assertEqual(respuesta.status_code, 302)
        operativa.refresh_from_db(); saas.refresh_from_db()
        self.assertEqual(operativa.nombre, "Panadería Demo SRL")
        self.assertEqual(saas.nombre, operativa.nombre)
        self.assertEqual(saas.rnc, "101")
        self.assertEqual(saas.correo, "new@example.com")
