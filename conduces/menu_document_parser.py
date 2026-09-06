import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

from pypdf import PdfReader


MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


@dataclass(frozen=True)
class ItemMenuExtraido:
    semana: int
    dia_semana: int
    producto: str
    texto_origen: str = ""
    pagina: int | None = None
    confianza: float = 1.0


@dataclass
class ResultadoExtraccionMenu:
    periodo: str = ""
    anio_inicio: int | None = None
    anio_fin: int | None = None
    codigo_modalidad: str = ""
    codigo_orden: str = ""
    version: str = ""
    vigente_desde: date | None = None
    semanas_ciclo: int = 0
    modalidad: str = ""
    items: list[ItemMenuExtraido] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    confianza: float = 0.0
    texto: str = ""
    paginas: int = 0

    @property
    def completo_regular(self):
        posiciones = {(item.semana, item.dia_semana) for item in self.items}
        return all(
            (semana, dia) in posiciones
            for semana in range(1, 6)
            for dia in range(5)
        )

    @property
    def completo_prepara(self):
        posiciones = {(item.semana, item.dia_semana) for item in self.items}
        return all(
            (semana, dia) in posiciones
            for semana in range(1, 6)
            for dia in (5, 6)
        )

    @property
    def total_esperado(self):
        if self.modalidad == "PREPARA":
            return 10
        return 25

    @property
    def completo(self):
        if self.modalidad == "PREPARA":
            return self.completo_prepara and len(self.items) == 10
        return self.completo_regular and len(self.items) == 25


