import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from pypdf import PdfReader

from .recipe_ocr import OCRError, RecipeOCRProvider
from .recipe_units import normalizar_unidad


def _normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto or "") if not unicodedata.combining(c)).upper().strip()


def _decimal(valor):
    texto = str(valor).replace(" ", "")
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+", texto): texto = texto.replace(",", "")
    else: texto = texto.replace(",", ".")
    try: return Decimal(texto)
    except (InvalidOperation, ValueError): return None


@dataclass
class IngredienteExtraido:
    nombre: str
    cantidad: Decimal
    unidad: str
    unidad_original: str = ""
    estado: str = "DETECTADO"


@dataclass
class ResultadoRecetaDocumento:
    nombre: str = ""
    codigo: str = ""
    revision: str = ""
    fecha_actualizacion: object = None
    rendimiento_base: Decimal = None
    unidad_rendimiento: str = ""
    ingredientes: list = field(default_factory=list)
    instrucciones: str = ""
    advertencias: list = field(default_factory=list)
    total: Decimal = None
    columna_base: int = None
    estado: str = "INCOMPLETA"

    def estado_campo(self, campo):
        return "DETECTADO" if getattr(self, campo, None) not in (None, "", []) else "NO_DETECTADO"


@dataclass
class ResultadoDocumentoRecetas:
    formulas: list = field(default_factory=list)
    advertencias: list = field(default_factory=list)
    paginas: int = 0

    def __getattr__(self, nombre):
        if self.formulas and hasattr(self.formulas[0], nombre):
            return getattr(self.formulas[0], nombre)
        raise AttributeError(nombre)


