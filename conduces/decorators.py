from django.shortcuts import redirect
from django.contrib import messages
from .services import obtener_empresa_usuario
from django.shortcuts import redirect
from django.contrib import messages
from .services import obtener_empresa_usuario


def modulo_requerido(nombre_modulo):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            empresa = obtener_empresa_usuario(request)

            if not empresa:
                messages.error(request, "No tienes una empresa asignada.")
                return redirect("login_usuario")

            if not getattr(empresa, nombre_modulo, False):
                messages.error(request, "No tienes acceso a este módulo.")
                return redirect("inicio")

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator