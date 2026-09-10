from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Empresa,
    EmpresaSaaS,
    EventoSuscripcion,
    PagoSuscripcion,
    PerfilUsuario,
    Plan,
)



from .tenant_context import (
    SESSION_SOPORTE_SAAS,
    SESSION_SOPORTE_OPERATIVA,
    SESSION_SOPORTE_MOTIVO,
    SESSION_SOPORTE_INICIADO,
    SESSION_SOPORTE_ACTOR,
    empresa_operativa_desde_saas,
    limpiar_contexto_soporte,
)

User = get_user_model()


GRUPO_SOPORTE_SASTRE = "Soporte SASTRE"


def es_soporte_sastre(user):
    if not getattr(user, "is_authenticated", False):
        return False

    if user.is_superuser:
        return True

    return user.groups.filter(
        name=GRUPO_SOPORTE_SASTRE
    ).exists()


soporte_sastre_required = user_passes_test(
    es_soporte_sastre,
    login_url="soporte_login",
)


def soporte_login(request):
    if request.user.is_authenticated:
        if es_soporte_sastre(request.user):
            return redirect("soporte_empresas")

        logout(request)

    if request.method == "POST":
        username = (
            request.POST.get("username")
            or ""
        ).strip()

        password = (
            request.POST.get("password")
            or ""
        )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is None:
            messages.error(
                request,
                "Usuario o contraseña incorrectos.",
            )

        elif not user.is_active:
            messages.error(
                request,
                "Este usuario se encuentra inactivo.",
            )

        elif not es_soporte_sastre(user):
            messages.error(
                request,
                "Este usuario no tiene autorización para acceder al Centro de Soporte SASTRE.",
            )

        else:
            login(request, user)

            return redirect(
                "soporte_empresas"
            )

    return render(
        request,
        "support_sastre/login.html",
    )


def soporte_logout(request):
    logout(request)

    return redirect(
        "soporte_login"
    )


MODULOS = (
    ("modulo_inabie", "INABIE"),
    ("modulo_conduces", "Conduces"),
    ("modulo_centros", "Centros educativos"),
    ("modulo_menu", "Menus"),
    ("modulo_facturacion", "Facturacion"),
    ("modulo_reportes", "Reportes"),
    ("modulo_inventario", "Inventario"),
    ("modulo_compras", "Compras"),
    ("modulo_catalogos", "Catalogos"),
    ("modulo_workflow", "Workflow"),
    ("modulo_rutas", "Rutas"),
    ("modulo_nomina", "Nomina"),
)


def _empresa_operativa_desde_saas(empresa_saas):
    perfiles = (
        PerfilUsuario.objects
        .filter(empresa=empresa_saas)
        .select_related("user")
    )

    for perfil in perfiles:
        empresa = getattr(
            perfil.user,
            "empresa_principal",
            None,
        )

        if empresa:
            return empresa

        empresa = Empresa.objects.filter(
            usuario=perfil.user
        ).first()

        if empresa:
            return empresa

    return None


def _diagnostico_acceso(empresa_saas):
    if not empresa_saas.activa:
        return {
            "texto": "Empresa desactivada",
            "clase": "bad",
        }

    if empresa_saas.suspendida_manualmente:
        return {
            "texto": "Suspendida manualmente",
            "clase": "bad",
        }

    if not empresa_saas.requiere_pago:
        return {
            "texto": "Acceso administrativo / cortesia",
            "clase": "ok",
        }

    sus = getattr(
        empresa_saas,
        "suscripcion",
        None,
    )

    if not sus:
        return {
            "texto": "Sin suscripcion activa",
            "clase": "warn",
        }

    if sus.esta_en_prueba():
        return {
            "texto": (
                f"Prueba activa - "
                f"{sus.dias_restantes_prueba()} dias"
            ),
            "clase": "info",
        }

    if sus.permite_acceso():
        if sus.estado == "pago_fallido":
            return {
                "texto": "Pago fallido en periodo de gracia",
                "clase": "warn",
            }

        return {
            "texto": "Acceso permitido",
            "clase": "ok",
        }

    return {
        "texto": f"Bloqueada: {sus.get_estado_display()}",
        "clase": "bad",
    }


