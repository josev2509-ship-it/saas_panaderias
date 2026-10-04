from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from conduces.models import PerfilUsuario
from conduces.subscription_service import estado_acceso_modulo_request
from conduces.tenant_context import (
    contexto_soporte_activo,
    empresa_operativa_usuario,
    es_soporte_sastre,
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

            # El modo soporte es un estado explícito de la sesión, no una
            # característica permanente del usuario. Fuera de ese modo, un
            # usuario con capacidad de soporte solo puede usar su tenant propio.
            soporte = contexto_soporte_activo(request)
            empresa_propia = None if soporte else empresa_operativa_usuario(request.user)
            if not soporte and empresa_propia is None and es_soporte_sastre(request.user):
                raise PermissionDenied("El soporte requiere un contexto empresarial activo.")

            empresa = (
                obtener_empresa_requerida(request, permitir_soporte=True)
                if soporte
                else empresa_propia
            )
            if empresa is None:
                raise PermissionDenied("No existe una empresa operativa vinculada a esta cuenta.")
            if not empresa.activa:
                raise PermissionDenied("La empresa se encuentra inactiva.")

            suscripcion_ok, modulo_ok = estado_acceso_modulo_request(
                request, empresa, "modulo_nomina"
            )
            if not suscripcion_ok or not modulo_ok:
                raise PermissionDenied("Gestión Humana y Nómina no están habilitadas.")

            perfil = None if soporte else obtener_perfil_saas_usuario(request.user)
            administrador = bool(
                (
                    request.user.is_superuser
                    and not soporte
                    and empresa_propia is not None
                    and empresa_propia.pk == empresa.pk
                )
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
