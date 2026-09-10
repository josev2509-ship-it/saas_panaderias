from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from conduces.models import (
    Empresa,
    EmpresaSaaS,
    PerfilUsuario,
    Plan,
    Suscripcion,
)

from conduces.subscription_service import (
    modulo_habilitado,
    suscripcion_permite_acceso,
)


class SubscriptionAccessTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="cliente",
            email="cliente@example.com",
            password="clave123",
        )

        self.empresa = Empresa.objects.create(
            usuario=self.user,
            nombre="Empresa Operativa",
            activa=True,
            modulo_conduces=False,
            modulo_centros=False,
            modulo_menu=False,
            modulo_facturacion=False,
            modulo_reportes=False,
            modulo_inabie=False,
            modulo_inventario=False,
        )

        self.saas = EmpresaSaaS.objects.create(
            nombre="Empresa SaaS",
            rnc="",
            correo="cliente@example.com",
            activa=True,
            requiere_pago=True,
        )

        PerfilUsuario.objects.create(
            user=self.user,
            empresa=self.saas,
            rol="admin_empresa",
            correo_validado=True,
            activo=True,
        )

        self.plan = Plan.objects.create(
            nombre="Plan Test",
            codigo="PLAN_TEST",
            precio=Decimal("1500.00"),
            modulo_conduces=True,
            modulo_inabie=True,
        )

    def crear_suscripcion(self, **kwargs):
        hoy = timezone.localdate()

        datos = {
            "empresa": self.saas,
            "plan": self.plan,
            "estado": "prueba",
            "fecha_inicio": hoy,
            "fecha_fin": hoy + timedelta(days=15),
            "en_prueba": True,
        }

        datos.update(kwargs)

        return Suscripcion.objects.create(**datos)

    def test_trial_permite_acceso(self):
        self.crear_suscripcion()

        self.assertTrue(
            suscripcion_permite_acceso(self.user)
        )

    def test_trial_es_full_access(self):
        self.crear_suscripcion()

        self.assertTrue(
            modulo_habilitado(
                self.user,
                "modulo_inventario",
            )
        )

    def test_trial_vencido_bloquea(self):
        hoy = timezone.localdate()

        self.crear_suscripcion(
            estado="vencida",
            en_prueba=False,
            fecha_fin=hoy - timedelta(days=1),
        )

        self.assertFalse(
            suscripcion_permite_acceso(self.user)
        )

    def test_suscripcion_activa_vigente(self):
        hoy = timezone.localdate()

        self.crear_suscripcion(
            estado="activa",
            en_prueba=False,
            periodo_actual_desde=hoy,
            periodo_actual_hasta=hoy + timedelta(days=30),
        )

        self.assertTrue(
            suscripcion_permite_acceso(self.user)
        )

    def test_modulo_fuera_plan_bloqueado(self):
        hoy = timezone.localdate()

        self.crear_suscripcion(
            estado="activa",
            en_prueba=False,
            periodo_actual_hasta=hoy + timedelta(days=30),
        )

        self.assertFalse(
            modulo_habilitado(
                self.user,
                "modulo_inventario",
            )
        )

    def test_empresa_sin_pago_permite(self):
        self.saas.requiere_pago = False
        self.saas.save(
            update_fields=["requiere_pago"]
        )

        self.empresa.modulo_inventario = True
        self.empresa.save(
            update_fields=["modulo_inventario"]
        )

        self.assertTrue(
            suscripcion_permite_acceso(self.user)
        )

        self.assertTrue(
            modulo_habilitado(
                self.user,
                "modulo_inventario",
            )
        )

    def test_suspension_manual_bloquea(self):
        self.saas.requiere_pago = False
        self.saas.suspendida_manualmente = True

        self.saas.save(
            update_fields=[
                "requiere_pago",
                "suspendida_manualmente",
            ]
        )

        self.assertFalse(
            suscripcion_permite_acceso(self.user)
        )

    def test_pago_fallido_con_gracia(self):
        hoy = timezone.localdate()

        self.crear_suscripcion(
            estado="pago_fallido",
            en_prueba=False,
            gracia_hasta=hoy + timedelta(days=3),
        )

        self.assertTrue(
            suscripcion_permite_acceso(self.user)
        )

    def test_pago_fallido_sin_gracia(self):
        hoy = timezone.localdate()

        self.crear_suscripcion(
            estado="pago_fallido",
            en_prueba=False,
            gracia_hasta=hoy - timedelta(days=1),
        )

        self.assertFalse(
            suscripcion_permite_acceso(self.user)
        )