def _registrar_evento(
    empresa,
    request,
    tipo,
    descripcion,
    datos=None,
):
    EventoSuscripcion.objects.create(
        empresa=empresa,
        suscripcion=getattr(
            empresa,
            "suscripcion",
            None,
        ),
        tipo=tipo,
        descripcion=descripcion,
        usuario=request.user,
        datos=datos or {},
    )


@soporte_sastre_required
def soporte_empresas(request):
    q = (
        request.GET.get("q")
        or ""
    ).strip()

    empresas = (
        EmpresaSaaS.objects
        .select_related(
            "suscripcion",
            "suscripcion__plan",
        )
        .order_by("nombre")
    )

    if q:
        empresas = (
            empresas
            .filter(
                Q(nombre__icontains=q)
                | Q(rnc__icontains=q)
                | Q(correo__icontains=q)
                | Q(
                    perfilusuario__user__username__icontains=q
                )
                | Q(
                    perfilusuario__user__email__icontains=q
                )
            )
            .distinct()
        )

    filas = []

    for empresa in empresas:
        sus = getattr(
            empresa,
            "suscripcion",
            None,
        )

        usuarios = PerfilUsuario.objects.filter(
            empresa=empresa
        )

        total_usuarios = usuarios.count()

        activos = usuarios.filter(
            activo=True,
            user__is_active=True,
        ).count()

        filas.append({
            "empresa": empresa,
            "suscripcion": sus,
            "total_usuarios": total_usuarios,
            "usuarios_activos": activos,
            "diagnostico": _diagnostico_acceso(
                empresa
            ),
        })

    hoy = timezone.localdate()

    base = EmpresaSaaS.objects.all()

    indicadores = {
        "total": base.count(),
        "activas": base.filter(
            activa=True,
            suspendida_manualmente=False,
        ).count(),
        "cortesia": base.filter(
            requiere_pago=False,
        ).count(),
        "suspendidas": base.filter(
            suspendida_manualmente=True,
        ).count(),
        "trial": base.filter(
            suscripcion__estado="prueba",
            suscripcion__en_prueba=True,
            suscripcion__fecha_fin__gte=hoy,
        ).count(),
    }

    return render(
        request,
        "support_sastre/empresas.html",
        {
            "filas": filas,
            "q": q,
            "indicadores": indicadores,
        },
    )


@soporte_sastre_required
def soporte_empresa_detalle(
    request,
    empresa_id,
):
    empresa = get_object_or_404(
        EmpresaSaaS.objects.select_related(
            "suscripcion",
            "suscripcion__plan",
        ),
        pk=empresa_id,
    )

    sus = getattr(
        empresa,
        "suscripcion",
        None,
    )

    plan = sus.plan if sus else None

    perfiles = list(
        PerfilUsuario.objects
        .filter(empresa=empresa)
        .select_related("user")
        .order_by(
            "-activo",
            "user__username",
        )
    )

    empresa_operativa = (
        _empresa_operativa_desde_saas(
            empresa
        )
    )

    modulos = []

    for campo, etiqueta in MODULOS:
        plan_activo = bool(
            plan
            and hasattr(plan, campo)
            and getattr(plan, campo)
        )

        manual_activo = bool(
            empresa_operativa
            and hasattr(
                empresa_operativa,
                campo,
            )
            and getattr(
                empresa_operativa,
                campo,
            )
        )

        if sus and sus.esta_en_prueba():
            efectivo = True
            fuente = "Prueba completa"

        elif not empresa.requiere_pago:
            efectivo = manual_activo
            fuente = "Configuracion manual"

        else:
            efectivo = (
                plan_activo
                or manual_activo
            )

            if plan_activo and manual_activo:
                fuente = "Plan + manual"
            elif plan_activo:
                fuente = "Plan"
            elif manual_activo:
                fuente = "Manual"
            else:
                fuente = "No habilitado"

        modulos.append({
            "campo": campo,
            "nombre": etiqueta,
            "plan": plan_activo,
            "manual": manual_activo,
            "efectivo": efectivo,
            "fuente": fuente,
        })

    pagos = (
        PagoSuscripcion.objects
        .filter(empresa=empresa)
        .order_by("-creado_en")[:20]
    )

    eventos = (
        EventoSuscripcion.objects
        .filter(empresa=empresa)
        .select_related(
            "usuario",
            "suscripcion",
        )
        .order_by("-creado_en")[:30]
    )

    ultimo_login = None

    for perfil in perfiles:
        if perfil.user.last_login:
            if (
                ultimo_login is None
                or perfil.user.last_login
                > ultimo_login
            ):
                ultimo_login = (
                    perfil.user.last_login
                )

    planes = Plan.objects.filter(
        activo=True
    ).order_by("nombre")

    return render(
        request,
        "support_sastre/empresa_detalle.html",
        {
            "empresa": empresa,
            "suscripcion": sus,
            "plan": plan,
            "planes": planes,
            "perfiles": perfiles,
            "empresa_operativa": (
                empresa_operativa
            ),
            "modulos": modulos,
            "pagos": pagos,
            "eventos": eventos,
            "diagnostico": (
                _diagnostico_acceso(
                    empresa
                )
            ),
            "ultimo_login": ultimo_login,
        },
    )


