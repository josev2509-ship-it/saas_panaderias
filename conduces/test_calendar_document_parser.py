import tempfile
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from reportlab.pdfgen import canvas

from conduces.calendar_document_parser import LocalTextPDFProvider
from conduces.calendar_document_service import analizar_documento_calendario, validar_pdf
from conduces.models import (
    AnalisisDocumentoCalendario,
    CalendarioEscolar,
    Empresa,
    EventoDocumentoCalendario,
)


TOTALES_2026_2027 = {
    (2026, 8): 6, (2026, 9): 21, (2026, 10): 22, (2026, 11): 20,
    (2026, 12): 14, (2027, 1): 15, (2027, 2): 20, (2027, 3): 18,
    (2027, 4): 21, (2027, 5): 19, (2027, 6): 14,
}


def crear_pdf(lineas, nombre="calendario.pdf"):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    y = 800
    for linea in lineas:
        pdf.drawString(45, y, linea)
        y -= 24
        if y < 50:
            pdf.showPage(); y = 800
    pdf.save()
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="application/pdf")


class ArchivoPDFConTamano(BytesIO):
    name = "calendario.pdf"

    def __init__(self, size):
        super().__init__(b"%PDF-")
        self.size = size


def lineas_calendario_oficial(total=190, incluir_total=True):
    lineas = [
        "CALENDARIO ESCOLAR 2026-2027",
        "Inicio de docencia: 24/08/2026",
        "Fin de docencia: 18/06/2027",
    ]
    if incluir_total:
        lineas.append(f"Total oficial de dias lectivos: {total} dias")
    nombres = ("Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio")
    for nombre, ((anio, _mes), dias) in zip(nombres, TOTALES_2026_2027.items()):
        lineas.append(f"{nombre} {anio}: {dias} dias lectivos")
    lineas += [
        "Feriado oficial: 24/09/2026",
        "Jornada docente sin docencia: 06/11/2026",
        "Vacaciones de Navidad: 21/12/2026 al 31/12/2026",
        "Vacaciones de Navidad y reinicio: 01/01/2027 al 08/01/2027",
        "Semana Santa: 22/03/2027 al 26/03/2027",
        "Dia de la ADP - no lectivo: 13/04/2027",
        "Dias no lectivos oficiales: 03/05/2027",
        "Jornada administrativa sin docencia: 27/05/2027",
    ]
    return lineas


class CalendarDocumentParserTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_dir = tempfile.TemporaryDirectory()
        cls.override = override_settings(MEDIA_ROOT=cls.media_dir.name)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        cls.media_dir.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user("calendar-admin", password="x")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Empresa A", modulo_menu=True)
        self.user.user_permissions.add(Permission.objects.get(codename="change_programamenu"))

    def parsear(self, lineas):
        archivo = crear_pdf(lineas)
        return LocalTextPDFProvider().extract(archivo)

    def test_pdf_valido_extrae_inicio_fin_total_y_ano(self):
        resultado = self.parsear(lineas_calendario_oficial())
        self.assertEqual((resultado.anio_inicio, resultado.anio_fin), (2026, 2027))
        self.assertEqual(resultado.inicio_docencia, date(2026, 8, 24))
        self.assertEqual(resultado.fin_docencia, date(2027, 6, 18))
        self.assertEqual(resultado.total_oficial, 190)

    def test_referencia_historica_interior_no_vence_portada(self):
        resultado = self.parsear([
            "CALENDARIO ESCOLAR 2031-2032",
            "Inicio de docencia: 25/08/2031",
            "Fin de docencia: 18/06/2032",
            "Referencia historica al calendario escolar 2017-2018",
        ])
        self.assertEqual((resultado.anio_inicio, resultado.anio_fin), (2031, 2032))
        self.assertEqual(resultado.evidencias["anio_escolar"].pagina, 1)

    def test_fecha_natural_con_numeros_entre_parentesis(self):
        resultado = self.parsear([
            "CALENDARIO ESCOLAR 2031-2032",
            "Estudiantes: inicia la docencia el lunes veinticinco (25) de agosto de dos mil treinta y uno (2031) y concluye el viernes dieciocho (18) de junio de dos mil treinta y dos (2032).",
            "Total: ciento ochenta y ocho (188) dias laborables de docencia.",
        ])
        self.assertEqual(resultado.inicio_docencia, date(2031, 8, 25))
        self.assertEqual(resultado.fin_docencia, date(2032, 6, 18))

    def test_ordinal_feria_no_es_total_mensual(self):
        resultado = self.parsear([
            "CALENDARIO ESCOLAR 2031-2032",
            "Febrero 2032 - 1ª Feria Escolar de Artesania y Artes Aplicadas.",
        ])
        self.assertNotIn((2032, 2), resultado.totales_mensuales)

    def test_evento_repartido_reconstruye_fecha_desde_celda_y_mes(self):
        resultado = self.parsear([
            "CALENDARIO ESCOLAR 2031-2032",
            "Abril 2032",
            "13",
            "Conmemoracion de la asociacion docente.",
            "No laborable para sus miembros.",
        ])
        evento = next(evento for evento in resultado.eventos if evento.tipo == "NO_LECTIVO")
        self.assertEqual(evento.fecha_inicio, date(2032, 4, 13))
        self.assertIn("No laborable", evento.evidencia.texto)

    def test_lista_oficial_feriados_respeta_cambio_anual_y_traslado(self):
        resultado = self.parsear([
            "CALENDARIO ESCOLAR 2031-2032",
            "Dias feriados",
            "Jueves 25 de diciembre",
            "Celebracion de diciembre",
            "Miercoles 6 de enero",
            "(movido al lunes 4 de enero)",
            "Celebracion de enero",
            "Viernes 1 de mayo",
            "Celebracion de mayo",
        ])
        feriados = {evento.fecha_inicio for evento in resultado.eventos if evento.tipo == "FERIADO"}
        self.assertIn(date(2031, 12, 25), feriados)
        self.assertIn(date(2032, 1, 4), feriados)
        self.assertIn(date(2032, 5, 1), feriados)

    @override_settings(CALENDAR_PDF_MAX_MB=30)
    def test_pdf_mayor_10_mb_dentro_limite_configurable_es_aceptado(self):
        validar_pdf(ArchivoPDFConTamano(11 * 1024 * 1024))

    @override_settings(CALENDAR_PDF_MAX_MB=30)
    def test_pdf_sobre_limite_configurable_es_rechazado(self):
        with self.assertRaisesMessage(Exception, "limite de 30 MB"):
            validar_pdf(ArchivoPDFConTamano(31 * 1024 * 1024))

    def test_documento_sin_texto_requiere_revision(self):
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)
        pdf.showPage()
        pdf.save()
        resultado = LocalTextPDFProvider().extract(BytesIO(buffer.getvalue()))
        self.assertEqual(resultado.confianza, 0)
        self.assertTrue(any("no contiene texto" in mensaje for mensaje in resultado.advertencias))

    def test_documento_ambiguo_permanece_en_revision(self):
        analisis = analizar_documento_calendario(
            empresa=self.empresa,
            usuario=self.user,
            archivo=crear_pdf(["CALENDARIO ESCOLAR 2031-2032", "Contenido sin fechas de vigencia"]),
        )
        self.assertEqual(analisis.estado, AnalisisDocumentoCalendario.Estado.REQUIERE_REVISION)
        self.assertIsNone(analisis.calendario)

    def test_documento_sin_total_no_asume_190(self):
        resultado = self.parsear(lineas_calendario_oficial(incluir_total=False))
        self.assertIsNone(resultado.total_oficial)
        self.assertTrue(any("no declara" in mensaje for mensaje in resultado.advertencias))

    def test_total_oficial_distinto_de_190_se_respeta(self):
        resultado = self.parsear(lineas_calendario_oficial(total=188))
        self.assertEqual(resultado.total_oficial, 188)

    def test_extrae_totales_mensuales_fixture_2026_2027(self):
        resultado = self.parsear(lineas_calendario_oficial())
        self.assertEqual({clave: valor[0] for clave, valor in resultado.totales_mensuales.items()}, TOTALES_2026_2027)

    def test_extrae_feriado_vacaciones_semana_santa_y_adp(self):
        resultado = self.parsear(lineas_calendario_oficial())
        eventos = {(evento.fecha_inicio, evento.clasificacion): evento for evento in resultado.eventos}
        self.assertIn((date(2026, 9, 24), "FERIADO"), eventos)
        self.assertIn((date(2026, 12, 21), "VACACIONES"), eventos)
        self.assertIn((date(2027, 3, 22), "VACACIONES"), eventos)
        self.assertIn((date(2027, 4, 13), "NO_LECTIVO"), eventos)

    def test_pdf_invalido_es_rechazado(self):
        archivo = SimpleUploadedFile("falso.pdf", b"esto no es pdf", content_type="application/pdf")
        with self.assertRaisesMessage(Exception, "cabecera PDF valida"):
            analizar_documento_calendario(empresa=self.empresa, usuario=self.user, archivo=archivo)

    def test_fixture_construye_distribucion_mensual_y_adp(self):
        analisis = analizar_documento_calendario(
            empresa=self.empresa, usuario=self.user, archivo=crear_pdf(lineas_calendario_oficial())
        )
        obtenidos = {(total.anio, total.mes): total.dias_calculados for total in analisis.totales_mensuales.all()}
        self.assertEqual(obtenidos, TOTALES_2026_2027)
        self.assertTrue(all(total.estado == "OK" for total in analisis.totales_mensuales.all()))
        adp = analisis.calendario.dias.get(fecha=date(2027, 4, 13))
        self.assertEqual(adp.clasificacion, "NO_LECTIVO")

    def test_diferencia_mensual_detectada_y_eventos_explican(self):
        lineas = lineas_calendario_oficial()
        lineas.remove("Dia de la ADP - no lectivo: 13/04/2027")
        analisis = analizar_documento_calendario(
            empresa=self.empresa, usuario=self.user, archivo=crear_pdf(lineas)
        )
        abril = analisis.totales_mensuales.get(anio=2027, mes=4)
        self.assertEqual(abril.diferencia, 1)
        self.assertEqual(abril.estado, "REQUIERE_REVISION")
        self.assertIn("no se encontro evidencia suficiente", abril.explicacion)

    def test_discrepancia_con_evento_conserva_explicacion(self):
        lineas = lineas_calendario_oficial()
        indice = lineas.index("Abril 2027: 21 dias lectivos")
        lineas[indice] = "Abril 2027: 20 dias lectivos"
        analisis = analizar_documento_calendario(
            empresa=self.empresa, usuario=self.user, archivo=crear_pdf(lineas)
        )
        abril = analisis.totales_mensuales.get(anio=2027, mes=4)
        self.assertEqual(abril.diferencia, 1)
        self.assertIn("Eventos detectados", abril.explicacion)

    def test_evidencia_pagina_confianza_y_estado_se_conservan(self):
        analisis = analizar_documento_calendario(
            empresa=self.empresa, usuario=self.user, archivo=crear_pdf(lineas_calendario_oficial())
        )
        adp = analisis.eventos.get(fecha_inicio=date(2027, 4, 13))
        self.assertIsNotNone(adp.pagina)
        self.assertGreater(adp.confianza, 0)
        self.assertEqual(adp.estado, EventoDocumentoCalendario.Estado.DETECTADO)

    def test_reanalisis_crea_version_nueva(self):
        analisis = analizar_documento_calendario(
            empresa=self.empresa, usuario=self.user, archivo=crear_pdf(lineas_calendario_oficial())
        )
        self.client.force_login(self.user)
        response = self.client.post(reverse("reanalizar_calendario", args=[analisis.calendario_id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AnalisisDocumentoCalendario.objects.filter(calendario=analisis.calendario).count(), 2)

    def test_calendario_activo_no_se_sobrescribe_al_reanalizar(self):
        analisis = analizar_documento_calendario(
            empresa=self.empresa, usuario=self.user, archivo=crear_pdf(lineas_calendario_oficial())
        )
        calendario = analisis.calendario
        calendario.estado = CalendarioEscolar.Estado.ACTIVO
        calendario.save()
        inicio_original = calendario.inicio_docencia
        nuevo = analizar_documento_calendario(
            empresa=self.empresa, usuario=self.user,
            archivo=crear_pdf([*lineas_calendario_oficial(), "Inicio de docencia: 25/08/2026"]),
            calendario=calendario,
        )
        calendario.refresh_from_db()
        self.assertEqual(calendario.inicio_docencia, inicio_original)
        self.assertEqual(nuevo.estado, AnalisisDocumentoCalendario.Estado.REQUIERE_REVISION)

    def test_otro_tenant_no_puede_reanalizar(self):
        analisis = analizar_documento_calendario(
            empresa=self.empresa, usuario=self.user, archivo=crear_pdf(lineas_calendario_oficial())
        )
        otro = get_user_model().objects.create_user("otro")
        Empresa.objects.create(usuario=otro, nombre="Empresa B", modulo_menu=True)
        otro.user_permissions.add(Permission.objects.get(codename="change_programamenu"))
        self.client.force_login(otro)
        response = self.client.post(reverse("reanalizar_calendario", args=[analisis.calendario_id]))
        self.assertEqual(response.status_code, 404)

    def test_usuario_sin_permiso_no_puede_analizar(self):
        consulta = get_user_model().objects.create_user("consulta")
        Empresa.objects.create(usuario=consulta, nombre="Empresa Consulta", modulo_menu=True)
        self.client.force_login(consulta)
        response = self.client.post(
            reverse("subir_analizar_calendario"),
            {"documento_fuente": crear_pdf(lineas_calendario_oficial())},
        )
        self.assertEqual(response.status_code, 403)
