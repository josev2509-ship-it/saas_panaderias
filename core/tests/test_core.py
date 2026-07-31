from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from auditoria.models import EventoAuditoria
from comercial.models import SecuenciaDocumento
from conduces.models import Empresa
from inventario.engine import (
    InventoryEngine, calcular_saldo_desde_movimientos, diagnosticar_producto,
    reconstruir_stock_cacheado,
)
from inventario.models import LoteInventario, MovimientoInventario, ProductoInventario

from core.application.event_bus import EventBus
from core.application.idempotency import begin, complete, fail
from core.application.numbering import obtener_siguiente_numero, vista_previa_numero
from core.application.operation_context import OperationContext
from core.domain.events import DomainEvent
from core.domain.exceptions import (
    BusinessRuleViolation, CrossCompanyViolation, IdempotencyConflict,
)
from core.domain.rules import format_number, free_quantity, net_quantity, positive_decimal
from core.infrastructure.audit_adapter import audit_create
from core.models import ConciliacionInventario, EventoDominio, RegistroIdempotencia


class CoreMotorTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("core", password="x")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="A")
        self.other = Empresa.objects.create(nombre="B")
        self.product = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="P", nombre="Producto",
            tipo="materia_prima", stock_actual=Decimal("10"),
        )
        self.lot = LoteInventario.objects.create(
            empresa=self.empresa, producto=self.product, lote="L",
            fecha_ingreso=timezone.localdate(), cantidad_inicial=10,
            cantidad_disponible=10,
        )

    def context(self, key="key"):
        return OperationContext(
            empresa=self.empresa, usuario=self.user,
            clave_idempotente=key, referencia="REF",
        )

    def test_operation_context_requires_company(self):
        with self.assertRaises(CrossCompanyViolation):
            OperationContext(empresa=None)

    def test_operation_context_rejects_cross_company_user(self):
        other_user = User.objects.create_user("other")
        Empresa.objects.create(usuario=other_user, nombre="Other")
        with self.assertRaises(CrossCompanyViolation):
            OperationContext(empresa=self.empresa, usuario=other_user)

    def test_pure_positive_decimal(self):
        self.assertEqual(positive_decimal("1.25"), Decimal("1.25"))
        with self.assertRaises(BusinessRuleViolation):
            positive_decimal(0)

    def test_pure_inventory_rules(self):
        self.assertEqual(free_quantity(10, 3), 7)
        self.assertEqual(net_quantity(10, 2), 8)
        with self.assertRaises(BusinessRuleViolation):
            net_quantity(2, 3)

    def test_pure_number_format(self):
        self.assertEqual(format_number("PED", 2026, 1), "PED-2026-000001")

    def test_idempotency_completed_is_not_new(self):
        record, created = begin(context=self.context(), operation="test", payload={"a": 1})
        self.assertTrue(created)
        complete(record, "7")
        same, execute = begin(context=self.context(), operation="test", payload={"a": 1})
        self.assertFalse(execute)
        self.assertEqual(same.resultado_referencia, "7")

    def test_idempotency_payload_conflict(self):
        begin(context=self.context(), operation="test", payload={"a": 1})
        with self.assertRaises(IdempotencyConflict):
            begin(context=self.context(), operation="test", payload={"a": 2})

    def test_idempotency_is_scoped_by_company(self):
        begin(context=self.context(), operation="test", payload={})
        other = OperationContext(empresa=self.other, clave_idempotente="key")
        _, created = begin(context=other, operation="test", payload={})
        self.assertTrue(created)

    def test_idempotency_failure_and_retry(self):
        record, _ = begin(context=self.context(), operation="test", payload={})
        fail(record, RuntimeError("safe"))
        retried, execute = begin(
            context=self.context(), operation="test", payload={}, allow_retry=True
        )
        self.assertTrue(execute)
        self.assertEqual(retried.estado, RegistroIdempotencia.Estado.INICIADA)
        self.assertEqual(retried.intentos, 2)

    def test_numbering_is_sequential_and_not_reused(self):
        first = obtener_siguiente_numero(empresa=self.empresa, tipo_documento="PED")
        second = obtener_siguiente_numero(empresa=self.empresa, tipo_documento="PED")
        self.assertEqual(first, "PED-2026-000001")
        self.assertEqual(second, "PED-2026-000002")

    def test_numbering_is_multi_company(self):
        self.assertEqual(
            obtener_siguiente_numero(empresa=self.empresa, tipo_documento="OP"),
            obtener_siguiente_numero(empresa=self.other, tipo_documento="OP"),
        )

    def test_number_preview_does_not_consume(self):
        preview = vista_previa_numero(empresa=self.empresa, tipo_documento="LOT")
        emitted = obtener_siguiente_numero(empresa=self.empresa, tipo_documento="LOT")
        self.assertEqual(preview, emitted)

    def test_numbering_allows_future_prefix(self):
        self.assertEqual(
            obtener_siguiente_numero(empresa=self.empresa, tipo_documento="FV"),
            "FV-2026-000001",
        )

    def test_direct_movement_does_not_change_stock(self):
        MovimientoInventario.objects.create(
            empresa=self.empresa, producto=self.product, tipo="salida", cantidad=3
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actual, 10)

    def test_engine_changes_product_and_lot_atomically(self):
        movement = InventoryEngine.apply_movement(
            context=self.context("move"), producto=self.product, lote=self.lot,
            tipo="consumo_produccion", cantidad=3,
        )
        self.product.refresh_from_db()
        self.lot.refresh_from_db()
        self.assertEqual((self.product.stock_actual, self.lot.cantidad_disponible), (7, 7))
        self.assertEqual((movement.saldo_anterior, movement.saldo_posterior), (10, 7))

    def test_engine_is_idempotent(self):
        first = InventoryEngine.apply_movement(
            context=self.context("same"), producto=self.product, lote=self.lot,
            tipo="consumo_produccion", cantidad=2,
        )
        second = InventoryEngine.apply_movement(
            context=self.context("same"), producto=self.product, lote=self.lot,
            tipo="consumo_produccion", cantidad=2,
        )
        self.product.refresh_from_db()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(self.product.stock_actual, 8)

    def test_engine_conflicting_request_is_rejected(self):
        InventoryEngine.apply_movement(
            context=self.context("conflict"), producto=self.product, lote=self.lot,
            tipo="consumo_produccion", cantidad=1,
        )
        with self.assertRaises(IdempotencyConflict):
            InventoryEngine.apply_movement(
                context=self.context("conflict"), producto=self.product, lote=self.lot,
                tipo="consumo_produccion", cantidad=2,
            )

    def test_engine_failure_rolls_back_and_is_recorded(self):
        with self.assertRaises(Exception):
            InventoryEngine.apply_movement(
                context=self.context("failure"), producto=self.product, lote=self.lot,
                tipo="consumo_produccion", cantidad=50,
            )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actual, 10)
        self.assertEqual(
            RegistroIdempotencia.objects.get(clave="failure").estado,
            RegistroIdempotencia.Estado.FALLIDA,
        )

    def test_engine_rejects_cross_company_product(self):
        other_product = ProductoInventario.objects.create(
            empresa=self.other, codigo="O", nombre="Other", tipo="materia_prima"
        )
        with self.assertRaises(CrossCompanyViolation):
            InventoryEngine.apply_movement(
                context=self.context("cross"), producto=other_product,
                tipo="entrada", cantidad=1,
            )

    def test_engine_creates_uniform_audit(self):
        movement = InventoryEngine.apply_movement(
            context=self.context("audit"), producto=self.product, lote=self.lot,
            tipo="consumo_produccion", cantidad=1,
        )
        self.assertTrue(EventoAuditoria.objects.filter(object_id=movement.pk).exists())

    def test_audit_removes_sensitive_values(self):
        audit_create(
            context=self.context(), module="core", description="Prueba",
            after={"password": "secret", "ok": 1},
        )
        event = EventoAuditoria.objects.get()
        self.assertNotIn("password", event.datos_nuevos)
        self.assertEqual(event.datos_nuevos["ok"], 1)

    def test_event_is_registered_and_processed_after_commit(self):
        bus = EventBus()
        received = []
        bus.subscribe("DomainEvent", received.append)
        with self.captureOnCommitCallbacks(execute=True):
            record = bus.publish(DomainEvent(
                empresa_id=self.empresa.pk, agregado_tipo="test",
                agregado_id="1", clave_idempotente="event-1",
            ))
        record.refresh_from_db()
        self.assertEqual(record.estado, EventoDominio.Estado.PROCESADO)
        self.assertEqual(len(received), 1)

    def test_event_is_idempotent(self):
        bus = EventBus()
        event = DomainEvent(
            empresa_id=self.empresa.pk, agregado_tipo="test",
            agregado_id="1", clave_idempotente="event-same",
        )
        with self.captureOnCommitCallbacks(execute=True):
            first = bus.publish(event)
        with self.captureOnCommitCallbacks(execute=True):
            second = bus.publish(event)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(EventoDominio.objects.count(), 1)

    def test_event_handler_failure_is_recorded(self):
        bus = EventBus()
        bus.subscribe("DomainEvent", lambda payload: (_ for _ in ()).throw(RuntimeError("handler")))
        with self.captureOnCommitCallbacks(execute=True):
            record = bus.publish(DomainEvent(
                empresa_id=self.empresa.pk, agregado_tipo="test",
                agregado_id="1", clave_idempotente="event-error",
            ))
        record.refresh_from_db()
        self.assertEqual(record.estado, EventoDominio.Estado.ERROR)

    def test_calculate_balance_uses_historical_balance(self):
        InventoryEngine.apply_movement(
            context=self.context("balance"), producto=self.product, lote=self.lot,
            tipo="consumo_produccion", cantidad=2,
        )
        self.assertEqual(calcular_saldo_desde_movimientos(self.product), 8)

    def test_diagnosis_detects_difference_without_mutation(self):
        diagnosis = diagnosticar_producto(context=self.context(), producto=self.product)
        self.product.refresh_from_db()
        self.assertEqual(diagnosis.estado, ConciliacionInventario.Estado.DIFERENCIA)
        self.assertEqual(self.product.stock_actual, 10)

    def test_rebuild_requires_permission_and_reason(self):
        with self.assertRaises(PermissionDenied):
            reconstruir_stock_cacheado(
                context=self.context(), producto=self.product, motivo="Correccion"
            )
        permission = Permission.objects.get(codename="rebuild_inventory_balance")
        self.user.user_permissions.add(permission)
        self.user = User.objects.get(pk=self.user.pk)
        with self.assertRaises(ValueError):
            reconstruir_stock_cacheado(
                context=self.context("missing-reason"), producto=self.product, motivo=""
            )

    def test_rebuild_corrects_cache_and_keeps_movements(self):
        movement = InventoryEngine.apply_movement(
            context=self.context("rebuild-move"), producto=self.product, lote=self.lot,
            tipo="consumo_produccion", cantidad=2,
        )
        ProductoInventario.objects.filter(pk=self.product.pk).update(stock_actual=99)
        self.user.user_permissions.add(Permission.objects.get(codename="rebuild_inventory_balance"))
        result = reconstruir_stock_cacheado(
            context=self.context(), producto=self.product, motivo="Corregir inconsistencia"
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_actual, 8)
        self.assertTrue(MovimientoInventario.objects.filter(pk=movement.pk).exists())
        self.assertEqual(result.estado, ConciliacionInventario.Estado.CORREGIDA)
        self.assertTrue(EventoAuditoria.objects.filter(object_id=result.pk).exists())

    def test_technical_views_require_login(self):
        self.assertEqual(self.client.get(reverse("core:motor_dashboard")).status_code, 302)

    def test_critical_views_reject_get(self):
        self.user.user_permissions.add(Permission.objects.get(codename="run_inventory_diagnosis"))
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("core:diagnostico_producto")).status_code, 405)

    def test_technical_view_without_permission_is_forbidden(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("core:eventos")).status_code, 403)

    def test_forms_do_not_expose_company_or_stock(self):
        from core.forms import ReconstruccionSaldoForm
        form = ReconstruccionSaldoForm(empresa=self.empresa)
        self.assertNotIn("empresa", form.fields)
        self.assertNotIn("stock_actual", form.fields)


class IdempotencyConcurrencyTest(TransactionTestCase):
    reset_sequences = True

    def test_unique_constraint_prevents_logical_duplicate(self):
        user = User.objects.create_user("tx")
        empresa = Empresa.objects.create(usuario=user, nombre="TX")
        context = OperationContext(empresa=empresa, usuario=user, clave_idempotente="tx")
        first, _ = begin(context=context, operation="logical", payload={"x": 1})
        with self.assertRaises(IdempotencyConflict):
            begin(context=context, operation="logical", payload={"x": 1})
        self.assertEqual(RegistroIdempotencia.objects.filter(pk=first.pk).count(), 1)
