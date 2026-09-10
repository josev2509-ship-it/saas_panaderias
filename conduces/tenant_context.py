"""
Contexto multiempresa central de SASTRE ERP.

Este módulo será la única fuente de verdad para determinar
la empresa operativa y la EmpresaSaaS asociadas a una petición.

IMPORTANTE:
El modo soporte todavía NO se activa aquí automáticamente.
La sesión de soporte solamente será tomada en cuenta cuando
la activemos expresamente después de migrar los módulos.
"""

from django.core.exceptions import PermissionDenied

from .models import Empresa, EmpresaSaaS, PerfilUsuario


GRUPO_SOPORTE_SASTRE = "Soporte SASTRE"

SESSION_SOPORTE_SAAS = "soporte_empresa_saas_id"
SESSION_SOPORTE_OPERATIVA = "soporte_empresa_operativa_id"
SESSION_SOPORTE_MOTIVO = "soporte_motivo"
SESSION_SOPORTE_INICIADO = "soporte_iniciado_en"
SESSION_SOPORTE_ACTOR = "soporte_actor_user_id"


def es_soporte_sastre(user):
    """
    Indica si el usuario puede operar el Centro de Soporte SASTRE.

    El resultado se cachea sobre la instancia User de la petición
    para evitar consultas repetidas al grupo durante el mismo request.
    """
    if not getattr(user, "is_authenticated", False):
        return False

    if user.is_superuser:
        return True

    cache_attr = "_sastre_es_soporte_cache"

    if hasattr(user, cache_attr):
        return getattr(user, cache_attr)

    permitido = user.groups.filter(
        name=GRUPO_SOPORTE_SASTRE
    ).exists()

    setattr(
        user,
        cache_attr,
        permitido,
    )

    return permitido


def obtener_perfil_saas_usuario(user):
    """
    Perfil SaaS real del usuario autenticado.
    No considera todavía contexto de soporte.
    """
    if not getattr(user, "is_authenticated", False):
        return None

    return (
        PerfilUsuario.objects
        .select_related("empresa")
        .filter(
            user=user,
            activo=True,
        )
        .first()
    )


def obtener_empresa_saas_usuario(user):
    perfil = obtener_perfil_saas_usuario(user)

    return (
        perfil.empresa
        if perfil
        else None
    )


def empresa_operativa_desde_saas(empresa_saas):
    """
    Resuelve la Empresa operativa vinculada a una EmpresaSaaS.

    Mientras la arquitectura actual conserve Empresa.usuario
    como OneToOne, buscamos la empresa a través de cualquiera
    de los perfiles pertenecientes a la EmpresaSaaS.
    """
    if empresa_saas is None:
        return None

    perfiles = (
        PerfilUsuario.objects
        .filter(
            empresa=empresa_saas,
        )
        .select_related("user")
        .order_by(
            "-user__is_active",
            "id",
        )
    )

    for perfil in perfiles:
        user = perfil.user

        empresa = getattr(
            user,
            "empresa_principal",
            None,
        )

        if empresa:
            return empresa

        empresa = (
            Empresa.objects
            .filter(usuario=user)
            .first()
        )

        if empresa:
            return empresa

    return None


def empresa_operativa_usuario(user):
    """
    Empresa operativa real del usuario.

    Esta función reemplazará progresivamente las implementaciones
    duplicadas distribuidas por el proyecto.
    """
    if not getattr(user, "is_authenticated", False):
        return None

    empresa = getattr(
        user,
        "empresa_principal",
        None,
    )

    if empresa:
        return empresa

    empresa = (
        Empresa.objects
        .filter(usuario=user)
        .first()
    )

    if empresa:
        return empresa

    empresa_saas = obtener_empresa_saas_usuario(user)

    return empresa_operativa_desde_saas(
        empresa_saas
    )


def contexto_soporte_activo(request):
    """
    Detecta una sesión de soporte válida.

    Además de comprobar autorización, verifica que la sesión
    pertenezca al mismo agente que inició el modo soporte.
    """
    if not es_soporte_sastre(request.user):
        return False

    actor_id = request.session.get(
        SESSION_SOPORTE_ACTOR
    )

    if actor_id != request.user.pk:
        return False

    return bool(
        request.session.get(
            SESSION_SOPORTE_SAAS
        )
        and request.session.get(
            SESSION_SOPORTE_OPERATIVA
        )
    )


def obtener_contexto_soporte(request):
    """
    Devuelve datos de una sesión de soporte ya validada.
    """
    if not contexto_soporte_activo(request):
        return None

    saas_id = request.session.get(
        SESSION_SOPORTE_SAAS
    )

    operativa_id = request.session.get(
        SESSION_SOPORTE_OPERATIVA
    )

    empresa_saas = (
        EmpresaSaaS.objects
        .filter(pk=saas_id)
        .first()
    )

    empresa_operativa = (
        Empresa.objects
        .filter(pk=operativa_id)
        .first()
    )

    if (
        empresa_saas is None
        or empresa_operativa is None
    ):
        limpiar_contexto_soporte(request)
        return None

    # Comprobación crítica:
    # la Empresa operativa guardada debe seguir correspondiendo
    # a la EmpresaSaaS seleccionada.
    esperada = empresa_operativa_desde_saas(
        empresa_saas
    )

    if (
        esperada is None
        or esperada.pk != empresa_operativa.pk
    ):
        limpiar_contexto_soporte(request)

        raise PermissionDenied(
            "El contexto de soporte no coincide con la empresa seleccionada."
        )

    return {
        "empresa_saas": empresa_saas,
        "empresa_operativa": empresa_operativa,
        "motivo": request.session.get(
            SESSION_SOPORTE_MOTIVO,
            "",
        ),
        "iniciado_en": request.session.get(
            SESSION_SOPORTE_INICIADO
        ),
        "actor_user_id": request.session.get(
            SESSION_SOPORTE_ACTOR
        ),
    }


def obtener_empresa_request(
    request,
    *,
    permitir_soporte=False,
):
    """
    Resolvedor central para una petición.

    Por seguridad, permitir_soporte=False durante esta primera fase.

    Cuando terminemos de migrar todos los módulos, cambiaremos
    los puntos controlados a permitir_soporte=True.
    """
    if (
        permitir_soporte
        and contexto_soporte_activo(request)
    ):
        contexto = obtener_contexto_soporte(
            request
        )

        if contexto:
            return contexto[
                "empresa_operativa"
            ]

    return empresa_operativa_usuario(
        request.user
    )


def obtener_empresa_saas_request(
    request,
    *,
    permitir_soporte=False,
):
    if (
        permitir_soporte
        and contexto_soporte_activo(request)
    ):
        contexto = obtener_contexto_soporte(
            request
        )

        if contexto:
            return contexto[
                "empresa_saas"
            ]

    return obtener_empresa_saas_usuario(
        request.user
    )


def limpiar_contexto_soporte(request):
    for key in (
        SESSION_SOPORTE_SAAS,
        SESSION_SOPORTE_OPERATIVA,
        SESSION_SOPORTE_MOTIVO,
        SESSION_SOPORTE_INICIADO,
        SESSION_SOPORTE_ACTOR,
    ):
        request.session.pop(
            key,
            None,
        )
