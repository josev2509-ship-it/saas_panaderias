import base64
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OCRError(RuntimeError): pass
class OCRNoDisponible(OCRError): pass
class OCRFallo(OCRError): pass


@dataclass(frozen=True)
class EstadoOCRLocal:
    tesseract_disponible: bool
    idioma_disponible: bool
    poppler_disponible: bool
    comando_tesseract: str = ""

    @property
    def disponible(self):
        return self.tesseract_disponible and self.idioma_disponible and self.poppler_disponible


def verificar_ocr_local(*, lang="spa", tesseract_cmd="", requiere_poppler=True):
    comando = tesseract_cmd or "tesseract"
    ruta_tesseract = shutil.which(comando)
    ruta_poppler = shutil.which("pdftoppm") if requiere_poppler else "no-requerido"
    idioma_disponible = False
    if ruta_tesseract:
        try:
            resultado = subprocess.run(
                [ruta_tesseract, "--list-langs"], capture_output=True, text=True,
                timeout=10, check=False,
            )
            idiomas = {linea.strip() for linea in resultado.stdout.splitlines() if linea.strip()}
            idioma_disponible = resultado.returncode == 0 and lang in idiomas
        except (OSError, subprocess.SubprocessError):
            idioma_disponible = False
    return EstadoOCRLocal(bool(ruta_tesseract), idioma_disponible, bool(ruta_poppler), ruta_tesseract or "")


class RecipeOCRProvider:
    """Contrato OCR y fábrica configurable para el importador de recetas."""
    def extract_text(self, archivo):
        proveedor = os.getenv("RECIPE_OCR_PROVIDER", "local").strip().lower()
        if proveedor in {"local", "tesseract"}:
            return LocalTesseractRecipeOCRProvider.from_environment().extract_text(archivo)
        if proveedor in {"azure", "azure_document_intelligence"}:
            return AzureDocumentIntelligenceProvider.from_environment().extract_text(archivo)
        raise OCRNoDisponible(f"Proveedor OCR no soportado: {proveedor}.")


class LocalTesseractRecipeOCRProvider(RecipeOCRProvider):
    def __init__(self, *, lang="spa", dpi=300, tesseract_cmd=""):
        self.lang = lang; self.dpi = dpi; self.tesseract_cmd = tesseract_cmd

    @classmethod
    def from_environment(cls):
        return cls(
            lang=os.getenv("RECIPE_OCR_LANG", "spa").strip() or "spa",
            dpi=int(os.getenv("RECIPE_OCR_DPI", "300")),
            tesseract_cmd=os.getenv("TESSERACT_CMD", "").strip(),
        )

    def extract_text(self, archivo):
        try:
            import pytesseract
            from PIL import Image, ImageOps
            es_pdf = archivo.name.lower().endswith(".pdf")
            estado = verificar_ocr_local(lang=self.lang, tesseract_cmd=self.tesseract_cmd, requiere_poppler=es_pdf)
            faltantes = []
            if not estado.tesseract_disponible: faltantes.append("binario tesseract")
            if estado.tesseract_disponible and not estado.idioma_disponible: faltantes.append(f"idioma {self.lang}")
            if es_pdf and not estado.poppler_disponible: faltantes.append("binario pdftoppm/Poppler")
            if faltantes: raise OCRNoDisponible(f"OCR local no disponible: falta {', '.join(faltantes)}.")
            if self.tesseract_cmd: pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            archivo.seek(0); contenido = archivo.read(); archivo.seek(0)
            if es_pdf:
                try:
                    from pdf2image import convert_from_bytes
                    imagenes = convert_from_bytes(contenido, dpi=self.dpi, fmt="png")
                except Exception as exc:
                    raise OCRFallo(f"No se pudo rasterizar el PDF para OCR local: {exc}") from exc
            else:
                imagenes = [Image.open(archivo)]
            paginas = []
            for imagen in imagenes:
                preparada = ImageOps.autocontrast(ImageOps.grayscale(imagen))
                datos = pytesseract.image_to_data(
                    preparada, lang=self.lang, config="--oem 3 --psm 6",
                    output_type=pytesseract.Output.DICT,
                )
                paginas.append(self._texto_desde_datos(datos))
            texto = "\n".join(p for p in paginas if p.strip())
            if not texto: raise OCRFallo("OCR local finalizó sin texto reconocible.")
            return texto
        except OCRError: raise
        except ImportError as exc:
            raise OCRNoDisponible("OCR local no instalado: se requieren pytesseract, pdf2image, Tesseract y Poppler.") from exc
        except Exception as exc:
            raise OCRFallo(f"OCR local no pudo reconocer el documento: {exc}") from exc

    @classmethod
    def _texto_desde_datos(cls, datos):
        lineas = {}
        textos = datos.get("text", [])
        for indice, texto in enumerate(textos):
            texto = str(texto or "").strip()
            try: confianza = float(datos.get("conf", [])[indice])
            except (ValueError, TypeError, IndexError): confianza = -1
            if not texto or confianza < 0: continue
            clave = tuple(datos.get(campo, [0] * len(textos))[indice] for campo in ("page_num", "block_num", "par_num", "line_num"))
            lineas.setdefault(clave, []).append((int(datos.get("left", [0] * len(textos))[indice]), texto))
        return "\n".join(cls._reconstruir_linea(sorted(palabras)) for _, palabras in sorted(lineas.items()))

    @staticmethod
    def _reconstruir_linea(palabras):
        tokens = [texto for _, texto in palabras]
        primero_numerico = next((i for i, token in enumerate(tokens) if token[:1].isdigit()), None)
        if primero_numerico is None or primero_numerico == 0:
            return " ".join(tokens)
        nombre = " ".join(tokens[:primero_numerico]); celdas, actual = [], []
        for token in tokens[primero_numerico:]:
            if token[:1].isdigit() and actual:
                celdas.append(" ".join(actual)); actual = [token]
            else: actual.append(token)
        if actual: celdas.append(" ".join(actual))
        return " | ".join([nombre, *celdas]) if len(celdas) > 1 else " ".join(tokens)


