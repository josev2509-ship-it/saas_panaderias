import re


def normalizar_identificacion(value):
    """Normaliza sin inferir, completar o inventar información."""
    return re.sub(r"[^A-Z0-9]", "", (value or "").strip().upper())