@soporte_sastre_required
@require_POST
def soporte_empresa_modulos(
    request,
    empresa_id,
):
    empresa = get_object_or_404(
        EmpresaSaaS,
        pk=empresa_id,
    )

    empresa_operativa = (
        _empresa_operativa_desde_saas(
            empresa
        )
    )

    if not empresa_operativa:
        messages.error(
            request,
            "No existe una empresa operativa vinculada.",
        )

        return redirect(
            "soporte_empresa_detalle",
            empresa_id=empresa.pk,
        )

    anteriores = {}

    nuevos = {}

    for campo, etiqueta in MODULOS:
        anterior = bool(
            getattr(
                empresa_operativa,
                campo,
                False,
            )
        )

        nuevo = (
            request.POST.get(campo)
            == "on"
        )

        anteriores[campo] = anterior
        nuevos[campo] = nuevo

        if hasattr(
            empresa_operativa,
            campo,
        ):
            setattr(
                empresa_operativa,
                campo,
                nuevo,
            )

    empresa_operativa.save(
        update_fields=[
            campo
            for campo, etiqueta in MODULOS
            if hasattr(
                empresa_operativa,
                campo,
            )
        ]
    )

    cambios = {
        campo: {
            "antes": anteriores[campo],
            "despues": nuevos[campo],
        }
        for campo, etiqueta in MODULOS
        if anteriores[campo]
        != nuevos[campo]
    }

    _registrar_evento(
        empresa,
        request,
        "MODULOS_ACTUALIZADOS",
        "Configuracion manual de modulos actualizada.",
        datos={
            "cambios": cambios,
        },
    )

    messages.success(
        request,
        "Modulos actualizados correctamente.",
    )

    return redirect(
        "soporte_empresa_detalle",
        empresa_id=empresa.pk,
    )


@soporte_sastre_required
@require_POST
def soporte_empresa_plan(
    request,
    empresa_id,
):
    empresa = get_object_or_404(
        EmpresaSaaS,
        pk=empresa_id,
    )

    sus = getattr(
        empresa,
        "suscripcion",
        None,
    )

    if not sus:
        messages.error(
            request,
            "Esta empresa no tiene una suscripcion registrada.",
        )

        return redirect(
            "soporte_empresa_detalle",
            empresa_id=empresa.pk,
        )

    plan_id = request.POST.get(
        "plan_id"
    )

    if not plan_id:
        plan = None
    else:
        plan = get_object_or_404(
            Plan,
            pk=plan_id,
        )

    anterior = (
        sus.plan.nombre
        if sus.plan
        else None
    )

    sus.plan = plan
    sus.save(
        update_fields=[
            "plan",
            "actualizada_en",
        ]
    )

    _registrar_evento(
        empresa,
        request,
        "CAMBIO_PLAN",
        "Plan actualizado desde Centro de Soporte.",
        datos={
            "plan_anterior": anterior,
            "plan_nuevo": (
                plan.nombre
                if plan
                else None
            ),
        },
    )

    messages.success(
        request,
        "Plan actualizado.",
    )

    return redirect(
        "soporte_empresa_detalle",
        empresa_id=empresa.pk,
    )


