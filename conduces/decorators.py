from .tenant_context import obtener_empresa_request
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404

from .services import obtener_empresa_usuario
from .models import Empresa, PerfilUsuario
from .subscription_service import (
    empresa_operativa_usuario,
    modulo_habilitado,
    suscripcion_permite_acceso,
    modulo_habilitado_request,
    suscripcion_permite_acceso_request,
)


def puede_eliminar_conduce(user):
    """Politica unificada para la baja logica de conduces."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.has_perm("conduces.delete_conduce"):
        return True
    return PerfilUsuario.objects.filter(
        user=user,
        rol="admin_empresa",
        activo=True,
    ).exists()


def permiso_eliminar_conduce_requerido(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not puede_eliminar_conduce(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


def modulo_requerido(nombre_modulo, permiso=None):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path()
                )

            empresa = obtener_empresa_request(
                request,
                permitir_soporte=True,
            )

            if empresa is None:
                raise PermissionDenied(
                    "El usuario no tiene una empresa activa."
                )

            if not empresa.activa:
                raise PermissionDenied(
                    "La empresa se encuentra inactiva."
                )

            if not suscripcion_permite_acceso_request(
                request
            ):
                raise PermissionDenied(
                    "La suscripción no está activa."
                )

            if not modulo_habilitado_request(
                request,
                nombre_modulo,
            ):
                raise PermissionDenied(
                    "El módulo no está disponible para esta empresa."
                )

            if permiso and not request.user.has_perm(
                permiso
            ):
                raise PermissionDenied

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapper

    return decorator
