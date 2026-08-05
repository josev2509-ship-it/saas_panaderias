import csv
from html import escape
from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from contabilidad.models import (CuentaPorPagarEnterprise, FacturaProveedor,
                                 NotaCreditoProveedor,NotaDebitoProveedor,OrdenPago,RetencionProveedor)
from tesoreria.models import ConciliacionBancaria
from compras.models import (AdjudicacionCompra, ComparativoCompra, DevolucionCompra,
                            OfertaProveedor, OrdenCompraEnterprise, Proveedor,
                            ProcesoRFQ, RecepcionCompra)

RESOURCES={
    "rfq":(ProcesoRFQ,["numero","titulo","estado","fecha_limite"]),
    "ofertas":(OfertaProveedor,["numero","proveedor__razon_social","estado","moneda__moneda__codigo","total"]),
    "comparativos":(ComparativoCompra,["numero","estado","recomendacion","congelado_en"]),
    "adjudicaciones":(AdjudicacionCompra,["numero","tipo","estado","justificacion"]),
    "ordenes":(OrdenCompraEnterprise,["numero","proveedor__razon_social","estado","moneda__moneda__codigo","total"]),
    "recepciones":(RecepcionCompra,["numero","orden__numero","estado","fecha"]),
    "devoluciones":(DevolucionCompra,["numero","recepcion__numero","estado","fecha"]),
    "facturas":(FacturaProveedor,["numero","proveedor__razon_social","estado","moneda__moneda__codigo","total","vence_el"]),
    "cxp":(CuentaPorPagarEnterprise,["factura__numero","proveedor__razon_social","estado","moneda__moneda__codigo","saldo","bucket_aging"]),
    "aging":(CuentaPorPagarEnterprise,["proveedor__razon_social","moneda__moneda__codigo","vence_el","saldo","bucket_aging"]),
    "pagos":(OrdenPago,["numero","solicitud__cuenta__proveedor__razon_social","estado","solicitud__monto"]),
    "proveedores":(Proveedor,["codigo","razon_social","estado","nivel_riesgo","documentacion_completa"]),
    "conciliacion":(ConciliacionBancaria,["cuenta__banco","cuenta__numero_enmascarado","desde","hasta","saldo_banco","saldo_libros","estado"]),
    "ahorro":(OfertaProveedor,["numero","proveedor__razon_social","moneda__moneda__codigo","subtotal","descuento","total","estado"]),
    "cumplimiento":(OrdenCompraEnterprise,["numero","proveedor__razon_social","entrega_desde","entrega_hasta","estado","total"]),
    "notas_credito":(NotaCreditoProveedor,["numero","factura__numero","factura__proveedor__razon_social","monto","impuesto","retencion","estado"]),
    "notas_debito":(NotaDebitoProveedor,["numero","factura__numero","factura__proveedor__razon_social","monto","impuesto","estado"]),
    "retenciones_fiscales":(RetencionProveedor,["numero","proveedor__razon_social","tipo","base","tasa","monto","moneda__moneda__codigo","certificado__numero","estado","fecha","asiento_id","factura__numero"]),
}

def _safe(value):
    text=str(value if value is not None else "")
    return "'"+text if text[:1] in "=+-@" else text

def rows(*,empresa,recurso,estado=""):
    model,fields=RESOURCES[recurso];qs=model.objects.filter(empresa=empresa)
    if estado and any(f.name=="estado" for f in model._meta.fields):qs=qs.filter(estado=estado)
    return fields,[[ _safe(value) for value in row] for row in qs.order_by("pk").values_list(*fields)]

def render_export(*,context,recurso,formato,estado=""):
    fields,data=rows(empresa=context.empresa,recurso=recurso,estado=estado);headers=[x.replace("__"," · ").replace("_"," ").title() for x in fields];filename=f"p2p_{recurso}"
    if formato=="csv":
        response=HttpResponse(content_type="text/csv; charset=utf-8");response["Content-Disposition"]=f'attachment; filename="{filename}.csv"';writer=csv.writer(response);writer.writerow(headers);writer.writerows(data)
    elif formato=="xlsx":
        workbook=Workbook();sheet=workbook.active;sheet.title=recurso[:31];sheet.append(headers)
        for row in data:sheet.append(row)
        sheet.freeze_panes="A2";sheet.auto_filter.ref=sheet.dimensions
        for column in sheet.columns:sheet.column_dimensions[column[0].column_letter].width=min(45,max(12,max(len(str(cell.value or "")) for cell in column)+2))
        stream=BytesIO();workbook.save(stream);response=HttpResponse(stream.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");response["Content-Disposition"]=f'attachment; filename="{filename}.xlsx"'
    elif formato=="pdf":
        stream=BytesIO();doc=SimpleDocTemplate(stream,pagesize=landscape(A4),title=f"P2P {recurso}");table=Table([headers,*data],repeatRows=1);table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1f3a5f")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.grey),("FONTSIZE",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"TOP") ]));doc.build([Paragraph(f"SASTRE ERP · Purchase to Pay · {recurso.title()}",getSampleStyleSheet()["Title"]),table]);response=HttpResponse(stream.getvalue(),content_type="application/pdf");response["Content-Disposition"]=f'attachment; filename="{filename}.pdf"'
    elif formato=="print":
        head="".join(f"<th>{escape(x)}</th>" for x in headers);body="".join("<tr>"+"".join(f"<td>{escape(str(v))}</td>" for v in row)+"</tr>" for row in data);response=HttpResponse(f"<!doctype html><html><head><title>{filename}</title><style>table{{border-collapse:collapse}}th,td{{border:1px solid #999;padding:4px}}</style></head><body><h1>P2P · {recurso.title()}</h1><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table><script>window.print()</script></body></html>")
    else:raise ValueError("Formato no soportado.")
    registrar_evento(empresa=context.empresa,usuario=context.usuario,request=context.request,modulo="compras",accion=EventoAuditoria.Accion.OTRO,descripcion=f"Exportación P2P {recurso} en {formato}.",datos_nuevos={"recurso":recurso,"formato":formato,"filas":len(data)})
    return response