@soporte_sastre_required
@require_POST
def soporte_empresa_accion(
    request,
    empresa_id,
):
    empresa = get_object_or_404(
        EmpresaSaaS,
        pk=empresa_id,
    )

    accion = request.POST.get(
        "accion"
    )

    motivo = (
        request.POST.get("motivo")
        or ""
    ).strip()

    if accion == "activar":
        empresa.activa = True
        empresa.suspendida_manualmente = False
        empresa.motivo_suspension = ""
        empresa.fecha_suspension = None

        empresa.save(
            update_fields=[
                "activa",
                "suspendida_manualmente",
                "motivo_suspension",
                "fecha_suspension",
            ]
        )

        _registrar_evento(
            empresa,
            request,
            "ACTIVACION_MANUAL",
            motivo
            or "Empresa activada manualmente.",
        )

        messages.success(
            request,
            "Empresa activada.",
        )

    elif accion == "suspender":
        if not motivo:
            messages.error(
                request,
                "Debes indicar el motivo de suspension.",
            )

            return redirect(
                "soporte_empresa_detalle",
                empresa_id=empresa.pk,
            )

        empresa.suspendida_manualmente = True
        empresa.fecha_suspension = (
            timezone.now()
        )
        empresa.motivo_suspension = (
            motivo
        )

        empresa.save(
            update_fields=[
                "suspendida_manualmente",
                "fecha_suspension",
                "motivo_suspension",
            ]
        )

        _registrar_evento(
            empresa,
            request,
            "SUSPENSION_MANUAL",
            motivo,
        )

        messages.success(
            request,
            "Empresa suspendida.",
        )

    elif accion == "cortesia":
        empresa.requiere_pago = False
        empresa.activa = True
        empresa.suspendida_manualmente = False
        empresa.motivo_suspension = ""
        empresa.fecha_suspension = None

        empresa.save(
            update_fields=[
                "requiere_pago",
                "activa",
                "suspendida_manualmente",
                "motivo_suspension",
                "fecha_suspension",
            ]
        )

        _registrar_evento(
            empresa,
            request,
            "CORTESIA_ACTIVADA",
            motivo
            or "Empresa configurada sin pago.",
        )

        messages.success(
            request,
            "Empresa configurada como cortesia.",
        )

    elif accion == "exigir_pago":
        empresa.requiere_pago = True

        empresa.save(
            update_fields=[
                "requiere_pago",
            ]
        )

        _registrar_evento(
            empresa,
            request,
            "PAGO_REQUERIDO",
            motivo
            or "La empresa vuelve a requerir pago.",
        )

        messages.success(
            request,
            "Pago requerido activado.",
        )

    elif accion == "extender_trial":
        sus = getattr(
            empresa,
            "suscripcion",
            None,
        )

        if not sus:
            messages.error(
                request,
                "La empresa no tiene suscripcion.",
            )
        else:
            try:
                dias = int(
                    request.POST.get(
                        "dias",
                        "15",
                    )
                )
            except ValueError:
                dias = 15

            dias = max(
                1,
                min(dias, 365),
            )

            hoy = timezone.localdate()

            base = (
                sus.fecha_fin
                if (
                    sus.fecha_fin
                    and sus.fecha_fin >= hoy
                )
                else hoy
            )

            sus.fecha_fin = (
                base
                + timedelta(days=dias)
            )
            sus.estado = "prueba"
            sus.en_prueba = True

            sus.save(
                update_fields=[
                    "fecha_fin",
                    "estado",
                    "en_prueba",
                    "actualizada_en",
                ]
            )

            _registrar_evento(
                empresa,
                request,
                "EXTENSION_TRIAL",
                (
                    f"Prueba extendida "
                    f"{dias} dias."
                ),
            )

            messages.success(
                request,
                (
                    f"Prueba extendida "
                    f"{dias} dias."
                ),
            )

    else:
        messages.error(
            request,
            "Accion no reconocida.",
        )

    return redirect(
        "soporte_empresa_detalle",
        empresa_id=empresa.pk,
    )


