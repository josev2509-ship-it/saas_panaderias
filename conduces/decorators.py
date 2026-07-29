from functools import wraps

from django.shortcuts import redirect
from django.contrib import messages

from .services import obtener_empresa_usuario


def modulo_requerido(nombre_modulo):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            # =================================================
            # MODO DESARROLLO
            # =================================================
            # Temporalmente permitir acceso completo
            # mientras terminamos el sistema SaaS.
            # =================================================

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator