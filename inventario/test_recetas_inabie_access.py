from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from conduces.models import Empresa, EmpresaSaaS, PerfilUsuario, Plan, Suscripcion
from conduces.tenant_context import (
    SESSION_SOPORTE_ACTOR,
    SESSION_SOPORTE_INICIADO,
    SESSION_SOPORTE_MOTIVO,
    SESSION_SOPORTE_OPERATIVA,
    SESSION_SOPORTE_SAAS,
)

from .models import ProductoInventario, RecetaProduccion


class RecetasInabieAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("cliente_inabie", password="x")
        self.empresa = Empresa.objects.create(
            usuario=self.user,
            nombre="Tenant A",
            activa=True,
        )
        self.saas = EmpresaSaaS.objects.create(
            nombre="Tenant A",
            correo="tenant-a@example.com",
            activa=True,
            requiere_pago=True,
        )
        PerfilUsuario.objects.create(
            user=self.user,
            empresa=self.saas,
            rol="admin_empresa",
            activo=True,
            correo_validado=True,
        )
        self.plan = Plan.objects.create(
            nombre="INABIE",
            codigo="INABIE_TEST",
            precio=Decimal("1500.00"),
            modulo_inabie=True,
        )
        hoy = timezone.localdate()
        self.suscripcion = Suscripcion.objects.create(
            empresa=self.saas,
            plan=self.plan,
            estado="activa",
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=30),
            periodo_actual_hasta=hoy + timedelta(days=30),
            en_prueba=False,
        )
        self.producto = ProductoInventario.objects.create(
            empresa=self.empresa,
            codigo="PT-A",
            nombre="Producto A",
            tipo="producto_terminado",
            unidad_medida="unidad",
            activo=True,
        )
        self.receta = RecetaProduccion.objects.create(
            empresa=self.empresa,
            codigo="REC-A",
            nombre="Receta A",
            producto_terminado=self.producto,
            rendimiento_base=1,
            unidad_rendimiento="unidad",
            activa=True,
            fecha_vigencia_desde=hoy,
        )
        self.url = reverse("inventario:recetas_lista")
        self.crear_url = reverse("inventario:receta_crear")

    def test_cliente_inabie_sin_permiso_inventario_puede_abrir_recetas(self):
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.has_perm("inventario.view_recetaproduccion"))
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REC-A")

    def test_empresa_sin_modulo_inabie_es_bloqueada(self):
        self.plan.modulo_inabie = False
        self.plan.save(update_fields=["modulo_inabie"])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_empresa_operativa_inactiva_es_bloqueada(self):
        self.empresa.activa = False
        self.empresa.save(update_fields=["activa"])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_suscripcion_vencida_es_bloqueada(self):
        ayer = timezone.localdate() - timedelta(days=1)
        self.suscripcion.estado = "vencida"
        self.suscripcion.fecha_fin = ayer
        self.suscripcion.periodo_actual_hasta = ayer
        self.suscripcion.save(
            update_fields=["estado", "fecha_fin", "periodo_actual_hasta"]
        )
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_listado_no_expone_recetas_de_otro_tenant(self):
        otro = User.objects.create_user("cliente_otro", password="x")
        empresa_b = Empresa.objects.create(usuario=otro, nombre="Tenant B")
        producto_b = ProductoInventario.objects.create(
            empresa=empresa_b,
            codigo="PT-B",
            nombre="Producto B",
            tipo="producto_terminado",
            unidad_medida="unidad",
            activo=True,
        )
        RecetaProduccion.objects.create(
            empresa=empresa_b,
            codigo="REC-B",
            nombre="Receta B",
            producto_terminado=producto_b,
            rendimiento_base=1,
            unidad_rendimiento="unidad",
            fecha_vigencia_desde=timezone.localdate(),
        )
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, "REC-A")
        self.assertNotContains(response, "REC-B")

    def test_soporte_autorizado_puede_abrir_recetas_del_tenant(self):
        soporte = User.objects.create_user("soporte_recetas", password="x", is_staff=True)
        grupo, _ = Group.objects.get_or_create(name="Soporte SASTRE")
        soporte.groups.add(grupo)
        self.client.force_login(soporte)
        session = self.client.session
        session[SESSION_SOPORTE_SAAS] = self.saas.pk
        session[SESSION_SOPORTE_OPERATIVA] = self.empresa.pk
        session[SESSION_SOPORTE_MOTIVO] = "Prueba recetas"
        session[SESSION_SOPORTE_INICIADO] = timezone.now().isoformat()
        session[SESSION_SOPORTE_ACTOR] = soporte.pk
        session.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REC-A")

    def test_anonimo_es_redirigido_al_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_admin_empresa_inabie_puede_abrir_nueva_receta_sin_permiso_directo(self):
        self.assertFalse(self.user.has_perm("inventario.add_recetaproduccion"))
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.crear_url).status_code, 200)

    def test_nueva_receta_exige_modulo_inabie(self):
        self.plan.modulo_inabie = False
        self.plan.save(update_fields=["modulo_inabie"])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.crear_url).status_code, 403)

    def test_nueva_receta_exige_suscripcion_vigente(self):
        ayer = timezone.localdate() - timedelta(days=1)
        self.suscripcion.estado = "vencida"
        self.suscripcion.fecha_fin = ayer
        self.suscripcion.periodo_actual_hasta = ayer
        self.suscripcion.save(
            update_fields=["estado", "fecha_fin", "periodo_actual_hasta"]
        )
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.crear_url).status_code, 403)

    def test_operador_no_admin_necesita_permiso_add_recetaproduccion(self):
        perfil = PerfilUsuario.objects.get(user=self.user)
        perfil.rol = "operaciones"
        perfil.save(update_fields=["rol"])
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.crear_url).status_code, 403)

        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="inventario",
            codename="add_recetaproduccion",
        ))
        self.assertEqual(self.client.get(self.crear_url).status_code, 200)

    def test_soporte_sastre_no_puede_crear_sin_permiso_explicito(self):
        soporte = User.objects.create_user("soporte_crear_receta", password="x", is_staff=True)
        grupo, _ = Group.objects.get_or_create(name="Soporte SASTRE")
        soporte.groups.add(grupo)
        self.client.force_login(soporte)
        session = self.client.session
        session[SESSION_SOPORTE_SAAS] = self.saas.pk
        session[SESSION_SOPORTE_OPERATIVA] = self.empresa.pk
        session[SESSION_SOPORTE_MOTIVO] = "Validar creación de receta"
        session[SESSION_SOPORTE_INICIADO] = timezone.now().isoformat()
        session[SESSION_SOPORTE_ACTOR] = soporte.pk
        session.save()
        self.assertEqual(self.client.get(self.crear_url).status_code, 403)