@soporte_sastre_required
def soporte_usuario_detalle(
    request,
    empresa_id,
    perfil_id,
):
    empresa = get_object_or_404(
        EmpresaSaaS,
        pk=empresa_id,
    )

    perfil = get_object_or_404(
        PerfilUsuario.objects
        .select_related("user"),
        pk=perfil_id,
        empresa=empresa,
    )

    if request.method == "POST":
        user = perfil.user

        first_name = (
            request.POST.get(
                "first_name"
            )
            or ""
        ).strip()

        last_name = (
            request.POST.get(
                "last_name"
            )
            or ""
        ).strip()

        email = (
            request.POST.get(
                "email"
            )
            or ""
        ).strip()

        rol = request.POST.get(
            "rol"
        )

        activo = (
            request.POST.get(
                "activo"
            )
            == "on"
        )

        correo_validado = (
            request.POST.get(
                "correo_validado"
            )
            == "on"
        )

        roles_validos = {
            value
            for value, label
            in PerfilUsuario.ROLES
        }

        if rol not in roles_validos:
            messages.error(
                request,
                "Rol no valido.",
            )

            return redirect(
                "soporte_usuario_detalle",
                empresa_id=empresa.pk,
                perfil_id=perfil.pk,
            )

        if (
            not activo
            and user.pk
            == request.user.pk
        ):
            messages.error(
                request,
                "No puedes desactivar tu propio usuario.",
            )

            return redirect(
                "soporte_usuario_detalle",
                empresa_id=empresa.pk,
                perfil_id=perfil.pk,
            )

        antes = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "rol": perfil.rol,
            "activo": perfil.activo,
            "correo_validado": (
                perfil.correo_validado
            ),
        }

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.is_active = activo

        user.save(
            update_fields=[
                "first_name",
                "last_name",
                "email",
                "is_active",
            ]
        )

        perfil.rol = rol
        perfil.activo = activo
        perfil.correo_validado = (
            correo_validado
        )

        perfil.save(
            update_fields=[
                "rol",
                "activo",
                "correo_validado",
            ]
        )

        despues = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "rol": rol,
            "activo": activo,
            "correo_validado": (
                correo_validado
            ),
        }

        _registrar_evento(
            empresa,
            request,
            "USUARIO_ACTUALIZADO",
            (
                f"Usuario "
                f"{user.username} actualizado."
            ),
            datos={
                "antes": antes,
                "despues": despues,
            },
        )

        messages.success(
            request,
            "Usuario actualizado correctamente.",
        )

        return redirect(
            "soporte_usuario_detalle",
            empresa_id=empresa.pk,
            perfil_id=perfil.pk,
        )

    return render(
        request,
        "support_sastre/usuario_detalle.html",
        {
            "empresa": empresa,
            "perfil": perfil,
            "usuario": perfil.user,
            "roles": PerfilUsuario.ROLES,
        },
    )


@soporte_sastre_required
@require_POST
def soporte_usuario_accion(
    request,
    empresa_id,
    perfil_id,
):
    empresa = get_object_or_404(
        EmpresaSaaS,
        pk=empresa_id,
    )

    perfil = get_object_or_404(
        PerfilUsuario.objects
        .select_related("user"),
        pk=perfil_id,
        empresa=empresa,
    )

    accion = request.POST.get(
        "accion"
    )

    if accion == "activar":
        perfil.activo = True
        perfil.user.is_active = True

        perfil.save(
            update_fields=["activo"]
        )

        perfil.user.save(
            update_fields=["is_active"]
        )

        _registrar_evento(
            empresa,
            request,
            "USUARIO_ACTIVADO",
            (
                f"Usuario "
                f"{perfil.user.username} activado."
            ),
        )

        messages.success(
            request,
            "Usuario activado.",
        )

    elif accion == "desactivar":
        if (
            perfil.user_id
            == request.user.id
        ):
            messages.error(
                request,
                "No puedes desactivar tu propio usuario.",
            )
        else:
            perfil.activo = False
            perfil.user.is_active = False

            perfil.save(
                update_fields=["activo"]
            )

            perfil.user.save(
                update_fields=["is_active"]
            )

            _registrar_evento(
                empresa,
                request,
                "USUARIO_DESACTIVADO",
                (
                    f"Usuario "
                    f"{perfil.user.username} desactivado."
                ),
            )

            messages.success(
                request,
                "Usuario desactivado.",
            )

    elif accion == "validar_correo":
        perfil.correo_validado = True

        perfil.save(
            update_fields=[
                "correo_validado"
            ]
        )

        _registrar_evento(
            empresa,
            request,
            "CORREO_VALIDADO_MANUAL",
            (
                f"Correo de "
                f"{perfil.user.username} "
                f"validado manualmente."
            ),
        )

        messages.success(
            request,
            "Correo validado.",
        )

    else:
        messages.error(
            request,
            "Accion no reconocida.",
        )

    return redirect(
        "soporte_empresa_detalle",
        empresa_id=empresa.pk,
    )


