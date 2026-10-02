from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from conduces.models import PerfilUsuario
from conduces.subscription_service import estado_acceso_modulo_request
from conduces.tenant_context import (
    contexto_soporte_activo,
    empresa_operativa_usuario,
    obtener_empresa_requerida,
    obtener_perfil_saas_usuario,
)


def gestion_humana_requerida(permiso=None):
    """Política tenant-aware compartida por RRHH y Nómina."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            pertenece_soporte = request.user.groups.filter(name="Soporte SASTRE").exists()
            soporte = pertenece_soporte or (
                request.user.is_superuser and empresa_operativa_usuario(request.user) is None
            )
            if soporte and not contexto_soporte_activo(request):
                raise PermissionDenied("El soporte requiere un contexto empresarial activo.")

            empresa = obtener_empresa_requerida(request, permitir_soporte=True)
            if not empresa.activa:
                raise PermissionDenied("La empresa se encuentra inactiva.")

            suscripcion_ok, modulo_ok = estado_acceso_modulo_request(
                request, empresa, "modulo_nomina"
            )
            if not suscripcion_ok or not modulo_ok:
                raise PermissionDenied("Gestión Humana y Nómina no están habilitadas.")

            perfil = None if soporte else obtener_perfil_saas_usuario(request.user)
            administrador = bool(
                (request.user.is_superuser and not soporte)
                or (
                    perfil
                    and perfil.activo
                    and perfil.rol == "admin_empresa"
                    and perfil.empresa_id
                    and perfil.empresa.empresa_operativa_id == empresa.pk
                )
            )
            if not (soporte or administrador or (permiso and request.user.has_perm(permiso))):
                raise PermissionDenied

            request.empresa_operativa = empresa
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def tiene_autorizacion_gestion_humana(request, permiso):
    perfil = obtener_perfil_saas_usuario(request.user)
    empresa = getattr(request, "empresa_operativa", None)
    return bool(
        contexto_soporte_activo(request)
        or (request.user.is_superuser and empresa is not None)
        or (
            perfil and perfil.activo and perfil.rol == "admin_empresa"
            and perfil.empresa_id
            and empresa is not None
            and perfil.empresa.empresa_operativa_id == empresa.pk
        )
        or request.user.has_perm(permiso)
    )