class LocalMenuPDFProvider:
    nombre = "local_pypdf_menu_deterministic"
    version = "1.1"

    def extract(self, archivo, modalidad=None):
        archivo.seek(0)
        lector = PdfReader(archivo)
        paginas = [
            (numero, pagina.extract_text() or "")
            for numero, pagina in enumerate(lector.pages, start=1)
        ]
        texto = "\n".join(contenido for _, contenido in paginas)

        resultado = ResultadoExtraccionMenu(
            texto=texto,
            paginas=len(paginas),
        )

        if not texto.strip():
            resultado.advertencias.append(
                "El PDF no contiene texto extraible; requiere revision."
            )
            archivo.seek(0)
            return resultado

        self._extraer_metadatos(resultado, texto)

        modalidad_normalizada = (modalidad or "").upper().strip()

        if modalidad_normalizada == "PREPARA":
            resultado.modalidad = "PREPARA"
        elif modalidad_normalizada == "REGULAR":
            resultado.modalidad = "REGULAR"
        else:
            texto_normalizado = self._normalizar(texto)
            if "PREPARA" in texto_normalizado:
                resultado.modalidad = "PREPARA"
            else:
                resultado.modalidad = "REGULAR"

        if resultado.modalidad == "PREPARA":
            self._extraer_items_prepara(resultado, paginas)
        else:
            self._extraer_items_regular(resultado, paginas)

        resultado.semanas_ciclo = max(
            (item.semana for item in resultado.items),
            default=0,
        )

        if resultado.modalidad == "PREPARA":
            if len(resultado.items) != 10:
                resultado.advertencias.append(
                    f"Se detectaron {len(resultado.items)} posiciones de panaderia; se esperaban 10."
                )
            if not resultado.completo_prepara:
                resultado.advertencias.append(
                    "La matriz PREPARA de 5 semanas por sabado y domingo esta incompleta y requiere revision."
                )
        else:
            if len(resultado.items) != 25:
                resultado.advertencias.append(
                    f"Se detectaron {len(resultado.items)} posiciones de panaderia; se esperaban 25."
                )
            if not resultado.completo_regular:
                resultado.advertencias.append(
                    "La matriz de 5 semanas por 5 dias esta incompleta y requiere revision."
                )

        archivo.seek(0)
        return resultado

    def _normalizar(self, texto):
        texto = "".join(
            c
            for c in unicodedata.normalize("NFD", texto.upper())
            if unicodedata.category(c) != "Mn"
        )
        return " ".join(texto.split())

    def _extraer_items_regular(self, resultado, paginas):
        semanas = {
            "SEMANA I": 1,
            "SEMANA II": 2,
            "SEMANA III": 3,
            "SEMANA IV": 4,
            "SEMANA V": 5,
        }

        for pagina, contenido in paginas:
            semana = None
            productos = []
            actual = ""

            for linea in contenido.splitlines():
                linea = linea.strip()
                if not linea:
                    continue

                n = self._normalizar(linea)

                if n in semanas:
                    if semana is not None:
                        if actual:
                            productos.append(actual)
                        self._guardar_semana_regular(
                            resultado,
                            semana,
                            productos,
                            pagina,
                        )

                    semana = semanas[n]
                    productos = []
                    actual = ""
                    continue

                if semana is None:
                    continue

                if n.startswith("NOTAS"):
                    if actual:
                        productos.append(actual)

                    self._guardar_semana_regular(
                        resultado,
                        semana,
                        productos,
                        pagina,
                    )

                    semana = None
                    productos = []
                    actual = ""
                    continue

                if n.startswith("LUNES") or n.startswith("DESAYUNO"):
                    continue

                if "/" in linea:
                    if actual:
                        productos.append(actual)
                    actual = linea.split("/", 1)[1].strip()
                elif actual:
                    actual += " " + linea

            if semana is not None:
                if actual:
                    productos.append(actual)

                self._guardar_semana_regular(
                    resultado,
                    semana,
                    productos,
                    pagina,
                )

    def _guardar_semana_regular(
        self,
        resultado,
        semana,
        productos,
        pagina,
    ):
        for dia_semana, producto in enumerate(productos[:5]):
            producto = " ".join(producto.split())

            resultado.items.append(
                ItemMenuExtraido(
                    semana=semana,
                    dia_semana=dia_semana,
                    producto=producto,
                    texto_origen=producto,
                    pagina=pagina,
                    confianza=1.0,
                )
            )

    def _extraer_items_prepara(self, resultado, paginas):
        texto = " ".join(contenido for _, contenido in paginas)
        compacto = " ".join(texto.split())

        productos = re.findall(
            r"Leche\s+(?:con\s+chocolate|blanca)\s*/\s*(Pan|Galleta\s+de\s+avena)",
            compacto,
            re.I,
        )
        productos = [" ".join(producto.split()) for producto in productos]

        if len(productos) < 10:
            resultado.advertencias.append(
                f"No se detectaron suficientes productos PREPARA. Se encontraron {len(productos)} de 10."
            )
            return

        bloques = [
            productos[i:i + 10]
            for i in range(0, len(productos), 10)
            if len(productos[i:i + 10]) == 10
        ]

        referencia = bloques[0]
        referencia_norm = [self._normalizar(x) for x in referencia]

        for bloque in bloques[1:]:
            if [self._normalizar(x) for x in bloque] != referencia_norm:
                resultado.advertencias.append(
                    "Los ciclos repetidos del documento PREPARA contienen productos diferentes."
                )
                return

        for semana, producto in enumerate(referencia[:5], start=1):
            resultado.items.append(
                ItemMenuExtraido(
                    semana=semana,
                    dia_semana=5,
                    producto=producto,
                    texto_origen=producto,
                    pagina=1,
                    confianza=1.0,
                )
            )

        for semana, producto in enumerate(referencia[5:10], start=1):
            resultado.items.append(
                ItemMenuExtraido(
                    semana=semana,
                    dia_semana=6,
                    producto=producto,
                    texto_origen=producto,
                    pagina=1,
                    confianza=1.0,
                )
            )

    def _extraer_metadatos(self, resultado, texto):
        normalizado = "".join(
            c
            for c in unicodedata.normalize("NFD", texto.lower())
            if unicodedata.category(c) != "Mn"
        )
        compacto = " ".join(normalizado.split())

        periodo = re.search(
            r"ano\s+escolar\s*:?\s*(20\d{2})\s*[-/]\s*(20\d{2})",
            compacto,
            re.I,
        )
        if periodo:
            resultado.anio_inicio = int(periodo.group(1))
            resultado.anio_fin = int(periodo.group(2))
            resultado.periodo = f"{resultado.anio_inicio}-{resultado.anio_fin}"
        else:
            resultado.advertencias.append("No se detecto el periodo escolar.")

        modalidad = re.search(
            r"c.digo\s+de\s+modalidad\s*:?\s*(.*?)\s+c.digo\s+de\s+orden",
            compacto,
            re.I,
        )
        if modalidad:
            codigo = re.sub(r"\s*-\s*", "-", modalidad.group(1).strip())
            resultado.codigo_modalidad = codigo.upper()
        else:
            resultado.advertencias.append("No se detecto el codigo de modalidad.")

        orden = re.search(
            r"c.digo\s+de\s+orden\s*:?\s*([a-z0-9-]+)",
            compacto,
            re.I,
        )
        if orden:
            resultado.codigo_orden = orden.group(1).upper()

        # La versión suele aparecer en la misma línea del encabezado
        # "MENÚ CÍCLICO", aunque PyPDF puede insertar espacios o texto
        # intermedio. Se limita la búsqueda a la línea para evitar tomar
        # versiones que pertenezcan a otra sección del documento.
        version = re.search(
            r"menu\s+ciclico[^\n]{0,160}?\b(v\d+)\b",
            normalizado,
            re.I,
        )

        # Fallback para PDFs cuyo extractor separa el encabezado y la
        # versión mediante un salto de línea.
        if not version:
            version = re.search(
                r"menu\s+ciclico[\s\S]{0,160}?\b(v\d+)\b",
                normalizado,
                re.I,
            )

        if version:
            resultado.version = version.group(1).upper()

        vigencia = re.search(
            r"vie?gente\s+desde\s*:?\s*([a-z]+)\s+(20\d{2})",
            compacto,
            re.I,
        )
        if vigencia:
            mes = MESES.get(vigencia.group(1))
            if mes:
                resultado.vigente_desde = date(int(vigencia.group(2)), mes, 1)

        if not resultado.vigente_desde:
            resultado.advertencias.append(
                "No se detecto la fecha de vigencia del menu."
            )

