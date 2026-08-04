import csv
import io
import re
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from core.application.event_bus import event_bus
from comercial.domain.o2c_full_events import ExportacionO2CFinancieraGenerada
from comercial.api.finanzas import estados
from comercial.models import FacturaVenta, NotaCreditoVenta, NotaDebitoVenta, ReciboCobro, CesionFactoring

@dataclass(frozen=True)
class ExportacionDTO:
    nombre: str
    mime: str
    contenido: bytes
    filas: int

def _safe(value):
    text = str(value if value is not None else "")
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text

def _rows(empresa, tipo):
    if tipo in {"diario", "mayor", "balanza"}: return estados(empresa=empresa)[tipo]
    maps = {"facturas": (FacturaVenta, ("numero", "fecha", "estado", "total")), "notas_credito": (NotaCreditoVenta, ("numero", "estado", "total")), "notas_debito": (NotaDebitoVenta, ("numero", "estado", "total")), "cobros": (ReciboCobro, ("numero", "fecha", "metodo", "monto", "estado")), "factoring": (CesionFactoring, ("numero", "factor", "monto_cedido", "neto_recibido", "estado"))}
    if tipo not in maps: raise ValidationError("Exportación financiera no soportada.")
    model, fields = maps[tipo]
    return [dict(zip(fields, row)) for row in model.objects.filter(empresa=empresa).values_list(*fields).iterator(chunk_size=1000)]

def exportar(*, context, tipo, formato):
    if not context.usuario or not context.usuario.has_perm("comercial.exportar_cxc"): raise PermissionDenied
    rows = _rows(context.empresa, tipo); headers = list(rows[0]) if rows else ["sin_datos"]; formato = formato.lower(); nombre = re.sub(r"[^a-z0-9_-]", "_", f"{tipo}_{context.empresa.pk}")
    if formato == "csv":
        out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=headers); writer.writeheader(); writer.writerows([{k: _safe(v) for k, v in row.items()} for row in rows]); content = out.getvalue().encode("utf-8-sig"); mime, ext = "text/csv", "csv"
    elif formato == "xlsx":
        from openpyxl import Workbook
        book = Workbook(write_only=True); sheet = book.create_sheet("Reporte"); sheet.append(headers)
        for row in rows: sheet.append([_safe(row.get(header, "")) for header in headers])
        out = io.BytesIO(); book.save(out); content = out.getvalue(); mime, ext = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    elif formato == "pdf":
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.pdfgen.canvas import Canvas
        out = io.BytesIO(); canvas = Canvas(out, pagesize=landscape(letter)); canvas.setTitle(nombre); canvas.drawString(36, 570, f"SASTRE ERP · {tipo}"); y = 550
        for row in rows[:500]:
            canvas.drawString(36, y, " | ".join(_safe(row.get(header, ""))[:35] for header in headers)); y -= 12
            if y < 36: canvas.showPage(); y = 570
        canvas.save(); content = out.getvalue(); mime, ext = "application/pdf", "pdf"
    else: raise ValidationError("Formato no soportado.")
    registrar_evento(empresa=context.empresa, usuario=context.usuario, request=context.request, modulo="o2c", accion=EventoAuditoria.Accion.OTRO, descripcion="Exportación financiera generada.", datos_nuevos={"tipo": tipo, "formato": formato, "filas": len(rows)})
    event_bus.publish(ExportacionO2CFinancieraGenerada(empresa_id=context.empresa.pk, usuario_id=context.usuario.pk, agregado_tipo="comercial.exportacionfinanciera", agregado_id=tipo, referencia=nombre, clave_idempotente=f"export:{context.identificador_solicitud}:{tipo}:{formato}", payload={"schema_version": 1, "empresa_id": context.empresa.pk, "tipo": tipo, "formato": formato, "filas": len(rows)}))
    return ExportacionDTO(f"{nombre}.{ext}", mime, content, len(rows))
