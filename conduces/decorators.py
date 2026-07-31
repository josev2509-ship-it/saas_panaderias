from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404

from .services import obtener_empresa_usuario
from .models import Empresa


def modulo_requerido(nombre_modulo, permiso=None):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            empresa = Empresa.objects.filter(usuario_id=request.user.pk).first()
            if empresa is None:
                raise PermissionDenied("El usuario no tiene una empresa activa.")
            if not empresa.activa:
                raise PermissionDenied("La empresa se encuentra inactiva.")
            empresa_usuario = getattr(request.user, "empresa_principal", None)
            if empresa_usuario is None or empresa_usuario.pk != empresa.pk:
                raise Http404
            if not hasattr(empresa, nombre_modulo) or not getattr(empresa, nombre_modulo):
                raise PermissionDenied("El módulo no está disponible para esta empresa.")
            if permiso and not request.user.has_perm(permiso):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
