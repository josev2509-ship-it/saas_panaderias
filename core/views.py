from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
from django.utils import timezone

from conduces.services import obtener_empresa_usuario
from inventario.engine import (
    InventoryEngine, diagnosticar_producto, vista_previa_reconstruccion,
)
from comercial.models import SecuenciaDocumento

from .application.operation_context import OperationContext
from .forms import (
    AccionIdempotenciaForm, DiagnosticoProductoForm, ReconstruccionSaldoForm,
    ReintentoEventoForm, SecuenciaDocumentoCreateForm, SecuenciaDocumentoForm,
    TechnicalFilterForm,
)
from .models import ConciliacionInventario, EventoDominio, RegistroIdempotencia
from .application.event_bus import event_bus
from .application.idempotency import begin, complete, fail
from .application.request_idempotency import resolve_idempotency_context
from .infrastructure.audit_adapter import audit_event_retry


def _empresa(request):
    return obtener_empresa_usuario(request)


@login_required
@permission_required("core.view_transaction_engine", raise_exception=True)
def motor_dashboard(request):
    empresa = _empresa(request)
    idempotencias = RegistroIdempotencia.objects.filter(empresa=empresa)
    eventos = EventoDominio.objects.filter(empresa=empresa)
    conciliaciones = ConciliacionInventario.objects.filter(empresa=empresa)
    secuencias = SecuenciaDocumento.objects.filter(empresa=empresa)
    stale_cutoff = timezone.now() - timezone.timedelta(
        seconds=settings.CORE_IDEMPOTENCY_STALE_SECONDS
    )
    return render(request, "core/motor_dashboard.html", {
        "idempotencias": idempotencias.order_by("-fecha_inicio")[:10],
        "eventos_error": eventos.filter(estado=EventoDominio.Estado.ERROR)[:10],
        "conciliaciones": conciliaciones[:10],
        "metricas": {
            "idem_iniciadas": idempotencias.filter(estado="INICIADA").count(),
            "idem_completadas": idempotencias.filter(estado="COMPLETADA").count(),
            "idem_fallidas": idempotencias.filter(estado="FALLIDA").count(),
            "idem_abandonadas": idempotencias.filter(
                estado="INICIADA", fecha_inicio__lt=stale_cutoff
            ).count(),
            "eventos_pendientes": eventos.filter(estado="PENDIENTE").count(),
            "eventos_procesando": eventos.filter(estado="PROCESANDO").count(),
            "eventos_procesados": eventos.filter(estado="PROCESADO").count(),
            "eventos_error": eventos.filter(estado="ERROR").count(),
            "eventos_agotados": eventos.filter(estado="AGOTADO").count(),
            "conciliaciones_diferencia": conciliaciones.filter(estado="DIFERENCIA").count(),
            "conciliaciones_corregidas": conciliaciones.filter(estado="CORREGIDA").count(),
            "productos_inconsistentes": conciliaciones.filter(
                estado__in=["DIFERENCIA", "REQUIERE_INTERVENCION"]
            ).values("producto_id").distinct().count(),
            "secuencias_activas": secuencias.filter(activo=True).count(),
            "secuencias_inactivas": secuencias.filter(activo=False).count(),
        },
    })


def _filtered_page(request, queryset, search_fields):
    form = TechnicalFilterForm(request.GET)
    if form.is_valid():
        data = form.cleaned_data
        if data.get("q"):
            query = Q()
            for field in search_fields:
                query |= Q(**{f"{field}__icontains": data["q"]})
            queryset = queryset.filter(query)
        if data.get("estado") and any(f.name == "estado" for f in queryset.model._meta.fields):
            queryset = queryset.filter(estado=data["estado"])
        if data.get("operacion") and any(f.name == "operacion" for f in queryset.model._meta.fields):
            queryset = queryset.filter(operacion__icontains=data["operacion"])
        date_fields = {
            "RegistroIdempotencia": "fecha_inicio",
            "EventoDominio": "fecha_creacion",
            "ConciliacionInventario": "fecha",
            "SecuenciaDocumento": "fecha_actualizacion",
        }
        date_field = date_fields.get(queryset.model.__name__)
        if data.get("fecha_desde"):
            queryset = queryset.filter(**{f"{date_field}__date__gte": data["fecha_desde"]})
        if data.get("fecha_hasta"):
            queryset = queryset.filter(**{f"{date_field}__date__lte": data["fecha_hasta"]})
    return Paginator(queryset, 25).get_page(request.GET.get("page")), form


@login_required
@permission_required("core.view_registroidempotencia", raise_exception=True)
def idempotencias_lista(request):
    page, form = _filtered_page(
        request, RegistroIdempotencia.objects.filter(empresa=_empresa(request)).order_by("-fecha_inicio"),
        ("clave", "operacion", "referencia"),
    )
    return render(request, "core/lista_tecnica.html", {
        "titulo": "Idempotencia",
        "objetos": page, "filtro": form, "detalle_url": "core:idempotencia_detalle",
    })


