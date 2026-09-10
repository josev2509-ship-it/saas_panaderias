"""Contexto global del Enterprise Shell."""

from .services import obtener_empresa_usuario


def empresa_activa(request):
    """Mantiene tenant y módulos del sidebar en todas las vistas autenticadas."""
    return {"empresa": obtener_empresa_usuario(request)}

# ============================================================
# CONTEXTO GLOBAL - MODO SOPORTE SASTRE
# ============================================================

def contexto_soporte_sastre(request):
    """
    Expone de forma segura el contexto temporal de soporte
    a todas las plantillas del ERP.
    """
    from .tenant_context import es_soporte_sastre, obtener_contexto_soporte

    try:
        contexto = obtener_contexto_soporte(
            request
        )
    except Exception:
        contexto = None

    return {
        "modo_soporte_sastre": bool(contexto),
        "soporte_contexto": contexto,
        "puede_administrar_empresas": es_soporte_sastre(request.user),
    }