class AzureDocumentIntelligenceProvider(RecipeOCRProvider):
    API_VERSION = "2024-11-30"

    def __init__(self, endpoint, key, *, transport=None, poll_interval=0.25, max_polls=120):
        self.endpoint = endpoint.rstrip("/"); self.key = key
        self.transport = transport or self._http
        self.poll_interval = poll_interval; self.max_polls = max_polls

    @classmethod
    def from_environment(cls):
        endpoint = os.getenv("RECIPE_OCR_ENDPOINT", "").strip(); key = os.getenv("RECIPE_OCR_KEY", "").strip()
        if not endpoint or not key:
            raise OCRNoDisponible("OCR Azure seleccionado, pero faltan RECIPE_OCR_ENDPOINT o RECIPE_OCR_KEY.")
        return cls(endpoint, key)

    def extract_text(self, archivo):
        archivo.seek(0); contenido = archivo.read(); archivo.seek(0)
        url = (f"{self.endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze"
               f"?_overload=analyzeDocument&api-version={self.API_VERSION}")
        cuerpo = json.dumps({"base64Source": base64.b64encode(contenido).decode("ascii")}).encode("utf-8")
        try:
            estado, cabeceras, _ = self.transport("POST", url, self._headers(), cuerpo)
            operacion = cabeceras.get("Operation-Location") or cabeceras.get("operation-location")
            if estado != 202 or not operacion: raise OCRFallo("OCR Azure no aceptó el documento para análisis.")
            for _ in range(self.max_polls):
                estado, _, respuesta = self.transport("GET", operacion, self._headers(), None)
                if estado != 200: raise OCRFallo("OCR Azure no pudo consultar el resultado.")
                estado_ocr = respuesta.get("status", "").lower()
                if estado_ocr == "succeeded": return self._texto_estructurado(respuesta.get("analyzeResult", {}))
                if estado_ocr in {"failed", "canceled"}: raise OCRFallo("OCR Azure no pudo reconocer el documento.")
                time.sleep(self.poll_interval)
            raise OCRFallo("OCR Azure excedió el tiempo máximo de procesamiento.")
        except OCRError: raise
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
            raise OCRFallo(f"OCR Azure no está disponible: {exc}") from exc

    def _headers(self):
        return {"Ocp-Apim-Subscription-Key": self.key, "Content-Type": "application/json"}

    @staticmethod
    def _texto_estructurado(resultado):
        texto = (resultado.get("content") or "").strip(); lineas_tabla = []
        for tabla in resultado.get("tables", []):
            filas = {}
            for celda in tabla.get("cells", []):
                fila = int(celda.get("rowIndex", 0)); columna = int(celda.get("columnIndex", 0))
                filas.setdefault(fila, {})[columna] = str(celda.get("content", "")).strip()
            for fila in sorted(filas):
                ultima = max(filas[fila], default=-1)
                lineas_tabla.append(" | ".join(filas[fila].get(i, "") for i in range(ultima + 1)))
        partes = [p for p in (texto, "\n".join(lineas_tabla)) if p]
        if not partes: raise OCRFallo("OCR finalizó sin texto ni tablas reconocibles.")
        return "\n".join(partes)

    @staticmethod
    def _http(metodo, url, cabeceras, cuerpo):
        solicitud = Request(url, data=cuerpo, headers=cabeceras, method=metodo)
        with urlopen(solicitud, timeout=60) as respuesta:
            datos = respuesta.read()
            return respuesta.status, dict(respuesta.headers.items()), json.loads(datos or b"{}")
