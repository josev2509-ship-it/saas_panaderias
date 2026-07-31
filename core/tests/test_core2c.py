from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.template import Context, Template

from conduces.models import Empresa
from inventario.engine import (
    calcular_saldo_desde_movimientos, diagnosticar_producto,
    reconstruir_stock_cacheado,
)
from inventario.models import LoteInventario, MovimientoInventario, ProductoInventario

from core.application.event_bus import EventBus
from core.application.idempotency import recover_stale
from core.application.operation_context import OperationContext
from core.application.request_idempotency import resolve_idempotency_context
from core.domain.events import DomainEvent
from core.models import ConciliacionInventario, EventoDominio, RegistroIdempotencia


class Core2CClosingTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("core2c", password="x")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Core 2C")
        self.product = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="C2C", nombre="Producto",
            stock_actual=Decimal("10"),
        )
        self.factory = RequestFactory()

    def request(self, **headers):
        request = self.factory.post("/inventario/movimiento/", **headers)
        request.user = self.user
        return request

    def context(self, key="core2c"):
        return OperationContext(
            empresa=self.empresa, usuario=self.user,
            clave_idempotente=key, referencia="CORE2C",
        )

    def test_equal_requests_without_header_receive_distinct_keys(self):
        first = resolve_idempotency_context(
            self.request(), operation="inventory.entry"
        )
        second = resolve_idempotency_context(
            self.request(), operation="inventory.entry"
        )
        self.assertNotEqual(first["clave_idempotente"], second["clave_idempotente"])
        self.assertEqual(first["metadata"]["key_source"], "request_id")

    def test_explicit_key_is_stable_and_records_origin(self):
        first = resolve_idempotency_context(
            self.request(HTTP_IDEMPOTENCY_KEY=" Retry 1 "),
            operation="inventory.entry",
        )
        second = resolve_idempotency_context(
            self.request(HTTP_IDEMPOTENCY_KEY=" Retry 1 "),
            operation="inventory.entry",
        )
        self.assertEqual(first["clave_idempotente"], second["clave_idempotente"])
        self.assertEqual(first["metadata"]["key_source"], "header")

    @override_settings(CORE_IDEMPOTENCY_STALE_SECONDS=60)
    def test_stale_started_operation_can_be_recovered(self):
        record = RegistroIdempotencia.objects.create(
            empresa=self.empresa, clave="stale", operacion="test",
            hash_solicitud="x",
        )
        RegistroIdempotencia.objects.filter(pk=record.pk).update(
            fecha_inicio=timezone.now() - timedelta(minutes=5)
        )
        recovered = recover_stale(empresa=self.empresa)
        record.refresh_from_db()
        self.assertEqual([item.pk for item in recovered], [record.pk])
        self.assertEqual(record.estado, RegistroIdempotencia.Estado.FALLIDA)

    def test_executable_event_without_consumer_is_not_processed(self):
        bus = EventBus()
        with self.captureOnCommitCallbacks(execute=True):
            record = bus.publish(DomainEvent(
                empresa_id=self.empresa.pk, agregado_tipo="test",
                agregado_id="1", clave_idempotente="exec",
                requiere_consumidor=True,
            ))
        record.refresh_from_db()
        self.assertEqual(record.estado, EventoDominio.Estado.ERROR)

    @override_settings(CORE_EVENT_PROCESSING_TIMEOUT_SECONDS=60)
    def test_stuck_event_can_be_recovered(self):
        record = EventoDominio.objects.create(
            empresa=self.empresa, tipo_evento="Test", agregado_tipo="test",
            agregado_id="1", clave_idempotente="stuck",
            estado=EventoDominio.Estado.PROCESANDO,
            fecha_ultimo_intento=timezone.now() - timedelta(minutes=5),
        )
        EventBus().recover_stuck(empresa=self.empresa)
        record.refresh_from_db()
        self.assertEqual(record.estado, EventoDominio.Estado.ERROR)

    def test_balance_ignores_corrupt_posterior_cache(self):
        MovimientoInventario.objects.create(
            empresa=self.empresa, producto=self.product, tipo="entrada",
            naturaleza=MovimientoInventario.Naturaleza.ENTRADA,
            cantidad=2, saldo_anterior=10, saldo_posterior=999,
            aplicado_por_servicio=True,
        )
        self.assertEqual(calcular_saldo_desde_movimientos(self.product), 12)

    def test_rebuild_with_inconsistent_lots_requires_intervention(self):
        LoteInventario.objects.create(
            empresa=self.empresa, producto=self.product, lote="L-C2C",
            fecha_ingreso=timezone.localdate(), cantidad_inicial=3,
            cantidad_disponible=3,
        )
        self.user.user_permissions.add(
            Permission.objects.get(codename="rebuild_inventory_balance")
        )
        result = reconstruir_stock_cacheado(
            context=self.context("rebuild-c2c"), producto=self.product,
            motivo="Prueba de inconsistencia",
        )
        self.assertEqual(
            result.estado, ConciliacionInventario.Estado.REQUIERE_INTERVENCION
        )

    def test_roles_command_is_idempotent(self):
        call_command("configurar_roles_core", verbosity=0)
        call_command("configurar_roles_core", verbosity=0)
        self.assertEqual(Group.objects.filter(name="Supervisor tecnico").count(), 1)

    def test_authorized_list_has_real_detail_link(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_eventodominio")
        )
        event = EventoDominio.objects.create(
            empresa=self.empresa, tipo_evento="Trace", agregado_tipo="test",
            agregado_id="1", clave_idempotente="ui",
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:eventos"))
        self.assertContains(response, reverse("core:evento_detalle", args=[event.pk]))

    def test_design_system_requires_permission_and_renders_components(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:design_system"))
        self.assertEqual(response.status_code, 403)
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_transaction_engine")
        )
        response = self.client.get(reverse("core:design_system"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enterprise Design System")
        self.assertContains(response, "ds-modal")
        self.assertContains(response, "ds-responsive-table")

    def test_base_menu_respects_technical_permission(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("inicio"))
        self.assertNotContains(response, reverse("core:design_system"))
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_transaction_engine")
        )
        response = self.client.get(reverse("inicio"))
        self.assertContains(response, reverse("core:design_system"))
        self.assertContains(response, "ds-menu-toggle")

    def test_unknown_status_has_safe_neutral_tone(self):
        rendered = Template(
            "{% load design_system %}{{ value|status_tone }}"
        ).render(Context({"value": "NUEVO_ESTADO_FUTURO"}))
        self.assertEqual(rendered, "neutral")
