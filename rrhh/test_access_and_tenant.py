from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from conduces.models import Empresa, EmpresaSaaS, PerfilUsuario
from conduces.tenant_context import (
    SESSION_SOPORTE_ACTOR, SESSION_SOPORTE_INICIADO, SESSION_SOPORTE_MOTIVO,
    SESSION_SOPORTE_OPERATIVA, SESSION_SOPORTE_SAAS,
)
from rrhh.models import Departamento


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class GestionHumanaAccessTests(TestCase):
    def crear_tenant(self, sufijo="a", *, modulo=True, rol="admin_empresa", vincular=True):
        user = User.objects.create_user(f"user-{sufijo}", password="x")
        empresa = Empresa.objects.create(
            usuario=user, nombre=f"Empresa {sufijo}", correo=f"{sufijo}@example.com",
            activa=True, modulo_nomina=modulo,
        )
        saas = EmpresaSaaS.objects.create(
            nombre=empresa.nombre, correo=f"saas-{sufijo}@example.com",
            rnc="", activa=True, requiere_pago=False,
            empresa_operativa=empresa if vincular else None,
        )
        PerfilUsuario.objects.create(user=user, empresa=saas, rol=rol, activo=True)
        return user, empresa, saas

    def test_admin_empresa_sin_grupo_accede_rrhh_nomina_y_crea_departamento(self):
        user, empresa, _ = self.crear_tenant()
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("nomina:dashboard")).status_code, 200)
        respuesta = self.client.post(reverse("rrhh:recurso_crear", args=["departamentos"]), {
            "codigo": "ADM", "nombre": "Administración", "descripcion": "", "activo": "on",
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(Departamento.objects.get(codigo="ADM").empresa, empresa)
        self.assertFalse(user.groups.exists())

    def test_modulo_deshabilitado_deniega_incluso_admin(self):
        user, _, _ = self.crear_tenant(modulo=False)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("nomina:dashboard")).status_code, 403)

    def test_usuario_normal_con_empresa_activa_accede_a_su_tenant(self):
        user, empresa, _ = self.crear_tenant("normal")
        self.client.force_login(user)
        respuesta = self.client.get(reverse("rrhh:dashboard"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["empresa"], empresa)

    def test_usuario_con_empresa_inactiva_es_detenido(self):
        user, empresa, _ = self.crear_tenant("inactiva")
        empresa.activa = False
        empresa.save(update_fields=["activa"])
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code, 403)

    def test_usuario_granular_necesita_permiso_especifico(self):
        user, _, _ = self.crear_tenant(rol="operaciones")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code, 403)
        user.user_permissions.add(Permission.objects.get(codename="view_empleado"))
        self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code, 200)
        self.assertEqual(
            self.client.post(reverse("rrhh:recurso_crear", args=["departamentos"]), {
                "codigo": "X", "nombre": "No permitido", "activo": "on",
            }).status_code,
            403,
        )

    def test_empresa_no_resoluble_no_llega_a_integrity_error(self):
        user = User.objects.create_user("huerfano", password="x")
        saas = EmpresaSaaS.objects.create(nombre="Sin operativa", correo="sin@example.com", rnc="", requiere_pago=False)
        PerfilUsuario.objects.create(user=user, empresa=saas, rol="admin_empresa", activo=True)
        self.client.force_login(user)
        respuesta = self.client.post(reverse("rrhh:recurso_crear", args=["departamentos"]), {
            "codigo": "X", "nombre": "No crear", "activo": "on",
        })
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(Departamento.objects.exists())

    def test_listado_y_edicion_aislados_por_empresa(self):
        user_a, empresa_a, _ = self.crear_tenant("a")
        _, empresa_b, _ = self.crear_tenant("b")
        dep_a = Departamento.objects.create(empresa=empresa_a, codigo="A", nombre="Solo A")
        dep_b = Departamento.objects.create(empresa=empresa_b, codigo="B", nombre="Solo B")
        self.client.force_login(user_a)
        respuesta = self.client.get(reverse("rrhh:recurso_lista", args=["departamentos"]))
        self.assertContains(respuesta, dep_a.nombre)
        self.assertNotContains(respuesta, dep_b.nombre)
        respuesta = self.client.post(reverse("rrhh:recurso_estado", args=["departamentos", dep_b.pk]), {"estado": "ACTIVO"})
        self.assertEqual(respuesta.status_code, 404)

    def test_tenant_form_rechaza_empresa_none(self):
        from rrhh.forms import DepartamentoForm
        with self.assertRaises(ValueError):
            DepartamentoForm()

    def test_soporte_requiere_contexto_y_escribe_solo_en_tenant_activo(self):
        soporte = User.objects.create_user("soporte", password="x")
        soporte.groups.add(Group.objects.create(name="Soporte SASTRE"))
        _, empresa_a, saas_a = self.crear_tenant("soporte-a")
        _, empresa_b, saas_b = self.crear_tenant("soporte-b")
        self.client.force_login(soporte)
        self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code, 403)
        session = self.client.session
        session[SESSION_SOPORTE_ACTOR] = soporte.pk
        session[SESSION_SOPORTE_SAAS] = saas_a.pk
        session[SESSION_SOPORTE_OPERATIVA] = empresa_a.pk
        session[SESSION_SOPORTE_MOTIVO] = "Prueba controlada"
        session[SESSION_SOPORTE_INICIADO] = timezone.now().isoformat()
        session.save()
        self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code, 200)
        self.client.post(reverse("rrhh:recurso_crear", args=["departamentos"]), {
            "codigo": "SOP", "nombre": "Soporte A", "activo": "on",
        })
        self.assertTrue(Departamento.objects.filter(empresa=empresa_a, codigo="SOP").exists())
        self.assertFalse(Departamento.objects.filter(empresa=empresa_b, codigo="SOP").exists())

    def test_superusuario_con_contexto_seleccionado_opera_solo_ese_tenant(self):
        soporte = User.objects.create_superuser("root-soporte", "root@example.com", "x")
        _, empresa_a, saas_a = self.crear_tenant("root-a")
        _, empresa_b, _ = self.crear_tenant("root-b")
        dep_b = Departamento.objects.create(empresa=empresa_b, codigo="B", nombre="Empresa B")
        self.client.force_login(soporte)
        session = self.client.session
        session[SESSION_SOPORTE_ACTOR] = soporte.pk
        session[SESSION_SOPORTE_SAAS] = saas_a.pk
        session[SESSION_SOPORTE_OPERATIVA] = empresa_a.pk
        session[SESSION_SOPORTE_MOTIVO] = "Diagnóstico autorizado"
        session[SESSION_SOPORTE_INICIADO] = timezone.now().isoformat()
        session.save()
        self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code, 200)
        respuesta = self.client.post(
            reverse("rrhh:recurso_estado", args=["departamentos", dep_b.pk]),
            {"estado": "ACTIVO"},
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_superusuario_con_empresa_propia_no_es_forzado_a_modo_soporte(self):
        user, empresa, saas = self.crear_tenant("root-propio")
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(user)
        self.assertFalse(self.client.session.get(SESSION_SOPORTE_OPERATIVA))
        self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code, 200)
        self.assertEqual(saas.empresa_operativa, empresa)

    def test_miembro_soporte_con_tenant_propio_no_recibe_privilegios_de_soporte(self):
        user, empresa, _ = self.crear_tenant("soporte-propio")
        user.groups.add(Group.objects.create(name="Soporte SASTRE"))
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("rrhh:dashboard")).status_code, 200)
        respuesta = self.client.post(reverse("rrhh:recurso_crear", args=["departamentos"]), {
            "codigo": "PROPIO", "nombre": "Tenant propio", "activo": "on",
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Departamento.objects.filter(empresa=empresa, codigo="PROPIO").exists())