@soporte_sastre_required
@require_POST
def soporte_entrar_empresa(
    request,
    empresa_id,
):
    empresa_saas = get_object_or_404(
        EmpresaSaaS.objects.select_related("suscripcion"),
        pk=empresa_id,
    )

    from .subscription_service import empresa_saas_permite_acceso

    # Un intento nuevo nunca debe heredar un tenant de soporte anterior.
    limpiar_contexto_soporte(request)

    if not empresa_saas_permite_acceso(empresa_saas):
        messages.error(
            request,
            "No es posible ingresar a esta empresa porque su acceso se encuentra "
            "suspendido o su suscripción no está vigente.",
        )
        return redirect(
            "soporte_empresa_detalle",
            empresa_id=empresa_saas.pk,
        )

    empresa_operativa = (
        empresa_operativa_desde_saas(
            empresa_saas
        )
    )

    if not empresa_operativa:
        messages.error(
            request,
            "No existe una empresa operativa vinculada.",
        )

        return redirect(
            "soporte_empresa_detalle",
            empresa_id=empresa_saas.pk,
        )

    motivo = (
        request.POST.get("motivo")
        or ""
    ).strip()

    if len(motivo) < 5:
        messages.error(
            request,
            "Indica el motivo del acceso de soporte.",
        )

        return redirect(
            "soporte_empresa_detalle",
            empresa_id=empresa_saas.pk,
        )

    momento = timezone.now()

    request.session[
        SESSION_SOPORTE_SAAS
    ] = empresa_saas.pk

    request.session[
        SESSION_SOPORTE_OPERATIVA
    ] = empresa_operativa.pk

    request.session[
        SESSION_SOPORTE_MOTIVO
    ] = motivo

    request.session[
        SESSION_SOPORTE_INICIADO
    ] = momento.isoformat()

    request.session[
        SESSION_SOPORTE_ACTOR
    ] = request.user.pk

    request.session.modified = True

    _registrar_evento(
        empresa_saas,
        request,
        "ACCESO_SOPORTE_INICIADO",
        (
            f"Acceso de soporte iniciado por "
            f"{request.user.get_username()}."
        ),
        datos={
            "empresa_operativa_id": (
                empresa_operativa.pk
            ),
            "motivo": motivo,
            "iniciado_en": momento.isoformat(),
        },
    )

    messages.success(
        request,
        (
            f"Modo soporte activo para "
            f"{empresa_saas.nombre}."
        ),
    )

    return redirect("inicio")


@soporte_sastre_required
@require_POST
def soporte_salir_empresa(request):
    from .tenant_context import (
        obtener_contexto_soporte,
    )

    contexto = obtener_contexto_soporte(
        request
    )

    empresa_saas = (
        contexto["empresa_saas"]
        if contexto
        else None
    )

    empresa_id = (
        empresa_saas.pk
        if empresa_saas
        else None
    )

    if empresa_saas:
        _registrar_evento(
            empresa_saas,
            request,
            "ACCESO_SOPORTE_FINALIZADO",
            (
                f"Acceso de soporte finalizado por "
                f"{request.user.get_username()}."
            ),
            datos={
                "motivo": contexto.get(
                    "motivo",
                    "",
                ),
                "iniciado_en": contexto.get(
                    "iniciado_en"
                ),
                "finalizado_en": (
                    timezone.now().isoformat()
                ),
            },
        )

    limpiar_contexto_soporte(request)

    messages.success(
        request,
        "Modo soporte finalizado.",
    )

    if empresa_id:
        return redirect(
            "soporte_empresa_detalle",
            empresa_id=empresa_id,
        )

    return redirect(
        "soporte_empresas"
    )
