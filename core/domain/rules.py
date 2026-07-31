from decimal import Decimal

import hashlib
import json
import re

from .exceptions import BusinessRuleViolation, UnsafePayloadError

SENSITIVE_KEYS = {"password", "contraseña", "token", "secret", "authorization", "archivo", "file"}


def positive_decimal(value, field="cantidad"):
    value = Decimal(value or 0)
    if value <= 0:
        raise BusinessRuleViolation(f"{field.capitalize()} debe ser mayor que cero.")
    return value


def non_negative_decimal(value, field="cantidad"):
    value = Decimal(value or 0)
    if value < 0:
        raise BusinessRuleViolation(f"{field.capitalize()} no puede ser negativa.")
    return value


def free_quantity(available, reserved):
    value = Decimal(available or 0) - Decimal(reserved or 0)
    return max(value, Decimal("0"))


def net_quantity(produced, rejected):
    value = Decimal(produced or 0) - Decimal(rejected or 0)
    if value < 0:
        raise BusinessRuleViolation("La cantidad neta no puede ser negativa.")
    return value


def format_number(prefix, year, number, length=6):
    validate_prefix(prefix)
    validate_document_length(length)
    if number <= 0:
        raise BusinessRuleViolation("La configuracion de numeracion no es valida.")
    return f"{prefix}-{year}-{number:0{length}d}"


def validate_consumption(quantity, available, reserved):
    quantity = positive_decimal(quantity)
    if quantity > Decimal(available) or quantity > Decimal(reserved):
        raise BusinessRuleViolation("El consumo supera la disponibilidad o reserva.")
    return quantity


def validate_return(quantity, consumed, returned):
    quantity = positive_decimal(quantity)
    if quantity > Decimal(consumed) - Decimal(returned):
        raise BusinessRuleViolation("La devolucion supera lo consumido.")
    return quantity


def validate_sufficient_balance(balance, quantity):
    if Decimal(balance) < positive_decimal(quantity):
        raise BusinessRuleViolation("Saldo insuficiente.")


def normalize_idempotency_key(value):
    value = re.sub(r"\s+", "-", str(value or "").strip().lower())
    if not value or len(value) > 180:
        raise BusinessRuleViolation("La clave idempotente no es valida.")
    return value


def validate_safe_payload(payload):
    def walk(value):
        if hasattr(value, "_meta") or hasattr(value, "read"):
            raise UnsafePayloadError("El payload contiene un objeto no permitido.")
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key).lower() in SENSITIVE_KEYS:
                    raise UnsafePayloadError("El payload contiene informacion sensible.")
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
        elif not isinstance(value, (str, int, float, bool, type(None))):
            raise UnsafePayloadError("El payload contiene un valor no serializable.")
    walk(payload)
    try:
        json.dumps(payload, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise UnsafePayloadError("El payload no es serializable.") from exc
    return payload


def idempotency_hash(payload):
    validate_safe_payload(payload or {})
    encoded = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def validate_prefix(prefix):
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", str(prefix or "")):
        raise BusinessRuleViolation("El prefijo documental no es valido.")
    return prefix


def validate_document_length(length):
    if not 3 <= int(length) <= 12:
        raise BusinessRuleViolation("La longitud documental debe estar entre 3 y 12.")
    return int(length)
