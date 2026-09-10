from .models import Empresa



def obtener_empresa_usuario(request):
    """
    Compatibilidad para los módulos que todavía utilizan
    services.obtener_empresa_usuario(request).

    La resolución real vive en tenant_context.
    """
    from .tenant_context import obtener_empresa_request

    return obtener_empresa_request(
        request,
        permitir_soporte=True,
    )
