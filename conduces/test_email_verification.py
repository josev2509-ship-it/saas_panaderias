import io
import json
import urllib.error
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from conduces.models import CodigoValidacion, PerfilUsuario
from core.transactional_email import (
    DeliveryResult,
    TransactionalEmailError,
    send_transactional_email,
)


class EmailVerificationFlowTests(TestCase):
    registration_data = {
        "username": "Usuario Smoke",
        "email": "smoke@example.com",
        "password1": "Clave-segura-2026!",
        "password2": "Clave-segura-2026!",
    }

    def setUp(self):
        self.delivery_patcher = patch(
            "conduces.views.send_transactional_email",
            return_value=DeliveryResult(provider="resend", message_id="email_test_123"),
        )
        self.delivery = self.delivery_patcher.start()
        self.addCleanup(self.delivery_patcher.stop)

    def register(self):
        return self.client.post(reverse("registro"), self.registration_data)

    def active_code(self):
        user = get_user_model().objects.get(username="smoke@example.com")
        return user, CodigoValidacion.objects.get(user=user, usado=False)

    def age_code_for_resend(self, code):
        CodigoValidacion.objects.filter(pk=code.pk).update(
            creado_en=timezone.now() - timedelta(seconds=61)
        )
        code.refresh_from_db()

    def test_registration_generates_six_digit_code_and_shows_verification(self):
        with self.assertLogs("conduces.verificacion_email", level="INFO") as logs:
            response = self.register()

        self.assertRedirects(response, reverse("verificar_correo"))
        user, code = self.active_code()
        self.assertFalse(user.is_active)
        self.assertRegex(code.codigo, r"^\d{6}$")
        self.assertEqual(self.delivery.call_count, 1)
        self.assertEqual(self.client.session["usuario_pendiente_id"], user.pk)
        output = "\n".join(logs.output)
        self.assertIn("VERIFICACION_EMAIL_ENVIO_INICIAL_INICIADO", output)
        self.assertIn("VERIFICACION_EMAIL_ENVIO_INICIAL_ENVIADO", output)
        self.assertNotIn(code.codigo, output)
        self.assertNotIn(user.email, output)

        page = self.client.get(reverse("verificar_correo"))
        self.assertContains(page, "smoke@example.com")
        self.assertContains(page, f'action="{reverse("reenviar_codigo_correo")}"')
        self.assertContains(page, "csrfmiddlewaretoken")

    def test_registration_failure_rolls_back_incomplete_account(self):
        self.delivery.side_effect = TransactionalEmailError(
            "application_error", status=500, request_id="request_safe_123"
        )
        with self.assertLogs("conduces.verificacion_email", level="INFO") as logs:
            response = self.register()

        self.assertRedirects(response, reverse("registro"))
        self.assertFalse(get_user_model().objects.filter(username="smoke@example.com").exists())
        self.assertFalse(CodigoValidacion.objects.exists())
        output = "\n".join(logs.output)
        self.assertIn("VERIFICACION_EMAIL_ENVIO_INICIAL_FALLIDO", output)
        self.assertIn("status=500", output)
        self.assertNotIn("smoke@example.com", output)
        self.assertNotIn("Clave-segura", output)

    def test_code_uses_secure_generator(self):
        user = get_user_model().objects.create_user(username="secure@example.com")
        with patch("conduces.models.secrets.randbelow", return_value=42) as generator:
            code = CodigoValidacion.objects.create(user=user, tipo="correo")
        generator.assert_called_once_with(900000)
        self.assertEqual(code.codigo, "100042")
        self.assertNotIn(code.codigo, str(code))

    def test_verification_activates_user_and_profile(self):
        self.register()
        user, code = self.active_code()
        response = self.client.post(reverse("verificar_correo"), {"codigo": code.codigo})

        self.assertRedirects(response, reverse("inicio"))
        user.refresh_from_db()
        code.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(code.usado)
        self.assertTrue(PerfilUsuario.objects.get(user=user).correo_validado)

    def test_incorrect_code_counts_attempt(self):
        self.register()
        _, code = self.active_code()
        response = self.client.post(reverse("verificar_correo"), {"codigo": "000000"})

        self.assertRedirects(response, reverse("verificar_correo"))
        code.refresh_from_db()
        self.assertEqual(code.intentos_fallidos, 1)
        self.assertFalse(code.usado)

    def test_fifth_incorrect_attempt_invalidates_code(self):
        self.register()
        _, code = self.active_code()
        for _ in range(5):
            self.client.post(reverse("verificar_correo"), {"codigo": "000000"})

        code.refresh_from_db()
        self.assertEqual(code.intentos_fallidos, 5)
        self.assertTrue(code.usado)

    def test_expired_code_is_rejected_and_invalidated(self):
        self.register()
        _, code = self.active_code()
        CodigoValidacion.objects.filter(pk=code.pk).update(
            expira_en=timezone.now() - timedelta(seconds=1)
        )
        response = self.client.post(reverse("verificar_correo"), {"codigo": code.codigo})

        self.assertRedirects(response, reverse("verificar_correo"))
        code.refresh_from_db()
        self.assertTrue(code.usado)

    def test_resend_is_post_only_and_requires_csrf(self):
        self.register()
        self.assertEqual(self.client.get(reverse("reenviar_codigo_correo")).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        session = csrf_client.session
        session["usuario_pendiente_id"] = get_user_model().objects.get(
            username="smoke@example.com"
        ).pk
        session.save()
        self.assertEqual(csrf_client.post(reverse("reenviar_codigo_correo")).status_code, 403)

    def test_resend_cooldown_preserves_current_code(self):
        self.register()
        _, previous = self.active_code()
        with self.assertLogs("conduces.verificacion_email", level="INFO") as logs:
            response = self.client.post(reverse("reenviar_codigo_correo"))

        self.assertRedirects(response, reverse("verificar_correo"))
        previous.refresh_from_db()
        self.assertFalse(previous.usado)
        self.assertEqual(CodigoValidacion.objects.count(), 1)
        self.assertEqual(self.delivery.call_count, 1)
        self.assertIn("causa=cooldown", "\n".join(logs.output))

    def test_resend_after_cooldown_replaces_previous_code(self):
        self.register()
        user, previous = self.active_code()
        self.age_code_for_resend(previous)
        with self.assertLogs("conduces.verificacion_email", level="INFO") as logs:
            response = self.client.post(reverse("reenviar_codigo_correo"))

        self.assertRedirects(response, reverse("verificar_correo"))
        previous.refresh_from_db()
        self.assertTrue(previous.usado)
        current = CodigoValidacion.objects.get(user=user, usado=False)
        self.assertNotEqual(current.pk, previous.pk)
        self.assertEqual(self.delivery.call_count, 2)
        output = "\n".join(logs.output)
        self.assertIn("VERIFICACION_EMAIL_REENVIO_INICIADO", output)
        self.assertIn("VERIFICACION_EMAIL_REENVIO_ENVIADO", output)

    def test_resend_api_failure_rolls_back_and_preserves_previous_code(self):
        self.register()
        user, previous = self.active_code()
        self.age_code_for_resend(previous)
        self.delivery.side_effect = TransactionalEmailError(
            "rate_limit_exceeded", status=429, request_id="request_safe_456"
        )
        with self.assertLogs("conduces.verificacion_email", level="INFO") as logs:
            response = self.client.post(reverse("reenviar_codigo_correo"))

        self.assertRedirects(response, reverse("verificar_correo"))
        previous.refresh_from_db()
        self.assertFalse(previous.usado)
        self.assertEqual(CodigoValidacion.objects.filter(user=user).count(), 1)
        output = "\n".join(logs.output)
        self.assertIn("VERIFICACION_EMAIL_REENVIO_FALLIDO", output)
        self.assertIn("rate_limit_exceeded", output)
        self.assertIn("status=429", output)
        self.assertNotIn(previous.codigo, output)
        self.assertNotIn(user.email, output)


class PasswordRecoveryEmailTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="recovery@example.com",
            email="recovery@example.com",
            password="Recover-2026!",
            is_active=True,
        )

    @patch(
        "core.transactional_email.send_transactional_email",
        return_value=DeliveryResult(provider="resend", message_id="password_email_123"),
    )
    def test_password_recovery_uses_transactional_backend(self, delivery):
        with self.assertLogs("conduces.recuperacion_password", level="INFO") as logs:
            response = self.client.post(reverse("password_reset"), {"email": self.user.email})
        self.assertRedirects(response, reverse("password_reset_done"))
        delivery.assert_called_once()
        output = "\n".join(logs.output)
        self.assertIn("RECUPERACION_PASSWORD_ENVIO_INICIADO", output)
        self.assertIn("RECUPERACION_PASSWORD_ENVIO_ENVIADO", output)
        self.assertNotIn(self.user.email, output)

    @patch(
        "core.transactional_email.send_transactional_email",
        side_effect=TransactionalEmailError("application_error", status=500),
    )
    def test_password_recovery_failure_is_safe(self, delivery):
        with self.assertLogs("conduces.recuperacion_password", level="INFO") as logs:
            response = self.client.post(reverse("password_reset"), {"email": self.user.email})
        self.assertRedirects(response, reverse("password_reset"))
        delivery.assert_called_once()
        output = "\n".join(logs.output)
        self.assertIn("RECUPERACION_PASSWORD_ENVIO_FALLIDO", output)
        self.assertIn("status=500", output)
        self.assertNotIn(self.user.email, output)