class RecipeDocumentParser:
    MIN_TEXTO_DIGITAL = 25

    def __init__(self, ocr_provider=None): self.ocr_provider = ocr_provider or RecipeOCRProvider()

    def parse_file(self, archivo):
        if archivo.name.lower().endswith(".pdf"): return self.parse_pdf(archivo)
        try: texto = self.ocr_provider.extract_text(archivo)
        except OCRError as exc: return ResultadoDocumentoRecetas(advertencias=[str(exc)])
        resultado = self.parse_text(texto)
        if not resultado.formulas:
            resultado.advertencias.append("No se pudieron interpretar fórmulas válidas en el documento.")
        return resultado

    def parse_pdf(self, archivo):
        lector = PdfReader(archivo)
        paginas = [(p.extract_text() or "") for p in lector.pages]
        texto = "\n".join(paginas)
        if len(texto.strip()) < self.MIN_TEXTO_DIGITAL:
            archivo.seek(0)
            try: texto = self.ocr_provider.extract_text(archivo)
            except OCRError as exc:
                return ResultadoDocumentoRecetas(advertencias=[str(exc)], paginas=len(lector.pages))
        formulas_pagina = []
        for numero, pagina in enumerate(paginas, start=1):
            if not self._es_pagina_formula(pagina):
                continue
            formula = self._parse_formula(pagina)
            if self._requiere_ocr(formula):
                try:
                    archivo.seek(0)
                    texto_ocr = self.ocr_provider.extract_pdf_page(archivo, numero)
                    formula = self._conciliar_formula(formula, self._parse_formula(texto_ocr), numero)
                except OCRError as exc:
                    formula.advertencias.append(f"Página {numero}: {exc}")
                    self._actualizar_estado(formula)
            formulas_pagina.append(formula)
        resultado = ResultadoDocumentoRecetas(formulas=formulas_pagina) if formulas_pagina else self.parse_text(texto)
        if not resultado.formulas and not resultado.advertencias:
            resultado.advertencias.append("No se pudieron interpretar fórmulas válidas en el documento.")
        resultado.paginas = len(lector.pages); return resultado

    @staticmethod
    def _es_pagina_formula(texto):
        normal = _normalizar(texto)
        return "INGREDIENTES" in normal and ("TOTAL" in normal or "CANTIDAD EN" in normal)

    def parse_text(self, texto):
        formulas = []
        for bloque in self._separar_formulas(texto):
            if not bloque.strip():
                continue
            formula = self._parse_formula(bloque)
            if formula.nombre and formula.ingredientes:
                formulas.append(formula)
        return ResultadoDocumentoRecetas(formulas=formulas)

    @staticmethod
    def _requiere_ocr(formula):
        return any(valor in (None, "", []) for valor in (
            formula.nombre, formula.ingredientes, formula.columna_base,
            formula.total, formula.rendimiento_base,
        ))

    def _conciliar_formula(self, digital, ocr, pagina):
        discrepancia = False
        campos = ("nombre", "codigo", "revision", "fecha_actualizacion", "rendimiento_base",
                  "unidad_rendimiento", "total", "columna_base")
        for campo in campos:
            original, reconocido = getattr(digital, campo), getattr(ocr, campo)
            if original in (None, "") and reconocido not in (None, ""):
                setattr(digital, campo, reconocido)
            elif original not in (None, "") and reconocido not in (None, ""):
                iguales = _normalizar(str(original)) == _normalizar(str(reconocido))
                if not iguales:
                    discrepancia = True
                    digital.advertencias.append(
                        f"Página {pagina}: discrepancia entre texto digital y OCR en {campo}; se conservó el valor digital."
                    )
        if not digital.ingredientes and ocr.ingredientes:
            digital.ingredientes = ocr.ingredientes
        elif digital.ingredientes and ocr.ingredientes:
            firma_digital = [( _normalizar(i.nombre), i.cantidad, i.unidad) for i in digital.ingredientes]
            firma_ocr = [(_normalizar(i.nombre), i.cantidad, i.unidad) for i in ocr.ingredientes]
            if firma_digital != firma_ocr:
                discrepancia = True
                digital.advertencias.append(
                    f"Página {pagina}: el OCR discrepa de los ingredientes digitales; se conservaron los datos digitales."
                )
        digital.advertencias.extend(a for a in ocr.advertencias if a not in digital.advertencias)
        self._actualizar_estado(digital)
        if discrepancia:
            digital.estado = "REVISAR"
        return digital

    @staticmethod
    def _actualizar_estado(resultado):
        faltantes = not resultado.nombre or not resultado.codigo or not resultado.rendimiento_base or not resultado.ingredientes
        ambiguo = bool(resultado.advertencias) or any(i.estado == "REVISAR" for i in resultado.ingredientes)
        resultado.estado = "INCOMPLETA" if faltantes else ("REVISAR" if ambiguo else "LISTA")

    def _separar_formulas(self, texto):
        lineas = [x.strip() for x in texto.replace("\r", "\n").split("\n") if x.strip()]
        bloques, actual = [], []
        for linea in lineas:
            if re.search(r"(?:PRODUCTO|NOMBRE\s+DEL\s+PRODUCTO)\s*:|FORMULACION(?:\s+DE)?\s+\S", _normalizar(linea)) and actual:
                bloques.append("\n".join(actual)); actual = []
            actual.append(linea)
        if actual: bloques.append("\n".join(actual))
        return bloques or [texto]

    def _parse_formula(self, texto):
        r = ResultadoRecetaDocumento(); lineas = [x.strip() for x in texto.splitlines() if x.strip()]
        lineas = self._unir_lineas_tabla(lineas)
        for linea in lineas:
            n = _normalizar(linea)
            if n.startswith(("PRODUCTO:", "NOMBRE DEL PRODUCTO:")): r.nombre = linea.split(":", 1)[1].strip()
            elif "FORMULACION" in n:
                match = re.search(r"formulaci[oó]n(?:\s+de)?\s*:?\s*(.+)$", linea, re.I)
                if match and match.group(1).strip(): r.nombre = match.group(1).strip(" :.")
            elif n.startswith("CODIGO:"): r.codigo = linea.split(":", 1)[1].strip()
            elif n.startswith("REVISION:"):
                r.revision = re.split(r"\s*P(?:A|Á)GINA\s*:", linea.split(":", 1)[1], flags=re.I)[0].strip()
            elif n.startswith("FECHA:"):
                valor = linea.split(":", 1)[1].strip()
                for formato in ("%d/%m/%Y", "%Y-%m-%d"):
                    try: r.fecha_actualizacion = datetime.strptime(valor, formato).date(); break
                    except ValueError: pass
        if not r.nombre:
            r.nombre = self._nombre_al_final(lineas)
        filas = self._filas_tabla(lineas)
        harina = next((f for f in filas if re.search(r"\bHARINA(?:\s+DE\s+TRIGO)?\b", _normalizar(f[0]))), None)
        if filas and harina and len(harina[1]) > 1:
            validas = self._columnas_validas(filas)
            candidatas = validas or list(range(len(harina[1])))
            indice = max(candidatas, key=lambda i: harina[1][i] if i < len(harina[1]) and harina[1][i] is not None else Decimal("-1")); r.columna_base = indice
            for descartada in sorted(set(range(len(harina[1]))) - set(validas)):
                if harina[1][descartada] > harina[1][indice]:
                    r.advertencias.append(f"Valor de harina inconsistente en columna {descartada + 1}: {harina[1][descartada]} lb; se excluyó de la selección base.")
            for nombre, valores, unidad in filas:
                normal = _normalizar(nombre); valor = valores[indice] if indice < len(valores) else None
                if normal.startswith("TOTAL"): r.total = valor; continue
                if normal.startswith("CANTIDAD EN UNIDADES"): r.rendimiento_base = valor; r.unidad_rendimiento = "unidad"; continue
                if valor is not None:
                    canon = normalizar_unidad(unidad)
                    r.ingredientes.append(IngredienteExtraido(nombre, valor, canon, unidad, "DETECTADO" if canon else "REVISAR"))
        else:
            self._parse_lineal(lineas, r)
            if filas and not harina: r.advertencias.append("No se identificó inequívocamente una fila de harina; revise la escala base.")
        self._actualizar_estado(r)
        return r

    def _filas_tabla(self, lineas):
        filas = []
        for linea in lineas:
            partes = [p.strip() for p in re.split(r"\s*[|;\t]\s*", linea)]
            unidad, valores = "", []
            if len(partes) >= 3:
                nombre = partes[0]
                for parte in partes[1:]:
                    m = re.fullmatch(r"([0-9][0-9.,]*)\s*([A-Za-zÁÉÍÓÚáéíóú]+)?", parte)
                    if m: valores.append(_decimal(m.group(1))); unidad = unidad or (m.group(2) or "")
            else:
                numeros = list(re.finditer(r"(?<!\w)[0-9][0-9.,]*(?!\w)", linea))
                if len(numeros) < 2: continue
                nombre = linea[:numeros[0].start()].strip(" :")
                valores = [_decimal(m.group()) for m in numeros]
            if _normalizar(nombre).startswith((
                "PRODUCTO", "NOMBRE DEL PRODUCTO", "CODIGO", "REVISION", "FECHA", "PAGINA", "FIRMA"
            )):
                continue
            if len(valores) >= 2: filas.append((nombre, valores, unidad or "lb"))
        return filas

    @staticmethod
    def _unir_lineas_tabla(lineas):
        salida, indice = [], 0
        while indice < len(lineas):
            if _normalizar(lineas[indice]) == "CANTIDAD EN" and indice + 1 < len(lineas):
                salida.append(f"{lineas[indice]} {lineas[indice + 1]}"); indice += 2
            else:
                salida.append(lineas[indice]); indice += 1
        return salida

    @staticmethod
    def _nombre_al_final(lineas):
        posicion = next((i for i, linea in enumerate(lineas) if _normalizar(linea).startswith("CANTIDAD EN UNIDADES")), -1)
        if posicion >= 0:
            for linea in reversed(lineas[posicion + 1:]):
                normal = _normalizar(linea)
                if normal and not re.search(r"\d", linea) and "FORMULACIONES Y PROCEDIMIENTOS" not in normal:
                    return linea.strip(" :.")
        return ""

    @staticmethod
    def _columnas_validas(filas):
        total = next((valores for nombre, valores, _ in filas if _normalizar(nombre).startswith("TOTAL")), None)
        ingredientes = [valores for nombre, valores, _ in filas if not _normalizar(nombre).startswith(("TOTAL", "CANTIDAD EN UNIDADES"))]
        if not total or not ingredientes: return list(range(max((len(v) for v in ingredientes), default=0)))
        validas = []
        for indice, esperado in enumerate(total):
            valores = [fila[indice] for fila in ingredientes if indice < len(fila) and fila[indice] is not None]
            if valores and abs(sum(valores, Decimal("0")) - esperado) <= max(Decimal("0.15"), esperado * Decimal("0.015")):
                validas.append(indice)
        return validas

    def _parse_lineal(self, lineas, r):
        administrativos = ("PRODUCTO", "NOMBRE DEL PRODUCTO", "CODIGO", "REVISION", "FECHA", "PAGINA", "TOTAL", "FIRMA")
        patron = re.compile(r"^(.+?)\s+([0-9]+(?:[.,][0-9]+)?)\s+([A-Za-zÁÉÍÓÚáéíóú]+)$")
        for linea in lineas:
            n = _normalizar(linea)
            if n.startswith("RENDIMIENTO"):
                m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s+([A-Za-zÁÉÍÓÚáéíóú]+)", linea)
                if m: r.rendimiento_base = _decimal(m.group(1)); r.unidad_rendimiento = normalizar_unidad(m.group(2))
                continue
            if n.startswith(administrativos): continue
            m = patron.match(linea)
            if m:
                unidad = normalizar_unidad(m.group(3))
                r.ingredientes.append(IngredienteExtraido(m.group(1).strip(), _decimal(m.group(2)), unidad, m.group(3), "DETECTADO" if unidad else "REVISAR"))
