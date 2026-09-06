"""Auditoría ejecutable de todas las rutas GET estáticas y seguras del demo."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver

from conduces.models import Empresa


UNSAFE_SEGMENTS = {
    "accion", "acciones", "actualizar", "analizar", "anular", "aprobar", "cancelar",
    "cargar", "cerrar", "completar", "crear", "descargar", "desactivar", "desembolsar",
    "duplicar", "eliminar", "emitir", "enviar", "estado", "exportacion",
    "exportar", "facturar", "generar", "integrar", "logout", "pdf", "plantilla",
    "diagnosticar", "importar", "previsualizar", "reabrir", "rechazar", "reconstruir",
    "reenviar", "registrar", "reintentar", "revertir", "solicitar",
    "toggle", "validar",
}
EXCLUDED_PREFIXES = ("admin/", "media/", "reset/")
EXCLUDED_NAMES = {
    "password_reset", "password_reset_done", "password_reset_confirm",
    "password_reset_complete", "verificar_correo",
}


def _static_safe_routes():
    routes = []
    stack = [("", get_resolver().url_patterns)]
    while stack:
        prefix, patterns = stack.pop()
        for entry in patterns:
            route = prefix + str(entry.pattern)
            if isinstance(entry, URLResolver):
                stack.append((route, entry.url_patterns))
                continue
            if not isinstance(entry, URLPattern) or "<" in route or not entry.name:
                continue
            normalized = route.strip("/")
            segments = set(normalized.replace("_", "-").split("/"))
            words = {word for segment in segments for word in segment.split("-")}
            if route.startswith(EXCLUDED_PREFIXES):
                continue
            if entry.name in EXCLUDED_NAMES or words & UNSAFE_SEGMENTS:
                continue
            routes.append((entry.name, "/" + route))
    # Una URL puede conservar más de un nombre público por compatibilidad.
    return sorted({url: (name, url) for name, url in routes}.values(), key=lambda item: item[1])


class FullDemoSafeGetCrawlerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            "demo-full-crawler", "demo-full@example.test", "test-only"
        )
        Empresa.objects.create(
            usuario=cls.user,
            nombre="Empresa Demo Full",
            modulo_conduces=True,
            modulo_facturacion=True,
            modulo_inventario=True,
            modulo_compras=True,
            modulo_catalogos=True,
            modulo_workflow=True,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_every_static_safe_get_avoids_404_and_500(self):
        routes = _static_safe_routes()
        self.assertGreaterEqual(len(routes), 50)
        failures = []
        for name, url in routes:
            try:
                response = self.client.get(url)
            except Exception as exc:  # agrega la ruta al diagnóstico de Django
                failures.append(f"{url} ({name}): {type(exc).__name__}: {exc}")
                continue
            if response.status_code not in (200, 302):
                failures.append(f"{url} ({name}): HTTP {response.status_code}")
        self.assertFalse(failures, "Errores del crawler:\n" + "\n".join(failures))

    def test_inventory_paths_are_unique_after_alias_normalization(self):
        paths = [url for _, url in _static_safe_routes()]
        self.assertEqual(len(paths), len(set(paths)))
