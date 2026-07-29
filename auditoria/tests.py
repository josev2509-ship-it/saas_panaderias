from django.test import TestCase


class AuditoriaSmokeTest(TestCase):
    def test_app_carga(self):
        from .services import registrar_evento
        self.assertTrue(callable(registrar_evento))
