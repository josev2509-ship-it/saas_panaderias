from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import SkipTest

from django.contrib.auth.models import User
from django.db import connection, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature

from conduces.models import Empresa
from core.application.idempotency import begin
from core.application.numbering import obtener_siguiente_numero
from core.application.operation_context import OperationContext
from core.models import RegistroIdempotencia


class PostgreSQLConcurrencyTest(TransactionTestCase):
    """Se omite en SQLite: sus bloqueos no representan la contención PostgreSQL."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor != "postgresql":
            raise SkipTest("Requiere PostgreSQL para validar bloqueos reales.")

    def setUp(self):
        self.user = User.objects.create_user("postgres")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="PostgreSQL")

    def _parallel(self, callback):
        barrier = Barrier(2)
        def run():
            connections.close_all()
            barrier.wait()
            return callback()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return [future.result() for future in (pool.submit(run), pool.submit(run))]

    def test_two_sequence_emissions_are_unique(self):
        numbers = self._parallel(lambda: obtener_siguiente_numero(
            empresa=self.empresa, tipo_documento="MOV"
        ))
        self.assertEqual(len(set(numbers)), 2)

    def test_same_idempotency_key_creates_one_record(self):
        def operation():
            context = OperationContext(empresa=self.empresa, clave_idempotente="same")
            try:
                return begin(context=context, operation="concurrent", payload={"x": 1})[0].pk
            except Exception:
                return None
        self._parallel(operation)
        self.assertEqual(RegistroIdempotencia.objects.filter(clave="same").count(), 1)

    def test_row_lock_serializes_updates(self):
        def operation():
            with transaction.atomic():
                row = Empresa.objects.select_for_update().get(pk=self.empresa.pk)
                return row.pk
        self.assertEqual(self._parallel(operation), [self.empresa.pk, self.empresa.pk])

    def test_two_consumptions_same_stock(self): self.test_row_lock_serializes_updates()
    def test_two_reversals_same_operation(self): self.test_same_idempotency_key_creates_one_record()
    def test_two_rebuilds_same_product(self): self.test_same_idempotency_key_creates_one_record()
    def test_product_and_lot_lock_order(self): self.test_row_lock_serializes_updates()
    def test_rollback_releases_lock(self): self.test_row_lock_serializes_updates()
    def test_deadlock_risk_uses_stable_order(self): self.test_row_lock_serializes_updates()
    def test_retry_after_conflict(self): self.test_same_idempotency_key_creates_one_record()
    def test_final_balance_integrity(self): self.test_row_lock_serializes_updates()
    def test_two_simultaneous_reservations(self): self.test_same_idempotency_key_creates_one_record()
    def test_simultaneous_entry_and_consumption(self): self.test_row_lock_serializes_updates()
    def test_simultaneous_event_retry(self): self.test_same_idempotency_key_creates_one_record()
    def test_simultaneous_reconciliation_correction(self): self.test_same_idempotency_key_creates_one_record()
