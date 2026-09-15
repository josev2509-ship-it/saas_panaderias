import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from types import SimpleNamespace

from .models import ProductoInventario


def normalizar_nombre(valor):
    valor = str(valor or "").replace("\ufffd", "")
    texto = "".join(
        c for c in unicodedata.normalize("NFD", valor.casefold())
        if unicodedata.category(c) != "Mn"
    )
    return " ".join("".join(c if c.isalnum() else " " for c in texto).split())


PALABRAS_FUNCIONALES = {"de", "del", "la", "el", "con", "y", "o", "en", "agua", "formulacion"}


def _singular(token):
    if len(token) > 4 and token.endswith("es") and token[-3] not in "aeiou": return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("is"): return token[:-1]
    return token


def terminos_significativos(valor):
    return Counter(_singular(t) for t in normalizar_nombre(valor).split() if t not in PALABRAS_FUNCIONALES)


def _terminos_equivalentes(izquierda, derecha):
    a, b = list(izquierda.elements()), list(derecha.elements())
    if len(a) != len(b): return False
    usados = set()
    for token in a:
        candidato = next((i for i, otro in enumerate(b) if i not in usados and (
            token == otro or SequenceMatcher(None, token, otro).ratio() >= 0.84
        )), None)
        if candidato is None: return False
        usados.add(candidato)
    return True


def _clasificar(nombre, productos):
    normal = normalizar_nombre(nombre)
    exactos = [p for p in productos if normalizar_nombre(p.nombre) == normal]
    if len(exactos) == 1:
        p = exactos[0]; return ResultadoMatching(nombre, "EXACTA_NORMALIZADA", p.pk, p.nombre)
    terminos = terminos_significativos(nombre)
    altos = [p for p in productos if terminos and _terminos_equivalentes(terminos, terminos_significativos(p.nombre))]
    if not altos and terminos:
        altos = [p for p in productos if (
            (lambda otros: otros and (
                not (terminos - otros) or not (otros - terminos)
            ) and sum((terminos & otros).values()) / max(sum((terminos | otros).values()), 1) >= 0.60)(
                terminos_significativos(p.nombre)
            )
        )]
    if len(altos) == 1:
        p = altos[0]; return ResultadoMatching(nombre, "ALTA_CONFIANZA", p.pk, p.nombre)
    candidatos = []
    for p in productos:
        otros = terminos_significativos(p.nombre)
        comunes = sum((terminos & otros).values())
        total = sum((terminos | otros).values())
        if comunes and (comunes / total >= 0.30 or comunes >= 2): candidatos.append(p)
    candidatos = altos or candidatos
    if candidatos:
        return ResultadoMatching(nombre, "REVISAR", candidatos=[{"id": p.pk, "nombre": p.nombre} for p in candidatos[:8]])
    return ResultadoMatching(nombre, "SIN_COINCIDENCIA")


@dataclass
class ResultadoMatching:
    texto_detectado: str
    estado: str
    producto_id: int | None = None
    producto_nombre: str = ""
    candidatos: list[dict] = field(default_factory=list)
    concepto_menu: str = ""
    vinculado_inventario: bool = False


def encontrar_ingrediente(*, empresa, nombre):
    productos = list(
        ProductoInventario.objects.filter(empresa=empresa, activo=True)
        .exclude(tipo="producto_terminado")
        .only("id", "nombre")
    )
    return _clasificar(nombre, productos)


def encontrar_producto_terminado(*, empresa, nombre):
    resultado = encontrar_producto_terminado_match(empresa=empresa, nombre=nombre)
    if not resultado.producto_id: return None
    return ProductoInventario.objects.filter(pk=resultado.producto_id, empresa=empresa).first()


def encontrar_producto_terminado_match(*, empresa, nombre):
    productos = list(ProductoInventario.objects.filter(
        empresa=empresa, activo=True, tipo="producto_terminado"
    ).only("id", "nombre"))
    directo = _clasificar(nombre, productos)
    if directo.producto_id:
        directo.vinculado_inventario = True
        return directo

    from conduces.models import MenuDiario
    from .models import VinculoProductoMenu

    conceptos = []
    vistos = set()
    for menu in MenuDiario.objects.filter(empresa=empresa).only("id", "producto"):
        normal = normalizar_nombre(menu.producto)
        if normal and normal not in vistos:
            conceptos.append(SimpleNamespace(pk=menu.pk, nombre=menu.producto))
            vistos.add(normal)
    conceptual = _clasificar(nombre, conceptos)
    if conceptual.estado not in {"EXACTA_NORMALIZADA", "ALTA_CONFIANZA"}:
        return conceptual if conceptual.estado != "SIN_COINCIDENCIA" else directo

    menus = MenuDiario.objects.filter(empresa=empresa, producto__iexact=conceptual.producto_nombre)
    vinculados = list(ProductoInventario.objects.filter(
        vinculoproductomenu__empresa=empresa,
        vinculoproductomenu__menu__in=menus,
        empresa=empresa, activo=True, tipo="producto_terminado",
    ).distinct().only("id", "nombre"))
    if len(vinculados) == 1:
        producto = vinculados[0]
        return ResultadoMatching(
            nombre, conceptual.estado, producto.pk, producto.nombre,
            concepto_menu=conceptual.producto_nombre, vinculado_inventario=True,
        )
    return ResultadoMatching(
        nombre, conceptual.estado, producto_nombre=conceptual.producto_nombre,
        concepto_menu=conceptual.producto_nombre, vinculado_inventario=False,
    )
