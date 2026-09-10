from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import EventoSuscripcion
from .tenant_context import (
    contexto_soporte_activo,
    obtener_contexto_soporte,
    limpiar_contexto_soporte,
)


METODOS_ESCRITURA = {
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
}


CAMPOS_SENSIBLES = {
    "password",
    "password1",
    "password2",
    "csrfmiddlewaretoken",
    "token",
    "codigo",
    "codigo_validacion",
    "secret",
}


class SoporteSastreMiddleware:
    """
    Seguridad transversal del modo soporte.

    - limita duración del contexto;
    - mantiene trazabilidad de operaciones de escritura;
    - nunca registra contraseñas ni tokens;
    - no afecta usuarios normales.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        contexto = None

        try:
            if contexto_soporte_activo(request):
                contexto = obtener_contexto_soporte(
                    request
                )
        except Exception:
            limpiar_contexto_soporte(request)
            contexto = None

        if contexto:
            expirado = self._esta_expirado(
                contexto
            )

            if expirado:
                empresa_saas = contexto[
                    "empresa_saas"
                ]

                self._registrar(
                    request=request,
                    empresa_saas=empresa_saas,
                    tipo="ACCESO_SOPORTE_EXPIRADO",
                    descripcion=(
                        "El modo soporte terminó "
                        "automáticamente por tiempo."
                    ),
                    datos={
                        "iniciado_en": contexto.get(
                            "iniciado_en"
                        ),
                    },
                )

                limpiar_contexto_soporte(
                    request
                )

                messages.warning(
                    request,
                    (
                        "La sesión de soporte expiró "
                        "por seguridad."
                    ),
                )

                return redirect(
                    "soporte_empresa_detalle",
                    empresa_id=empresa_saas.pk,
                )

            request.sastre_soporte_contexto = (
                contexto
            )

        response = self.get_response(
            request
        )

        if (
            contexto
            and request.method
            in METODOS_ESCRITURA
            and not request.path.startswith(
                "/sastre-admin/"
            )
        ):
            self._registrar_operacion(
                request,
                response,
                contexto,
            )

        return response

    def _esta_expirado(self, contexto):
        minutos = getattr(
            settings,
            "SASTRE_SUPPORT_SESSION_MINUTES",
            60,
        )

        iniciado_raw = contexto.get(
            "iniciado_en"
        )

        if not iniciado_raw:
            return True

        iniciado = parse_datetime(
            iniciado_raw
        )

        if iniciado is None:
            return True

        if timezone.is_naive(iniciado):
            iniciado = timezone.make_aware(
                iniciado
            )

        limite = iniciado + timedelta(
            minutes=minutos
        )

        return timezone.now() >= limite

    def _registrar_operacion(
        self,
        request,
        response,
        contexto,
    ):
        empresa_saas = contexto[
            "empresa_saas"
        ]

        resolver = getattr(
            request,
            "resolver_match",
            None,
        )

        nombre_vista = (
            resolver.view_name
            if resolver
            else ""
        )

        campos = []

        if hasattr(request, "POST"):
            campos = sorted(
                campo
                for campo in request.POST.keys()
                if campo.lower()
                not in CAMPOS_SENSIBLES
            )

        self._registrar(
            request=request,
            empresa_saas=empresa_saas,
            tipo="ACCION_SOPORTE",
            descripcion=(
                f"{request.method} "
                f"{request.path}"
            ),
            datos={
                "metodo": request.method,
                "ruta": request.path,
                "vista": nombre_vista,
                "status_http": (
                    response.status_code
                ),
                "campos_modificados": campos,
                "motivo_soporte": (
                    contexto.get(
                        "motivo",
                        "",
                    )
                ),
                "empresa_operativa_id": (
                    contexto[
                        "empresa_operativa"
                    ].pk
                ),
            },
        )

    def _registrar(
        self,
        *,
        request,
        empresa_saas,
        tipo,
        descripcion,
        datos,
    ):
        EventoSuscripcion.objects.create(
            empresa=empresa_saas,
            suscripcion=getattr(
                empresa_saas,
                "suscripcion",
                None,
            ),
            tipo=tipo,
            descripcion=descripcion,
            usuario=request.user,
            datos=datos,
        )
