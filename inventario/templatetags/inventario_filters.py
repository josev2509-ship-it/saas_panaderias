from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def cantidad(valor):
    try:
        numero = Decimal(valor)
        if numero == numero.to_integral():
            return f"{int(numero):,}"
        return f"{numero:,.2f}"
    except Exception:
        return valor


@register.filter
def dinero(valor):
    try:
        numero = Decimal(valor)
        return f"RD$ {numero:,.2f}"
    except Exception:
        return valor


@register.filter
def porcentaje(valor):
    try:
        numero = Decimal(valor)
        if numero == numero.to_integral():
            return f"{int(numero)}%"
        return f"{numero:.2f}%"
    except Exception:
        return valor