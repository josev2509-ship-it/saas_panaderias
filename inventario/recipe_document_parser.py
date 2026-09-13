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
    try: return Decimal(str(valor).replace(" ", "").replace(",", "."))
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
        return self.parse_text(texto)

    def parse_pdf(self, archivo):
        lector = PdfReader(archivo)
        texto = "\n".join((p.extract_text() or "") for p in lector.pages)
        if len(texto.strip()) < self.MIN_TEXTO_DIGITAL:
            archivo.seek(0)
            try: texto = self.ocr_provider.extract_text(archivo)
            except OCRError as exc:
                return ResultadoDocumentoRecetas(advertencias=[str(exc)], paginas=len(lector.pages))
        resultado = self.parse_text(texto); resultado.paginas = len(lector.pages); return resultado

    def parse_text(self, texto):
        formulas = [self._parse_formula(b) for b in self._separar_formulas(texto) if b.strip()]
        return ResultadoDocumentoRecetas(formulas=formulas)

    def _separar_formulas(self, texto):
        lineas = [x.strip() for x in texto.replace("\r", "\n").split("\n") if x.strip()]
        bloques, actual = [], []
        for linea in lineas:
            if re.match(r"^(?:PRODUCTO|NOMBRE\s+DEL\s+PRODUCTO)\s*:", _normalizar(linea)) and actual:
                bloques.append("\n".join(actual)); actual = []
            actual.append(linea)
        if actual: bloques.append("\n".join(actual))
        return bloques or [texto]

    def _parse_formula(self, texto):
        r = ResultadoRecetaDocumento(); lineas = [x.strip() for x in texto.splitlines() if x.strip()]
        for linea in lineas:
            n = _normalizar(linea)
            if n.startswith(("PRODUCTO:", "NOMBRE DEL PRODUCTO:")): r.nombre = linea.split(":", 1)[1].strip()
            elif n.startswith("CODIGO:"): r.codigo = linea.split(":", 1)[1].strip()
            elif n.startswith("REVISION:"):
                r.revision = re.split(r"\s*P(?:A|Á)GINA\s*:", linea.split(":", 1)[1], flags=re.I)[0].strip()
            elif n.startswith("FECHA:"):
                valor = linea.split(":", 1)[1].strip()
                for formato in ("%d/%m/%Y", "%Y-%m-%d"):
                    try: r.fecha_actualizacion = datetime.strptime(valor, formato).date(); break
                    except ValueError: pass
        filas = self._filas_tabla(lineas)
        harina = next((f for f in filas if re.search(r"\bHARINA(?:\s+DE\s+TRIGO)?\b", _normalizar(f[0]))), None)
        if filas and harina and len(harina[1]) > 1:
            indice = max(range(len(harina[1])), key=lambda i: harina[1][i] if harina[1][i] is not None else Decimal("-1")); r.columna_base = indice
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
        faltantes = not r.nombre or not r.codigo or not r.rendimiento_base or not r.ingredientes
        ambiguo = bool(r.advertencias) or any(i.estado == "REVISAR" for i in r.ingredientes)
        r.estado = "INCOMPLETA" if faltantes else ("REVISAR" if ambiguo else "LISTA")
        return r

    def _filas_tabla(self, lineas):
        filas = []
        for linea in lineas:
            partes = [p.strip() for p in re.split(r"\s*[|;\t]\s*", linea)]
            if len(partes) < 3: continue
            nombre, unidad, valores = partes[0], "", []
            for parte in partes[1:]:
                m = re.fullmatch(r"([0-9]+(?:[.,][0-9]+)?)\s*([A-Za-zÁÉÍÓÚáéíóú]+)?", parte)
                if m: valores.append(_decimal(m.group(1))); unidad = unidad or (m.group(2) or "")
            if len(valores) >= 2: filas.append((nombre, valores, unidad or "lb"))
        return filas

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
