import unicodedata
from dataclasses import dataclass, field

from .models import ProductoInventario


def normalizar_nombre(valor):
    texto = "".join(
        c for c in unicodedata.normalize("NFD", str(valor or "").casefold())
        if unicodedata.category(c) != "Mn"
    )
    return " ".join("".join(c if c.isalnum() else " " for c in texto).split())


@dataclass
class ResultadoMatching:
    texto_detectado: str
    estado: str
    producto_id: int | None = None
    producto_nombre: str = ""
    candidatos: list[dict] = field(default_factory=list)


def encontrar_ingrediente(*, empresa, nombre):
    objetivo = normalizar_nombre(nombre)
    productos = list(
        ProductoInventario.objects.filter(empresa=empresa, activo=True)
        .exclude(tipo="producto_terminado")
        .only("id", "nombre")
    )
    exactos = [p for p in productos if normalizar_nombre(p.nombre) == objetivo]
    if len(exactos) == 1:
        producto = exactos[0]
        return ResultadoMatching(nombre, "COINCIDENCIA", producto.pk, producto.nombre)
    candidatos = exactos or [
        p for p in productos
        if objetivo and (objetivo in normalizar_nombre(p.nombre) or normalizar_nombre(p.nombre) in objetivo)
    ]
    if candidatos:
        return ResultadoMatching(
            nombre,
            "REVISAR",
            candidatos=[{"id": p.pk, "nombre": p.nombre} for p in candidatos[:8]],
        )
    return ResultadoMatching(nombre, "SIN_COINCIDENCIA")


def encontrar_producto_terminado(*, empresa, nombre):
    objetivo = normalizar_nombre(nombre)
    productos = list(ProductoInventario.objects.filter(
        empresa=empresa, activo=True, tipo="producto_terminado"
    ).only("id", "nombre"))
    exactos = [p for p in productos if normalizar_nombre(p.nombre) == objetivo]
    return exactos[0] if len(exactos) == 1 else None
