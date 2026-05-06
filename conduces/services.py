from .models import Empresa


def obtener_empresa_usuario(request):
    if not request.user.is_authenticated:
        return None

    empresa = getattr(request.user, "empresa_principal", None)

    if empresa:
        return empresa

    return Empresa.objects.filter(usuario=request.user).first()