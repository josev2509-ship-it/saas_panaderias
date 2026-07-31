from datetime import date
from pathlib import Path

from django.contrib import admin
from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from comercial.models import SecuenciaDocumento
from conduces.models import Empresa
from inventario.admin import MovimientoInventarioAdmin
from inventario.models import MovimientoInventario

from core.admin import RegistroIdempotenciaAdmin
from core.application.event_bus import EventBus
from core.application.numbering import obtener_siguiente_numero, vista_previa_numero
from core.application.operation_context import OperationContext
from core.domain.events import DomainEvent
from core.domain.exceptions import (
    DomainError, IdempotencyConflict, InactiveSequenceError, UnsafePayloadError,
)
from core.domain.rules import (
    idempotency_hash, non_negative_decimal, normalize_idempotency_key,
    validate_document_length, validate_safe_payload,
)
from core.models import EventoDominio, RegistroIdempotencia


class CoreHardeningTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("hard", password="x")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Empresa")

    def test_operation_context_normalizes_key_and_works_without_request(self):
        context = OperationContext(
            empresa=self.empresa, usuario=self.user,
            clave_idempotente="  OPERACION  1 ",
        )
        self.assertEqual(context.clave_idempotente, "operacion-1")
        self.assertIsNone(context.ip)
        self.assertTrue(context.identificador_solicitud)

    def test_operation_context_rejects_sensitive_or_unserializable_metadata(self):
        with self.assertRaises(UnsafePayloadError):
            OperationContext(empresa=self.empresa, metadata={"token": "secret"})
        with self.assertRaises(UnsafePayloadError):
            OperationContext(empresa=self.empresa, metadata={"object": self.empresa})

    def test_domain_exception_is_safe_and_serializable(self):
        error = DomainError("Mensaje seguro", code="safe", metadata={"id": 1})
        self.assertEqual(error.as_dict(), {
            "code": "safe", "message": "Mensaje seguro", "metadata": {"id": 1}
        })

    def test_pure_hardening_rules(self):
        self.assertEqual(non_negative_decimal(0), 0)
        self.assertEqual(normalize_idempotency_key(" A  B "), "a-b")
        self.assertEqual(len(idempotency_hash({"b": 2, "a": 1})), 64)
        self.assertEqual(validate_document_length(8), 8)
        with self.assertRaises(UnsafePayloadError):
            validate_safe_payload({"password": "x"})

    def test_sequence_supports_current_and_future_types(self):
        for code in ("PED", "PLA", "OP", "LOT", "RES", "MOV", "FV", "CON", "OC", "NC", "REC"):
            self.assertEqual(
                obtener_siguiente_numero(
                    empresa=self.empresa, tipo_documento=code, fecha=date(2026, 1, 1)
                ),
                f"{code}-2026-000001",
            )

    def test_sequence_length_and_annual_restart(self):
        self.assertEqual(
            obtener_siguiente_numero(
                empresa=self.empresa, tipo_documento="PED",
                fecha=date(2026, 1, 1), longitud=4,
            ),
            "PED-2026-0001",
        )
        self.assertEqual(
            obtener_siguiente_numero(
                empresa=self.empresa, tipo_documento="PED",
                fecha=date(2027, 1, 1), longitud=4,
            ),
            "PED-2027-0001",
        )

    def test_inactive_sequence_is_blocked(self):
        SecuenciaDocumento.objects.create(
            empresa=self.empresa, tipo="LOT", periodo=2026,
            ultimo_numero=3, prefijo="LOT", activo=False,
        )
        with self.assertRaises(InactiveSequenceError):
            obtener_siguiente_numero(
                empresa=self.empresa, tipo_documento="LOT", fecha=date(2026, 1, 1)
            )

    def test_preview_does_not_update_sequence(self):
        sequence = SecuenciaDocumento.objects.create(
            empresa=self.empresa, tipo="MOV", periodo=2026, ultimo_numero=8,
            prefijo="MOV",
        )
        self.assertEqual(
            vista_previa_numero(
                empresa=self.empresa, tipo_documento="MOV", fecha=date(2026, 1, 1)
            ),
            "MOV-2026-000009",
        )
        sequence.refresh_from_db()
        self.assertEqual(sequence.ultimo_numero, 8)

    def test_event_supports_multiple_handlers(self):
        bus = EventBus()
        received = []
        bus.subscribe("DomainEvent", lambda payload: received.append("a"))
        bus.subscribe("DomainEvent", lambda payload: received.append("b"))
        with self.captureOnCommitCallbacks(execute=True):
            bus.publish(DomainEvent(
                empresa_id=self.empresa.pk, agregado_tipo="test",
                agregado_id="1", clave_idempotente="multi",
            ))
        self.assertEqual(received, ["a", "b"])

    def test_failed_event_can_be_retried_once(self):
        bus = EventBus()
        calls = {"count": 0}
        def handler(payload):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("fallo")
        bus.subscribe("DomainEvent", handler)
        with self.captureOnCommitCallbacks(execute=True):
            event = bus.publish(DomainEvent(
                empresa_id=self.empresa.pk, agregado_tipo="test",
                agregado_id="1", clave_idempotente="retry",
            ))
        event.refresh_from_db()
        self.assertEqual(event.estado, EventoDominio.Estado.ERROR)
        bus.retry(event.pk)
        event.refresh_from_db()
        self.assertEqual(event.estado, EventoDominio.Estado.PROCESADO)
        self.assertEqual(event.intentos, 2)

    def test_event_payload_rejects_django_objects(self):
        bus = EventBus()
        with self.assertRaises(UnsafePayloadError):
            bus.publish(DomainEvent(
                empresa_id=self.empresa.pk, agregado_tipo="test",
                agregado_id="1", clave_idempotente="unsafe",
                payload={"empresa": self.empresa},
            ))

    def test_idempotency_and_movement_admin_are_immutable(self):
        request = type("Request", (), {"user": self.user})()
        idem_admin = RegistroIdempotenciaAdmin(RegistroIdempotencia, admin.site)
        movement_admin = MovimientoInventarioAdmin(MovimientoInventario, admin.site)
        self.assertFalse(idem_admin.has_add_permission(request))
        self.assertFalse(idem_admin.has_change_permission(request))
        self.assertFalse(idem_admin.has_delete_permission(request))
        self.assertFalse(movement_admin.has_add_permission(request))
        self.assertFalse(movement_admin.has_change_permission(request))
        self.assertFalse(movement_admin.has_delete_permission(request))

    def test_no_view_creates_movements_or_writes_stock_directly(self):
        source = Path("inventario/views.py").read_text(encoding="utf-8")
        self.assertNotIn("MovimientoInventario.objects.create", source)
        self.assertNotIn("producto.stock_actual =", source)
        self.assertNotIn("lote.cantidad_disponible =", source)

    def test_all_technical_views_require_authentication(self):
        urls = (
            reverse("core:motor_dashboard"), reverse("core:idempotencias"),
            reverse("core:eventos"), reverse("core:eventos_fallidos"),
            reverse("core:secuencias"), reverse("core:conciliaciones"),
        )
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_all_critical_actions_reject_get(self):
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=[
            "retry_eventodominio", "run_inventory_diagnosis",
            "rebuild_inventory_balance",
        ]))
        self.client.force_login(self.user)
        event = EventoDominio.objects.create(
            empresa=self.empresa, tipo_evento="X", agregado_tipo="X",
            agregado_id="1", clave_idempotente="x",
        )
        for url in (
            reverse("core:evento_reintentar", args=[event.pk]),
            reverse("core:diagnostico_producto"),
            reverse("core:reconstruir_saldo"),
        ):
            self.assertEqual(self.client.get(url).status_code, 405)

    def test_cross_company_detail_is_not_visible(self):
        other = Empresa.objects.create(nombre="Otra")
        record = RegistroIdempotencia.objects.create(
            empresa=other, clave="x", operacion="x", hash_solicitud="h"
        )
        self.user.user_permissions.add(Permission.objects.get(codename="view_registroidempotencia"))
        self.client.force_login(self.user)
        self.assertEqual(
            self.client.get(reverse("core:idempotencia_detalle", args=[record.pk])).status_code,
            404,
        )