@login_required
@permission_required("core.view_registroidempotencia", raise_exception=True)
def idempotencia_detalle(request, pk):
    objeto = get_object_or_404(RegistroIdempotencia, pk=pk, empresa=_empresa(request))
    return render(request, "core/detalle_tecnico.html", {
        "titulo": "Detalle de idempotencia",
        "objeto": objeto, "tipo_objeto": "idempotencia",
        "accion_form": AccionIdempotenciaForm(),
    })


@login_required
@permission_required("core.view_eventodominio", raise_exception=True)
def eventos_lista(request):
    page, form = _filtered_page(
        request, EventoDominio.objects.filter(empresa=_empresa(request)).order_by("-fecha_creacion"),
        ("tipo_evento", "referencia", "agregado_id"),
    )
    return render(request, "core/lista_tecnica.html", {
        "titulo": "Eventos de dominio",
        "objetos": page, "filtro": form, "detalle_url": "core:evento_detalle",
    })


@login_required
@permission_required("core.view_eventodominio", raise_exception=True)
def evento_detalle(request, pk):
    objeto = get_object_or_404(EventoDominio, pk=pk, empresa=_empresa(request))
    return render(request, "core/detalle_tecnico.html", {
        "titulo": "Detalle de evento",
        "objeto": objeto, "tipo_objeto": "evento",
        "accion_form": ReintentoEventoForm(),
    })


@login_required
@permission_required("core.view_eventodominio", raise_exception=True)
def eventos_fallidos(request):
    return render(request, "core/lista_tecnica.html", {
        "titulo": "Fallos de eventos",
        "objetos": EventoDominio.objects.filter(
            empresa=_empresa(request), estado=EventoDominio.Estado.ERROR
        ).order_by("-fecha_creacion"),
        "detalle_url": "core:evento_detalle",
    })


