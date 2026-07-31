from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import FileResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from conduces.services import obtener_empresa_usuario

from .forms import DocumentoForm, ReemplazoDocumentoForm
from .models import Documento, TipoDocumento
from .services import (
    anular_documento, crear_documento_asociado, reemplazar_documento,
    resolver_objeto_permitido,
)


def _empresa(request):
    empresa = obtener_empresa_usuario(request)
    if not empresa:
        messages.error(request, "Tu usuario no tiene una empresa asociada.")
        return None, redirect("inicio")
    return empresa, None


@login_required
def documentos_lista(request):
    empresa, salida = _empresa(request)
    if salida:
        return salida
    qs = Documento.objects.filter(empresa=empresa).select_related("tipo_documento", "creado_por")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(titulo__icontains=q) | Q(nombre_original__icontains=q))
    for campo in ("tipo_documento", "estado", "fecha_documento", "fecha_vencimiento"):
        valor = request.GET.get(campo, "")
        if valor:
            qs = qs.filter(**{campo: valor})
    return render(request, "documentos/documentos_lista.html", {
        "empresa": empresa, "documentos": qs, "q": q,
        "tipos": TipoDocumento.objects.filter(empresa=empresa, activo=True),
        "estados": Documento.Estado.choices,
    })


@login_required
def documentos_objeto(request, app_label, model, object_id):
    empresa, salida = _empresa(request)
    if salida:
        return salida
    try:
        objeto = resolver_objeto_permitido(
            empresa=empresa, app_label=app_label, model=model, object_id=object_id
        )
    except ValidationError:
        objeto = None
    if objeto is None:
        from django.http import Http404
        raise Http404
    if app_label.lower() == "compras" and model.lower() == "proveedor":
        return redirect("compras:detalle", pk=objeto.pk)
    return redirect("comercial:cliente_detalle", pk=objeto.pk)


@login_required
def documento_cargar(request, app_label, model, object_id):
    empresa, salida = _empresa(request)
    if salida:
        return salida
    try:
        objeto = resolver_objeto_permitido(empresa=empresa, app_label=app_label, model=model, object_id=object_id)
    except ValidationError:
        from django.http import Http404
        raise Http404
    form = DocumentoForm(request.POST or None, request.FILES or None, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        try:
            documento = crear_documento_asociado(
                empresa=empresa, objeto=objeto, usuario=request.user, request=request,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Documento cargado correctamente.")
            return redirect("documentos:detalle", pk=documento.pk)
    return render(request, "documentos/documento_form.html", {
        "empresa": empresa, "form": form, "objeto": objeto,
    })


@login_required
def documento_detalle(request, pk):
    empresa, salida = _empresa(request)
    if salida:
        return salida
    documento = get_object_or_404(
        Documento.objects.select_related("tipo_documento", "creado_por", "documento_anterior"),
        pk=pk, empresa=empresa,
    )
    return render(request, "documentos/documento_detalle.html", {
        "empresa": empresa, "documento": documento, "reemplazo_form": ReemplazoDocumentoForm(),
    })


@login_required
def documento_descargar(request, pk):
    empresa, salida = _empresa(request)
    if salida:
        return salida
    documento = get_object_or_404(Documento, pk=pk, empresa=empresa)
    registrar_evento(
        empresa=empresa, usuario=request.user, request=request, objeto=documento.content_object,
        modulo="documentos", accion=EventoAuditoria.Accion.DESCARGAR_DOCUMENTO,
        descripcion=f"Se descargó el documento «{documento.titulo}» (v{documento.version}).",
        datos_nuevos={"documento_id": documento.pk, "version": documento.version},
    )
    return FileResponse(documento.archivo.open("rb"), as_attachment=True, filename=documento.nombre_original)


@login_required
def documento_reemplazar(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    empresa, salida = _empresa(request)
    if salida:
        return salida
    documento = get_object_or_404(Documento, pk=pk, empresa=empresa)
    form = ReemplazoDocumentoForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            nuevo = reemplazar_documento(
                documento=documento, archivo=form.cleaned_data["archivo"],
                usuario=request.user, request=request,
            )
        except ValidationError as error:
            messages.error(request, "; ".join(error.messages))
        else:
            messages.success(request, "Documento reemplazado y versión anterior conservada.")
            return redirect("documentos:detalle", pk=nuevo.pk)
    else:
        messages.error(request, "Selecciona un archivo válido para reemplazar.")
    return redirect("documentos:detalle", pk=documento.pk)


@login_required
def documento_anular(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    empresa, salida = _empresa(request)
    if salida:
        return salida
    documento = get_object_or_404(Documento, pk=pk, empresa=empresa)
    try:
        anular_documento(documento=documento, usuario=request.user, request=request)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, "Documento anulado sin eliminar el archivo.")
    return redirect("documentos:detalle", pk=documento.pk)
