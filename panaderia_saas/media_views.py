import mimetypes
from pathlib import Path, PurePosixPath

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404

from conduces.services import obtener_empresa_usuario


def _safe_name(value):
    if not value or "\x00" in value or "\\" in value:
        raise Http404
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise Http404
    return candidate.as_posix()


def _field_for_user(request, name):
    empresa = obtener_empresa_usuario(request)
    if empresa is None:
        raise Http404

    from activos.models import DocumentoActivo
    from comercial.models import ProductoComercial
    from comercial.models_o2c4 import EvidenciaEntrega
    from conduces.models import Empresa, Factura
    from documentos.models import Documento
    from nomina.models import PrestamoEmpleado, ReciboNomina
    from rrhh.models import DocumentoEmpleado, Empleado

    lookups = [
        (Empresa, "logo", {"pk": empresa.pk}, None),
        (Documento, "archivo", {"empresa": empresa}, None),
        (Empleado, "foto", {"empresa": empresa}, "rrhh.view_empleado"),
        (DocumentoEmpleado, "archivo", {"empresa": empresa}, "rrhh.view_documentoempleado"),
        (PrestamoEmpleado, "documento_soporte", {"empresa": empresa}, "nomina.view_prestamoempleado"),
        (ReciboNomina, "archivo", {"detalle__nomina__empresa": empresa}, "nomina.view_recibonomina"),
        (Factura, "xml_ecf", {"empresa": empresa}, "conduces.view_factura"),
        (Factura, "pdf_ecf_externo", {"empresa": empresa}, "conduces.view_factura"),
        (ProductoComercial, "imagen", {"empresa": empresa}, "comercial.view_productocomercial"),
        (EvidenciaEntrega, "archivo", {"entrega__empresa": empresa}, "comercial.view_evidenciaentrega"),
        (DocumentoActivo, "archivo", {"empresa": empresa}, "activos.view_documentoactivo"),
    ]
    for model, field_name, tenant_filter, permission in lookups:
        if permission and not request.user.has_perm(permission):
            continue
        obj = model.objects.filter(**tenant_filter, **{field_name: name}).only(field_name).first()
        if obj is not None:
            field = getattr(obj, field_name)
            if field and field.name == name:
                return field
    raise Http404


@login_required
def protected_media(request, media_path):
    name = _safe_name(media_path)
    field = _field_for_user(request, name)
    try:
        stream = field.storage.open(field.name, "rb")
    except (FileNotFoundError, OSError):
        raise Http404 from None
    content_type = mimetypes.guess_type(field.name)[0] or "application/octet-stream"
    response = FileResponse(
        stream,
        as_attachment=request.GET.get("download") == "1",
        filename=Path(field.name).name,
        content_type=content_type,
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
