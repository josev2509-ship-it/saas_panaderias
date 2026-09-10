from .models import Empresa, PerfilUsuario


def obtener_perfil_saas(user):
    if not getattr(user, "is_authenticated", False):
        return None

    return (
        PerfilUsuario.objects
        .select_related(
            "empresa",
            "empresa__suscripcion",
            "empresa__suscripcion__plan",
        )
        .filter(
            user=user,
            activo=True,
        )
        .first()
    )


def obtener_empresa_saas(user):
    perfil = obtener_perfil_saas(user)
    return perfil.empresa if perfil else None


def obtener_suscripcion(user):
    empresa_saas = obtener_empresa_saas(user)

    if not empresa_saas:
        return None

    return getattr(
        empresa_saas,
        "suscripcion",
        None,
    )


def empresa_saas_permite_acceso(empresa_saas):
    """Política comercial única para evaluar una EmpresaSaaS."""
    if empresa_saas is None:
        return False

    if empresa_saas.suspendida_manualmente:
        return False

    if not empresa_saas.activa:
        return False

    if not empresa_saas.requiere_pago:
        return True

    suscripcion = getattr(empresa_saas, "suscripcion", None)
    return bool(suscripcion and suscripcion.permite_acceso())



def empresa_operativa_usuario(user):
    """
    Compatibilidad con la capa de suscripciones.

    La empresa operativa se resuelve exclusivamente desde
    tenant_context.
    """
    from .tenant_context import (
        empresa_operativa_usuario as resolver_empresa_operativa_usuario,
    )

    return resolver_empresa_operativa_usuario(
        user
    )



def suscripcion_permite_acceso(user):
    if not getattr(user, "is_authenticated", False):
        return False

    if getattr(user, "is_superuser", False):
        return True

    empresa_saas = obtener_empresa_saas(user)

    if empresa_saas is None:
        # Compatibilidad con usuarios históricos.
        return True

    return empresa_saas_permite_acceso(empresa_saas)


def modulo_habilitado(user, nombre_modulo):
    if not suscripcion_permite_acceso(user):
        return False

    if getattr(user, "is_superuser", False):
        return True

    empresa_saas = obtener_empresa_saas(user)
    suscripcion = obtener_suscripcion(user)
    empresa_operativa = empresa_operativa_usuario(user)

    # Trial = acceso completo.
    if suscripcion and suscripcion.esta_en_prueba():
        return True

    # Empresa gratuita/cortesía:
    # manda la configuración manual de Empresa.
    if empresa_saas and not empresa_saas.requiere_pago:
        return bool(
            empresa_operativa
            and hasattr(
                empresa_operativa,
                nombre_modulo,
            )
            and getattr(
                empresa_operativa,
                nombre_modulo,
            )
        )

    plan = suscripcion.plan if suscripcion else None

    incluido_plan = bool(
        plan
        and hasattr(plan, nombre_modulo)
        and getattr(plan, nombre_modulo)
    )

    override_empresa = bool(
        empresa_operativa
        and hasattr(
            empresa_operativa,
            nombre_modulo,
        )
        and getattr(
            empresa_operativa,
            nombre_modulo,
        )
    )

    return incluido_plan or override_empresa

def suscripcion_permite_acceso_request(request):
    """
    Comprueba acceso utilizando la empresa efectiva de la petición.

    En modo soporte evalúa la empresa seleccionada, no la cuenta
    interna del agente de soporte.
    """
    from .tenant_context import (
        contexto_soporte_activo,
        obtener_contexto_soporte,
    )

    if contexto_soporte_activo(request):
        contexto = obtener_contexto_soporte(request)

        if not contexto:
            return False

        return empresa_saas_permite_acceso(contexto["empresa_saas"])

    return suscripcion_permite_acceso(
        request.user
    )


def modulo_habilitado_request(
    request,
    nombre_modulo,
):
    """
    Comprueba módulos utilizando el tenant efectivo de la petición.
    """
    from .tenant_context import (
        contexto_soporte_activo,
        obtener_contexto_soporte,
    )

    if contexto_soporte_activo(request):
        contexto = obtener_contexto_soporte(request)

        if not contexto:
            return False

        empresa_saas = contexto["empresa_saas"]
        empresa_operativa = contexto[
            "empresa_operativa"
        ]

        suscripcion = getattr(
            empresa_saas,
            "suscripcion",
            None,
        )

        # Durante prueba: acceso completo.
        if (
            suscripcion
            and suscripcion.esta_en_prueba()
        ):
            return True

        manual = bool(
            getattr(
                empresa_operativa,
                nombre_modulo,
                False,
            )
        )

        # Cortesía/manual: manda configuración operativa.
        if not empresa_saas.requiere_pago:
            return manual

        plan = (
            suscripcion.plan
            if suscripcion
            else None
        )

        plan_activo = bool(
            plan
            and getattr(
                plan,
                nombre_modulo,
                False,
            )
        )

        return plan_activo or manual

    return modulo_habilitado(
        request.user,
        nombre_modulo,
    )
