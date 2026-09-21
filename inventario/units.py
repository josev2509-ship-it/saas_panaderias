"""Unidades físicas: conversiones Decimal, sin equivalencias masa-volumen."""

import re
import unicodedata
from decimal import Decimal, ROUND_CEILING

from django.core.exceptions import ValidationError


def _key(value):
    value = "".join(c for c in unicodedata.normalize("NFD", str(value or "").lower()) if unicodedata.category(c) != "Mn")
    return " ".join(value.replace("_", " ").strip().split())


ALIASES = {
    "lb": "lb", "lbs": "lb", "libra": "lb", "libras": "lb",
    "oz": "oz", "onza": "oz", "onzas": "oz",
    "kg": "kg", "kgs": "kg", "kilo": "kg", "kilos": "kg", "kilogramo": "kg", "kilogramos": "kg",
    "g": "g", "gr": "g", "gramo": "g", "gramos": "g",
    "l": "litro", "lt": "litro", "litro": "litro", "litros": "litro",
    "ml": "ml", "mililitro": "ml", "mililitros": "ml",
    "fl oz": "fl_oz", "onza liquida": "fl_oz", "onzas liquidas": "fl_oz",
    "gal": "gal_us", "galon": "gal_us", "galones": "gal_us", "gal us": "gal_us",
    "unidad": "unidad", "unidades": "unidad", "ud": "unidad", "uds": "unidad",
    "docena": "docena", "docenas": "docena",
    "yarda": "yarda", "yardas": "yarda",
}
FACTORES = {
    "g": ("masa", Decimal("1")), "kg": ("masa", Decimal("1000")),
    "lb": ("masa", Decimal("453.59237")), "oz": ("masa", Decimal("453.59237") / 16),
    "ml": ("volumen", Decimal("1")), "litro": ("volumen", Decimal("1000")),
    "fl_oz": ("volumen", Decimal("29.5735295625")), "gal_us": ("volumen", Decimal("3785.411784")),
    "unidad": ("conteo", Decimal("1")), "docena": ("conteo", Decimal("12")),
    "yarda": ("longitud", Decimal("1")),
}


def normalizar_unidad(value):
    return ALIASES.get(_key(value), "")


def unidades_compatibles(origen, destino):
    a, b = normalizar_unidad(origen), normalizar_unidad(destino)
    return bool(a and b and FACTORES[a][0] == FACTORES[b][0])


def convertir(cantidad, origen, destino):
    a, b = normalizar_unidad(origen), normalizar_unidad(destino)
    if not unidades_compatibles(a, b):
        raise ValidationError("Unidades incompatibles; requiere equivalencia específica del producto.")
    value = Decimal(str(cantidad))
    if not value.is_finite():
        raise ValidationError("Cantidad inválida.")
    return value * FACTORES[a][1] / FACTORES[b][1]


def sumar(cantidades, destino):
    return sum((convertir(cantidad, unidad, destino) for cantidad, unidad in cantidades), Decimal("0"))


def interpretar_cantidad(texto, destino):
    tokens = re.findall(r"(\d+(?:[.,]\d+)?)\s*([A-Za-z_áéíóúÁÉÍÓÚ]+(?:\s+[A-Za-z_áéíóúÁÉÍÓÚ]+)?)", texto)
    if not tokens or "".join(re.findall(r"[\dA-Za-záéíóúÁÉÍÓÚ]+", texto)).lower() != "".join((n + u).replace(" ", "") for n, u in tokens).lower():
        raise ValidationError("Expresión de cantidad inválida.")
    return sumar(((Decimal(n.replace(",", ".")), u) for n, u in tokens), destino)


def formatear_masa_lb(cantidad):
    value = Decimal(str(cantidad))
    libras = int(value)
    onzas = (value - libras) * 16
    return f"{libras} lb" + (f" {onzas.normalize()} oz" if onzas else "")


def desglosar_empaques(cantidad, contenido):
    cantidad, contenido = Decimal(str(cantidad)), Decimal(str(contenido))
    if contenido <= 0:
        raise ValidationError("La presentación debe ser positiva.")
    completos = int(cantidad // contenido)
    return completos, cantidad - completos * contenido, int((cantidad / contenido).to_integral_value(rounding=ROUND_CEILING))
