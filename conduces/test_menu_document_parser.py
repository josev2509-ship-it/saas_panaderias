from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from conduces.calendar_document_parser import _normalizar
from conduces.menu_document_parser import ItemMenuExtraido, LocalMenuPDFProvider, ResultadoExtraccionMenu
from conduces.models import Empresa, ItemCicloMenu, ProgramaMenu, VersionProgramaMenu


PRODUCTOS = [
    ["Pan", "Muffin de zanahoria", "Pan", "Galleta de avena", "Pan de zanahoria"],
    ["Pan", "Muffin de maíz", "Pan de zanahoria", "Galleta de avena", "Pan"],
    ["Pan", "Galleta de avena", "Pan de zanahoria", "Muffin de avena y guineo", "Pan"],
    ["Pan", "Muffin de zanahoria", "Pan", "Galleta de avena", "Pan de zanahoria"],
    ["Pan", "Galleta de avena", "Pan de zanahoria", "Muffin de maíz", "Pan"],
]


def resultado_completo():
    return ResultadoExtraccionMenu(
        periodo="2026-2028", anio_inicio=2026, anio_fin=2028,
        codigo_modalidad="PAE-URBANO", codigo_orden="000", version="V2",
        vigente_desde=date(2026, 8, 1), semanas_ciclo=5,
        items=[ItemMenuExtraido(s, d, PRODUCTOS[s - 1][d]) for s in range(1, 6) for d in range(5)],
        confianza=1.0,
    )


class MenuDocumentParserTests(TestCase):
    def test_extrae_metadatos_matriz_y_solo_panaderia(self):
        romanos = ("I", "II", "III", "IV", "V")
        lineas = [
            "Año escolar: 2026-2028", "Código de modalidad: PAE-URBANO",
            "Código de orden: 000", "Menú cíclico V2", "Vigente desde: agosto 2026",
        ]
        for semana, romano in enumerate(romanos):
            lineas.append(f"SEMANA {romano}")
            for dia, producto in enumerate(PRODUCTOS[semana]):
                lineas.append(f"Leche y bebida {dia} / {producto}")
            lineas.append("NOTAS")
        pagina = SimpleNamespace(extract_text=lambda: "\n".join(lineas))
        with patch("conduces.menu_document_parser.PdfReader", return_value=SimpleNamespace(pages=[pagina])):
            resultado = LocalMenuPDFProvider().extract(BytesIO(b"%PDF-"))
        self.assertEqual((resultado.periodo, resultado.codigo_modalidad, resultado.codigo_orden, resultado.version), ("2026-2028", "PAE-URBANO", "000", "V2"))
        self.assertEqual(resultado.vigente_desde, date(2026, 8, 1))
        self.assertEqual(len(resultado.items), 25)
        self.assertTrue(resultado.completo_regular)
        self.assertEqual([[i.producto for i in resultado.items if i.semana == s] for s in range(1, 6)], PRODUCTOS)
        self.assertFalse(any("leche" in _normalizar(i.producto) or "bebida" in _normalizar(i.producto) for i in resultado.items))


class MenuDocumentFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("menu-importador")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Empresa menú", modulo_menu=True)
        self.user.user_permissions.add(Permission.objects.get(codename="change_programamenu"))
        self.programa = ProgramaMenu.objects.create(empresa=self.empresa, codigo="REG", nombre="Regular", modalidad="REGULAR")
        self.version = VersionProgramaMenu.objects.create(
            programa=self.programa, nombre="V2", vigente_desde=date(2026, 8, 1),
            fecha_ancla_ciclo=date(2026, 8, 24), documento_fuente=SimpleUploadedFile("menu.pdf", b"%PDF-1.4"),
        )
        self.client.force_login(self.user)

    def aplicar(self, fecha="2026-08-24"):
        with patch("conduces.menu_document_parser.LocalMenuPDFProvider.extract", return_value=resultado_completo()):
            return self.client.post(reverse("aplicar_documento_programa_menu", args=[self.version.pk]), {"fecha_uso_desde": fecha})

    def test_aplicar_crea_25_es_idempotente_y_guarda_fecha(self):
        self.assertEqual(self.aplicar().status_code, 302)
        self.assertEqual(self.aplicar().status_code, 302)
        self.version.refresh_from_db()
        self.assertEqual(self.version.items.count(), 25)
        self.assertEqual(self.version.fecha_uso_desde, date(2026, 8, 24))
        self.assertEqual([[i.producto for i in self.version.items.filter(semana=s)] for s in range(1, 6)], PRODUCTOS)

    def test_fecha_anterior_es_rechazada(self):
        self.aplicar("2026-07-31")
        self.version.refresh_from_db()
        self.assertIsNone(self.version.fecha_uso_desde)
        self.assertEqual(self.version.items.count(), 0)

    def test_version_activa_no_es_sobrescrita(self):
        self.version.estado = "ACTIVA"; self.version.save(update_fields=("estado",))
        self.aplicar()
        self.assertEqual(self.version.items.count(), 0)

    def test_usuario_sin_permiso_y_otro_tenant_no_aplican(self):
        otro = get_user_model().objects.create_user("sin-permiso")
        Empresa.objects.create(usuario=otro, nombre="Otra", modulo_menu=True)
        self.client.force_login(otro)
        self.assertEqual(self.client.post(reverse("aplicar_documento_programa_menu", args=[self.version.pk]), {"fecha_uso_desde": "2026-08-24"}).status_code, 403)
        otro.user_permissions.add(Permission.objects.get(codename="change_programamenu"))
        self.assertEqual(self.client.get(reverse("analizar_version_programa_menu", args=[self.version.pk])).status_code, 404)

    def test_activacion_exige_fecha_y_25_posiciones(self):
        url = reverse("activar_version_programa_menu", args=[self.version.pk])
        self.client.post(url)
        self.version.refresh_from_db(); self.assertEqual(self.version.estado, "BORRADOR")
        self.version.fecha_uso_desde = date(2026, 8, 24); self.version.save(update_fields=("fecha_uso_desde",))
        for item in resultado_completo().items[:-1]:
            ItemCicloMenu.objects.create(version=self.version, semana=item.semana, dia_semana=item.dia_semana, producto=item.producto)
        self.client.post(url)
        self.version.refresh_from_db(); self.assertEqual(self.version.estado, "BORRADOR")
        ultimo = resultado_completo().items[-1]
        ItemCicloMenu.objects.create(version=self.version, semana=ultimo.semana, dia_semana=ultimo.dia_semana, producto=ultimo.producto)
        self.client.post(url)
        self.version.refresh_from_db(); self.assertEqual(self.version.estado, "ACTIVA")
