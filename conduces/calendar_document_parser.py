import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

from pypdf import PdfReader


MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
NOMBRES_MESES = "|".join(MESES)


def _normalizar(texto):
    return "".join(
        caracter for caracter in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(caracter) != "Mn"
    )


def _compactar(texto):
    return " ".join(texto.replace("\ufffd", " ").split())


def _fecha_numerica(texto):
    coincidencia = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", texto)
    if not coincidencia:
        return None
    try:
        return date(int(coincidencia.group(3)), int(coincidencia.group(2)), int(coincidencia.group(1)))
    except ValueError:
        return None


def _fechas_linea(texto):
    fechas = []
    for dia, mes, anio in re.findall(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", texto):
        try:
            fechas.append(date(int(anio), int(mes), int(dia)))
        except ValueError:
            continue
    normalizado = _normalizar(texto)
    patron_natural = re.compile(
        rf"(?:\b[a-z]+\s+)?(?:\((\d{{1,2}})\)|(\d{{1,2}}))\s+de\s+({NOMBRES_MESES})"
        rf"\s+(?:de\s+)?(?:[a-z]+\s+){{0,8}}(?:\((20\d{{2}})\)|(20\d{{2}})\b)"
    )
    for dia_parentesis, dia_directo, mes_texto, anio_parentesis, anio_directo in patron_natural.findall(normalizado):
        try:
            fechas.append(date(
                int(anio_parentesis or anio_directo), MESES[mes_texto], int(dia_parentesis or dia_directo),
            ))
        except ValueError:
            continue
    return list(dict.fromkeys(fechas))


@dataclass(frozen=True)
class Evidencia:
    texto: str
    pagina: int | None
    confianza: float


@dataclass(frozen=True)
class EventoExtraido:
    fecha_inicio: date
    fecha_fin: date | None
    clasificacion: str
    tipo: str
    descripcion: str
    evidencia: Evidencia


@dataclass
class ResultadoExtraccionCalendario:
    nombre: str = ""
    anio_inicio: int | None = None
    anio_fin: int | None = None
    inicio_docencia: date | None = None
    fin_docencia: date | None = None
    total_oficial: int | None = None
    totales_mensuales: dict[tuple[int, int], tuple[int, Evidencia]] = field(default_factory=dict)
    eventos: list[EventoExtraido] = field(default_factory=list)
    evidencias: dict[str, Evidencia] = field(default_factory=dict)
    advertencias: list[str] = field(default_factory=list)
    confianza: float = 0
    texto: str = ""
    paginas: int = 0


class CalendarExtractionProvider(Protocol):
    nombre: str
    version: str

    def extract(self, archivo) -> ResultadoExtraccionCalendario: ...


class LocalTextPDFProvider:
    nombre = "local_pypdf_deterministic"
    version = "2.0"

    def extract(self, archivo):
        archivo.seek(0)
        lector = PdfReader(archivo)
        paginas = [(numero, pagina.extract_text() or "") for numero, pagina in enumerate(lector.pages, start=1)]
        texto = "\n".join(contenido for _, contenido in paginas)
        resultado = ResultadoExtraccionCalendario(texto=texto, paginas=len(paginas))
        if not texto.strip():
            resultado.advertencias.append("El PDF no contiene texto extraible; requiere revision manual u OCR futuro.")
            return resultado

        self._extraer_estructura(resultado, paginas)
        meses_por_pagina = self._meses_dominantes(paginas)
        self._extraer_totales_resumen(resultado, paginas)
        self._extraer_totales_por_pagina(resultado, paginas, meses_por_pagina)
        self._extraer_eventos(resultado, paginas, meses_por_pagina)
        self._extraer_feriados_oficiales(resultado, paginas)
        self._inferir_periodos_documentados(resultado, paginas)

        if not resultado.inicio_docencia:
            resultado.advertencias.append("No se detectó el inicio de docencia.")
        if not resultado.fin_docencia:
            resultado.advertencias.append("No se detectó el fin de docencia.")
        if resultado.total_oficial is None:
            resultado.advertencias.append("El documento no declara un total oficial identificable.")
        campos = (resultado.anio_inicio, resultado.anio_fin, resultado.inicio_docencia, resultado.fin_docencia)
        resultado.confianza = round(
            (sum(valor is not None for valor in campos) / len(campos)) * 0.8
            + (0.2 if resultado.total_oficial is not None else 0), 4,
        )
        archivo.seek(0)
        return resultado

    def _extraer_estructura(self, resultado, paginas):
        candidatos = []
        patrones = (
            re.compile(r"calendario\s+escolar\s*[:\-]?\s*(20\d{2})\s*[-–/]\s*(20\d{2})", re.I),
            re.compile(r"a[nñ]o\s+(?:escolar|lectivo)\s*[:\-]?\s*(20\d{2})\s*[-–/]\s*(20\d{2})", re.I),
        )
        for pagina, contenido in paginas:
            compacto = _compactar(contenido)
            for prioridad, patron in enumerate(patrones):
                for coincidencia in patron.finditer(compacto):
                    confianza = 0.99 if pagina == 1 and prioridad == 0 else 0.96 if pagina <= 5 else 0.85
                    candidatos.append((confianza, -pagina, coincidencia, pagina))
        if not candidatos:
            for pagina, contenido in paginas:
                coincidencia = re.search(r"\b(20\d{2})\s*[-–/]\s*(20\d{2})\b", contenido)
                if coincidencia:
                    candidatos.append((0.55, -pagina, coincidencia, pagina))
        if candidatos:
            confianza, _, coincidencia, pagina = max(candidatos, key=lambda item: (item[0], item[1]))
            resultado.anio_inicio, resultado.anio_fin = int(coincidencia.group(1)), int(coincidencia.group(2))
            resultado.nombre = f"Año escolar {resultado.anio_inicio}-{resultado.anio_fin}"
            resultado.evidencias["anio_escolar"] = Evidencia(coincidencia.group(0), pagina, confianza)
        else:
            resultado.advertencias.append("No se pudo determinar el año escolar.")

        for pagina, contenido in paginas:
            compacto = _compactar(contenido)
            normalizado = _normalizar(compacto)
            posicion = normalizado.find("estudiantes")
            segmento = normalizado[posicion:posicion + 900] if posicion >= 0 else normalizado
            expresion_inicio = any(
                expresion in segmento
                for expresion in ("inicio de docencia", "inicia la docencia", "inicia el")
            )
            if not expresion_inicio or "docencia" not in segmento:
                continue
            fechas = _fechas_linea(segmento)
            if fechas:
                resultado.inicio_docencia = fechas[0]
                evidencia = Evidencia(
                    compacto[posicion:posicion + 650] if posicion >= 0 else compacto[:650],
                    pagina, 0.96 if posicion >= 0 else 0.82,
                )
                resultado.evidencias["inicio_docencia"] = evidencia
                if len(fechas) > 1 and any(x in segmento for x in ("conclusion", "concluye", "finaliza")):
                    resultado.fin_docencia = fechas[1]
                    resultado.evidencias["fin_docencia"] = evidencia
                break

        if not resultado.inicio_docencia or not resultado.fin_docencia:
            for pagina, contenido in paginas:
                for linea in contenido.splitlines():
                    normalizada = _normalizar(linea)
                    fechas = _fechas_linea(linea)
                    if not fechas:
                        continue
                    if not resultado.inicio_docencia and "inicio" in normalizada and "docencia" in normalizada:
                        resultado.inicio_docencia = fechas[0]
                        resultado.evidencias["inicio_docencia"] = Evidencia(_compactar(linea), pagina, 0.85)
                    if not resultado.fin_docencia and any(x in normalizada for x in ("fin", "final", "conclu")) and "docencia" in normalizada:
                        resultado.fin_docencia = fechas[-1]
                        resultado.evidencias["fin_docencia"] = Evidencia(_compactar(linea), pagina, 0.85)

        patron_total = re.compile(
            r"(?:[a-záéíóúñ]+\s+){0,4}\((\d{2,3})\)\s+d[ií]as\s+(?:laborables|lectivos|de\s+docencia|de\s+docencia\s+efectiva)|"
            r"\b(\d{2,3})\s+d[ií]as\s+(?:lectivos|de\s+docencia(?:\s+efectiva)?)|"
            r"(?:total(?:\s+oficial)?\s+de\s+)?d[ií]as\s+(?:lectivos|de\s+docencia)\s*:\s*(\d{2,3})\s+d[ií]as", re.I,
        )
        candidatos_total = []
        for pagina, contenido in paginas:
            compacto = _compactar(contenido)
            for coincidencia in patron_total.finditer(compacto):
                valor = int(coincidencia.group(1) or coincidencia.group(2) or coincidencia.group(3))
                if 100 <= valor <= 260:
                    contexto = compacto[max(0, coincidencia.start() - 100):coincidencia.end() + 100]
                    prioridad = 0.98 if "efectiva para estudiantes" in _normalizar(contexto) else 0.92
                    candidatos_total.append((prioridad, -pagina, valor, pagina, contexto))
        if candidatos_total:
            confianza, _, valor, pagina, contexto = max(candidatos_total, key=lambda item: (item[0], item[1]))
            resultado.total_oficial = valor
            resultado.evidencias["total_oficial"] = Evidencia(contexto, pagina, confianza)

    def _meses_dominantes(self, paginas):
        explicitos = {}
        patron = re.compile(rf"\b({NOMBRES_MESES})\s+(20\d{{2}})\b", re.I)
        for pagina, contenido in paginas:
            coincidencias = [(MESES[_normalizar(mes)], int(anio)) for mes, anio in patron.findall(contenido)]
            if coincidencias:
                explicitos[pagina] = Counter(coincidencias).most_common(1)[0][0]
        dominantes = dict(explicitos)
        for pagina, _ in paginas:
            if pagina not in dominantes:
                anteriores = [p for p in explicitos if 0 < pagina - p <= 2]
                if anteriores:
                    dominantes[pagina] = explicitos[max(anteriores)]
        return dominantes

    def _anio_para_mes(self, resultado, mes):
        if not resultado.anio_inicio or not resultado.anio_fin:
            return None
        mes_inicio = resultado.inicio_docencia.month if resultado.inicio_docencia else 8
        return resultado.anio_inicio if mes >= mes_inicio else resultado.anio_fin

    def _extraer_totales_resumen(self, resultado, paginas):
        patron_mes = re.compile(rf"^\s*({NOMBRES_MESES})\s*:\s*$", re.I)
        patron_dias = re.compile(r"\b(\d{1,2})\s+d[ií]as?\b", re.I)
        patron_docencia = re.compile(r"\b(\d{1,2})\s+d[ií]as?\s+de\s+docencia\b", re.I)
        for pagina, contenido in paginas:
            lineas = [_compactar(linea) for linea in contenido.splitlines() if linea.strip()]
            indices = [(i, MESES[_normalizar(m.group(1))]) for i, linea in enumerate(lineas) if (m := patron_mes.match(linea))]
            if len(indices) < 3:
                continue
            ultimo_indice = indices[-1][0]
            valores = []
            for linea in lineas[ultimo_indice + 1:]:
                if "docencia efectiva para estudiantes" in _normalizar(linea):
                    break
                coincidencia = patron_docencia.search(linea) or patron_dias.search(linea)
                if coincidencia:
                    valor = int(coincidencia.group(1))
                    if 1 <= valor <= 23:
                        valores.append((valor, linea))
                if len(valores) >= len(indices):
                    break
            if len(valores) < len(indices):
                continue
            for (_, mes), (valor, evidencia_texto) in zip(indices, valores):
                anio = self._anio_para_mes(resultado, mes)
                if anio:
                    resultado.totales_mensuales[(anio, mes)] = (valor, Evidencia(evidencia_texto, pagina, 0.97))
            return

    def _extraer_totales_por_pagina(self, resultado, paginas, meses_por_pagina):
        patron = re.compile(r"\b(\d{1,2})\s+d[ií]as?\s+lectivos\b", re.I)
        patron_linea = re.compile(
            rf"\b({NOMBRES_MESES})\s+(20\d{{2}})\D{{0,25}}(\d{{1,2}})\s+d[ií]as?\s+lectivos\b",
            re.I,
        )
        for pagina, contenido in paginas:
            for mes_texto, anio, dias in patron_linea.findall(_compactar(contenido)):
                valor = int(dias)
                if 1 <= valor <= 23:
                    resultado.totales_mensuales[(int(anio), MESES[_normalizar(mes_texto)])] = (
                        valor, Evidencia(f"{mes_texto} {anio}: {dias} dias lectivos", pagina, 0.95),
                    )
            mes_anio = meses_por_pagina.get(pagina)
            clave = (mes_anio[1], mes_anio[0]) if mes_anio else None
            if not clave or clave in resultado.totales_mensuales:
                continue
            coincidencias = [m for m in patron.finditer(_compactar(contenido)) if 1 <= int(m.group(1)) <= 23]
            if coincidencias:
                coincidencia = coincidencias[-1]
                resultado.totales_mensuales[clave] = (
                    int(coincidencia.group(1)), Evidencia(coincidencia.group(0), pagina, 0.9),
                )

    def _clasificar_evento(self, texto):
        normalizado = _normalizar(texto)
        if normalizado.strip().startswith("reinicio") and any(x in normalizado for x in ("docencia", "clases")):
            return "DOCENCIA"
        if "suspension" in normalizado or "suspend" in normalizado:
            return "SUSPENSION"
        if any(x in normalizado for x in ("vacacion", "naviden", "semana santa")):
            return "VACACIONES"
        if "feriado" in normalizado:
            return "FERIADO"
        if any(x in normalizado for x in ("no laborable", "no lectiv", "sin docencia", "jornada docente", "jornada administrativa")):
            return "NO_LECTIVO"
        return None

    def _tipo_evento(self, texto, clasificacion):
        normalizado = _normalizar(texto)
        if clasificacion == "FERIADO":
            return "FERIADO"
        if clasificacion == "SUSPENSION":
            return "SUSPENSION"
        if clasificacion == "DOCENCIA":
            return "REINICIO_DOCENCIA"
        if "semana santa" in normalizado:
            return "SEMANA_SANTA"
        if "navid" in normalizado or "na vide" in normalizado:
            return "VACACIONES_NAVIDAD"
        if clasificacion == "NO_LECTIVO" and "jornada" in normalizado:
            return "JORNADA_ESPECIAL"
        if clasificacion == "NO_LECTIVO":
            return "NO_LECTIVO"
        return "OTRO"

    def _dia_contextual(self, texto):
        coincidencia = re.search(r"(?:^|\s)([1-9]|[12]\d|3[01])\s+(?![.ªº])(?=[A-Za-zÁÉÍÓÚÑ])", texto)
        return int(coincidencia.group(1)) if coincidencia else None

    def _rango_contextual(self, texto, mes_anio):
        normalizado = _normalizar(texto)
        coincidencia = re.search(
            rf"\bdel?\s+(\d{{1,2}})\s+de\s+({NOMBRES_MESES})\s+al\s+(\d{{1,2}})\s+de\s+({NOMBRES_MESES})\b",
            normalizado,
        )
        if not coincidencia:
            return None
        dia_inicio, mes_inicio, dia_fin, mes_fin = coincidencia.groups()
        mes_inicio, mes_fin = MESES[mes_inicio], MESES[mes_fin]
        anio_referencia = mes_anio[1]
        anio_inicio = anio_referencia
        anio_fin = anio_referencia + (1 if mes_fin < mes_inicio else 0)
        try:
            return date(anio_inicio, mes_inicio, int(dia_inicio)), date(anio_fin, mes_fin, int(dia_fin))
        except ValueError:
            return None

    def _celdas_pagina(self, lineas):
        celdas = []
        dia_actual = None
        contenido = []
        for linea in lineas:
            dia_solo = re.fullmatch(r"([1-9]|[12]\d|3[01])", linea)
            dia_con_texto = re.match(r"^([1-9]|[12]\d|3[01])\s+(?![.ªº])(.*\D.*)$", linea)
            if dia_solo or dia_con_texto:
                if dia_actual is not None and contenido:
                    celdas.append((dia_actual, " ".join(contenido)))
                dia_actual = int((dia_solo or dia_con_texto).group(1))
                contenido = [dia_con_texto.group(2)] if dia_con_texto else []
            elif dia_actual is not None:
                contenido.append(linea)
        if dia_actual is not None and contenido:
            celdas.append((dia_actual, " ".join(contenido)))
        return celdas

    def _extraer_eventos(self, resultado, paginas, meses_por_pagina):
        vistos = set()
        for pagina, contenido in paginas:
            mes_anio = meses_por_pagina.get(pagina)
            lineas = [_compactar(linea) for linea in contenido.splitlines() if linea.strip()]
            # Phase 1: explicit dates remain authoritative and isolated from
            # adjacent entries in the PDF reading order.
            for linea in lineas:
                clasificacion = self._clasificar_evento(linea)
                if not clasificacion:
                    continue
                fechas = _fechas_linea(linea)
                if fechas:
                    inicio, fin = fechas[0], fechas[1] if len(fechas) > 1 else None
                else:
                    continue
                clave = (inicio, fin, clasificacion, _normalizar(linea)[:80])
                if clave in vistos:
                    continue
                vistos.add(clave)
                resultado.eventos.append(EventoExtraido(
                    fecha_inicio=inicio, fecha_fin=fin, clasificacion=clasificacion,
                    tipo=self._tipo_evento(linea, clasificacion),
                    descripcion=linea[:255], evidencia=Evidencia(linea[:600], pagina, 0.94),
                ))
            # Phase 2: rebuild calendar cells whose day and description were
            # emitted on separate lines by pypdf.
            if not mes_anio:
                continue
            for dia, texto_celda in self._celdas_pagina(lineas):
                clasificacion = self._clasificar_evento(texto_celda)
                if not clasificacion:
                    continue
                if (
                    clasificacion == "VACACIONES"
                    and "semana santa" in _normalizar(texto_celda)
                    and "vacacion" not in _normalizar(texto_celda)
                    and len(texto_celda) > 400
                ):
                    continue
                rango = self._rango_contextual(texto_celda, mes_anio)
                try:
                    inicio = rango[0] if rango else date(mes_anio[1], mes_anio[0], dia)
                except ValueError:
                    continue
                fin = rango[1] if rango else None
                clave = (inicio, fin, clasificacion, _normalizar(texto_celda)[:80])
                if clave in vistos:
                    continue
                vistos.add(clave)
                resultado.eventos.append(EventoExtraido(
                    fecha_inicio=inicio, fecha_fin=fin, clasificacion=clasificacion,
                    tipo=self._tipo_evento(texto_celda, clasificacion),
                    descripcion=texto_celda[:255], evidencia=Evidencia(texto_celda[:600], pagina, 0.86),
                ))

    def _inferir_periodos_documentados(self, resultado, paginas):
        texto = _compactar(" ".join(contenido for _, contenido in paginas))
        normalizado = _normalizar(texto)
        coincidencia = re.search(
            r"semana santa.{0,120}?(?:[a-z]+\s+)?\((\d{1,2})\)\s+dias laborables",
            normalizado,
        )
        reinicio = next(
            (
                evento for evento in resultado.eventos
                if evento.tipo == "REINICIO_DOCENCIA" and "semana santa" in _normalizar(evento.descripcion)
            ),
            None,
        )
        if not coincidencia or not reinicio:
            return
        cantidad = int(coincidencia.group(1))
        if not 1 <= cantidad <= 10:
            return
        dias = []
        actual = reinicio.fecha_inicio - timedelta(days=1)
        while len(dias) < cantidad:
            if actual.weekday() < 5:
                dias.append(actual)
            actual -= timedelta(days=1)
        inicio, fin = min(dias), max(dias)
        if any(evento.tipo == "SEMANA_SANTA" for evento in resultado.eventos):
            return
        pagina_regla = next(
            (pagina for pagina, contenido in paginas if "semana santa" in _normalizar(contenido) and "dias laborables" in _normalizar(contenido)),
            None,
        )
        evidencia = (
            f"El documento declara {cantidad} días laborables de Semana Santa; "
            f"reinicio detectado el {reinicio.fecha_inicio.isoformat()}."
        )
        resultado.eventos.append(EventoExtraido(
            fecha_inicio=inicio,
            fecha_fin=fin,
            clasificacion="VACACIONES",
            tipo="SEMANA_SANTA",
            descripcion="Semana Santa",
            evidencia=Evidencia(evidencia, pagina_regla, 0.82),
        ))

    def _extraer_feriados_oficiales(self, resultado, paginas):
        if not resultado.anio_inicio or not resultado.anio_fin:
            return
        patron_fecha = re.compile(
            rf"^(?:lunes|martes|miercoles|miércoles|jueves|viernes|sabado|sábado|domingo)\s+"
            rf"(\d{{1,2}})\s+de\s+({NOMBRES_MESES})\b",
            re.I,
        )
        patron_movido = re.compile(
            rf"movido\s+al\s+(?:lunes|martes|miercoles|miércoles|jueves|viernes)\s+"
            rf"(\d{{1,2}})\s+de\s+({NOMBRES_MESES})",
            re.I,
        )
        existentes = {(evento.fecha_inicio, evento.tipo) for evento in resultado.eventos}
        for pagina, contenido in paginas:
            if "dias feriados" not in _normalizar(contenido):
                continue
            lineas = [_compactar(linea) for linea in contenido.splitlines() if linea.strip()]
            if sum(bool(patron_fecha.match(linea)) for linea in lineas) < 3:
                continue
            anio = resultado.anio_inicio
            mes_anterior = None
            indice = 0
            while indice < len(lineas):
                fecha_match = patron_fecha.match(lineas[indice])
                if not fecha_match:
                    indice += 1
                    continue
                dia, mes_texto = fecha_match.groups()
                mes = MESES[_normalizar(mes_texto)]
                if mes_anterior is not None and mes < mes_anterior:
                    anio = resultado.anio_fin
                mes_anterior = mes
                fecha_efectiva = date(anio, mes, int(dia))
                evidencia_lineas = [lineas[indice]]
                indice += 1
                if indice < len(lineas):
                    movido = patron_movido.search(lineas[indice])
                    if movido:
                        dia_movido, mes_movido_texto = movido.groups()
                        mes_movido = MESES[_normalizar(mes_movido_texto)]
                        fecha_efectiva = date(anio, mes_movido, int(dia_movido))
                        evidencia_lineas.append(lineas[indice])
                        indice += 1
                descripcion = lineas[indice] if indice < len(lineas) else "Día feriado"
                evidencia_lineas.append(descripcion)
                clave = (fecha_efectiva, "FERIADO")
                if clave not in existentes:
                    resultado.eventos.append(EventoExtraido(
                        fecha_inicio=fecha_efectiva,
                        fecha_fin=None,
                        clasificacion="FERIADO",
                        tipo="FERIADO",
                        descripcion=descripcion[:255],
                        evidencia=Evidencia(" ".join(evidencia_lineas), pagina, 0.96),
                    ))
                    existentes.add(clave)
                indice += 1
            return