@login_required
@permission_required("core.retry_eventodominio", raise_exception=True)
def evento_reintentar(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    empresa = _empresa(request)
    event = get_object_or_404(EventoDominio, pk=pk, empresa=empresa)
    form = ReintentoEventoForm(request.POST)
    if form.is_valid():
        context = OperationContext(
            empresa=empresa, usuario=request.user, request=request,
            **resolve_idempotency_context(
                request, operation="core.retry_domain_event",
                reference=event.referencia,
            ),
        )
        record, execute = begin(
            context=context, operation="core.retry_domain_event",
            payload={"evento_id": event.pk, "motivo": form.cleaned_data["motivo"]},
        )
        if execute:
            try:
                result = event_bus.retry(event.pk)
                audit_event_retry(
                    context=context, module="core", obj=result,
                    description=f"Reintento del evento {event.pk}.",
                    before={"estado": EventoDominio.Estado.ERROR},
                    after={"estado": result.estado, "motivo": form.cleaned_data["motivo"]},
                )
                complete(record, result.pk)
                messages.success(request, "El evento fue reintentado.")
            except Exception as exc:
                fail(record, exc)
                raise
    return redirect("core:eventos_fallidos")


@login_required
@permission_required("core.retry_registroidempotencia", raise_exception=True)
def idempotencia_cerrar(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    empresa = _empresa(request)
    record = get_object_or_404(
        RegistroIdempotencia, pk=pk, empresa=empresa,
        estado__in=[
            RegistroIdempotencia.Estado.INICIADA,
            RegistroIdempotencia.Estado.FALLIDA,
        ],
    )
    form = AccionIdempotenciaForm(request.POST)
    if form.is_valid():
        context = OperationContext(
            empresa=empresa, usuario=request.user, request=request,
            **resolve_idempotency_context(
                request, operation="core.close_idempotency", reference=record.referencia,
            ),
        )
        action_record, execute = begin(
            context=context, operation="core.close_idempotency",
            payload={"record_id": record.pk, "motivo": form.cleaned_data["motivo"]},
        )
        if execute:
            try:
                before = record.estado
                record.estado = RegistroIdempotencia.Estado.FALLIDA
                record.mensaje_error = form.cleaned_data["motivo"]
                record.fecha_finalizacion = timezone.now()
                record.save(update_fields=["estado", "mensaje_error", "fecha_finalizacion"])
                from .infrastructure.audit_adapter import audit_update
                audit_update(
                    context=context, module="core", obj=record,
                    description=f"Cierre controlado de idempotencia {record.pk}.",
                    before={"estado": before},
                    after={"estado": record.estado, "motivo": form.cleaned_data["motivo"]},
                )
                complete(action_record, record.pk)
            except Exception as exc:
                fail(action_record, exc)
                raise
        messages.success(request, "La operacion fue cerrada de forma controlada.")
    return redirect("core:idempotencia_detalle", pk=pk)


@login_required
@permission_required("core.manage_document_sequences", raise_exception=True)
def secuencias_lista(request):
    return render(request, "core/lista_tecnica.html", {
        "titulo": "Secuencias documentales",
        "objetos": SecuenciaDocumento.objects.filter(
            empresa=_empresa(request)
        ).order_by("tipo", "-periodo"),
        "detalle_url": "core:secuencia_detalle",
        "crear_url": "core:secuencia_crear",
    })


@login_required
@permission_required("core.manage_document_sequences", raise_exception=True)
def secuencia_detalle(request, pk):
    sequence = get_object_or_404(SecuenciaDocumento, pk=pk, empresa=_empresa(request))
    from .application.numbering import vista_previa_numero
    return render(request, "core/detalle_tecnico.html", {
        "titulo": "Secuencia documental", "objeto": sequence,
        "tipo_objeto": "secuencia",
        "proximo_numero": vista_previa_numero(
            empresa=sequence.empresa, tipo_documento=sequence.tipo,
            prefijo=sequence.prefijo, longitud=sequence.longitud,
        ),
    })


@login_required
@permission_required("core.manage_document_sequences", raise_exception=True)
def secuencia_crear(request):
    empresa = _empresa(request)
    if request.method == "POST":
        form = SecuenciaDocumentoCreateForm(request.POST)
        if form.is_valid():
            sequence = form.save(commit=False)
            sequence.empresa = empresa
            sequence.creado_por = request.user
            sequence.actualizado_por = request.user
            sequence.save()
            messages.success(request, "Secuencia creada.")
            return redirect("core:secuencia_detalle", pk=sequence.pk)
    else:
        form = SecuenciaDocumentoCreateForm()
    return render(request, "core/form_tecnico.html", {
        "titulo": "Crear secuencia", "form": form,
    })


@login_required
@permission_required("core.manage_document_sequences", raise_exception=True)
def secuencia_editar(request, pk):
    empresa = _empresa(request)
    sequence = get_object_or_404(SecuenciaDocumento, pk=pk, empresa=empresa)
    if request.method == "POST":
        form = SecuenciaDocumentoForm(request.POST, instance=sequence)
        if form.is_valid():
            sequence = form.save(commit=False)
            sequence.actualizado_por = request.user
            sequence.save()
            messages.success(request, "Secuencia actualizada.")
            return redirect("core:secuencia_detalle", pk=pk)
    else:
        form = SecuenciaDocumentoForm(instance=sequence)
    return render(request, "core/form_tecnico.html", {"titulo": "Configurar secuencia", "form": form})


@login_required
@permission_required("core.view_conciliacioninventario", raise_exception=True)
def conciliaciones_lista(request):
    return render(request, "core/lista_tecnica.html", {
        "titulo": "Conciliaciones",
        "objetos": ConciliacionInventario.objects.filter(empresa=_empresa(request)),
        "detalle_url": "core:conciliacion_detalle",
        "diagnostico_form": DiagnosticoProductoForm(empresa=_empresa(request)),
    })


@login_required
@permission_required("core.view_conciliacioninventario", raise_exception=True)
def conciliacion_detalle(request, pk):
    return render(request, "core/detalle_tecnico.html", {
        "titulo": "Detalle de conciliacion",
        "objeto": get_object_or_404(ConciliacionInventario, pk=pk, empresa=_empresa(request)),
        "tipo_objeto": "conciliacion",
    })


@login_required
@permission_required("core.run_inventory_diagnosis", raise_exception=True)
def diagnostico_producto(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    empresa = _empresa(request)
    form = DiagnosticoProductoForm(request.POST, empresa=empresa)
    if form.is_valid():
        context = OperationContext(empresa=empresa, usuario=request.user, request=request)
        diagnosticar_producto(context=context, producto=form.cleaned_data["producto"])
        messages.success(request, "Diagnostico completado.")
    return redirect("core:conciliaciones")


@login_required
@permission_required("core.rebuild_inventory_balance", raise_exception=True)
def reconstruir_saldo(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    empresa = _empresa(request)
    form = ReconstruccionSaldoForm(request.POST, empresa=empresa)
    if form.is_valid():
        context = OperationContext(
            empresa=empresa, usuario=request.user, request=request,
            **resolve_idempotency_context(
                request, operation="core.rebuild_inventory_balance",
                reference=f"producto:{form.cleaned_data['producto'].pk}",
            ),
        )
        InventoryEngine.rebuild_cached_balance(
            context=context, producto=form.cleaned_data["producto"],
            motivo=form.cleaned_data["motivo"],
        )
        messages.success(request, "Reconstruccion procesada.")
    return redirect("core:conciliaciones")


@login_required
@permission_required("core.rebuild_inventory_balance", raise_exception=True)
def previsualizar_saldo(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    empresa = _empresa(request)
    form = DiagnosticoProductoForm(request.POST, empresa=empresa)
    if not form.is_valid():
        messages.error(request, "Seleccione un producto valido.")
        return redirect("core:conciliaciones")
    context = OperationContext(empresa=empresa, usuario=request.user, request=request)
    preview = vista_previa_reconstruccion(
        context=context, producto=form.cleaned_data["producto"]
    )
    return render(request, "core/reconstruccion_preview.html", {
        "producto": form.cleaned_data["producto"],
        "preview": preview,
        "form": ReconstruccionSaldoForm(
            initial={"producto": form.cleaned_data["producto"]}, empresa=empresa
        ),
    })