class ResendApiServiceTests(TestCase):
    @override_settings(RESEND_API_KEY="")
    def test_missing_api_key_fails_safely(self):
        with self.assertRaises(TransactionalEmailError) as error:
            send_transactional_email(
                subject="Subject", text="Body", recipients=["recipient@example.com"]
            )
        self.assertEqual(error.exception.category, "missing_resend_api_key")

    @override_settings(
        RESEND_API_KEY="test_api_key_not_real",
        DEFAULT_FROM_EMAIL="SASTRE ERP <no-reply@notificaciones.saaspanaderias.com>",
    )
    @patch("core.transactional_email.urllib.request.urlopen")
    def test_https_api_request_uses_resend_contract(self, urlopen):
        response = MagicMock()
        response.status = 200
        response.headers = {"x-request-id": "request_123"}
        response.read.return_value = json.dumps({"id": "email_123"}).encode()
        urlopen.return_value.__enter__.return_value = response

        result = send_transactional_email(
            subject="Subject",
            text="Body",
            recipients=["recipient@example.com"],
            idempotency_key="test/idempotency/1",
        )
        self.assertEqual(result.message_id, "email_123")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.resend.com/emails")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.headers["Idempotency-key"], "test/idempotency/1")
        self.assertEqual(request.headers["User-agent"], "sastre-erp/1.0")

    @override_settings(RESEND_API_KEY="test_api_key_not_real")
    @patch("core.transactional_email.urllib.request.urlopen")
    def test_resend_http_error_exposes_only_safe_metadata(self, urlopen):
        urlopen.side_effect = urllib.error.HTTPError(
            "https://api.resend.com/emails",
            429,
            "Too Many Requests",
            {"x-request-id": "request_429"},
            io.BytesIO(b'{"name":"rate_limit_exceeded","message":"private detail"}'),
        )
        with self.assertRaises(TransactionalEmailError) as error:
            send_transactional_email(
                subject="Subject",
                text="Sensitive body",
                recipients=["recipient@example.com"],
            )
        self.assertEqual(error.exception.category, "rate_limit_exceeded")
        self.assertEqual(error.exception.status, 429)
        self.assertEqual(error.exception.request_id, "request_429")
        self.assertNotIn("private detail", str(error.exception))
