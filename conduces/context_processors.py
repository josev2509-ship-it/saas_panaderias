"""Contexto global del Enterprise Shell."""

from .services import obtener_empresa_usuario


def empresa_activa(request):
    """Mantiene tenant y módulos del sidebar en todas las vistas autenticadas."""
    return {"empresa": obtener_empresa_usuario(request)}
