import unicodedata

UNIDADES_CANONICAS = {
    "kg": "kg",
    "g": "g",
    "lb": "lb",
    "oz": "oz",
    "l": "L",
    "ml": "ml",
    "unidad": "unidad",
}

ALIASES_UNIDADES = {
    "kg": "kg",
    "kgs": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "kilogramo": "kg",
    "kilogramos": "kg",
    "g": "g",
    "gr": "g",
    "grs": "g",
    "gramo": "g",
    "gramos": "g",
    "lb": "lb",
    "lbs": "lb",
    "libra": "lb",
    "libras": "lb",
    "oz": "oz",
    "onza": "oz",
    "onzas": "oz",
    "l": "L",
    "lt": "L",
    "lts": "L",
    "litro": "L",
    "litros": "L",
    "ml": "ml",
    "mililitro": "ml",
    "mililitros": "ml",
    "unidad": "unidad",
    "unidades": "unidad",
    "und": "unidad",
    "uds": "unidad",
}


def _normalizar_texto(valor):
    valor = str(valor or "").strip().lower()
    valor = "".join(
        c for c in unicodedata.normalize("NFD", valor)
        if unicodedata.category(c) != "Mn"
    )
    valor = " ".join("".join(c if c.isalnum() else " " for c in valor).split())
    return valor


def normalizar_unidad(valor):
    texto = _normalizar_texto(valor)
    if not texto:
        return ""
    return ALIASES_UNIDADES.get(texto, "")


def unidad_reconocida(valor):
    return bool(normalizar_unidad(valor))


def opciones_unidad():
    return [(codigo, codigo) for codigo in ("kg", "g", "lb", "oz", "L", "ml", "unidad")]
