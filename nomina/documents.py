from io import BytesIO
from decimal import Decimal
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from django.utils import timezone

from .models import PlantillaDocumentoRRHH, ReciboNomina
from .loan_services import loan_totals


def _money(value):
    return f"RD$ {value:,.2f}"


def _template(empresa, kind):
    return PlantillaDocumentoRRHH.objects.filter(empresa=empresa, tipo=kind, activo=True).first()


class _NumberedCanvas(canvas.Canvas):
    """Adds stable Page X of Y numbering after ReportLab knows the final count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#526079"))
            self.drawRightString(self._pagesize[0] - 14 * mm, 7 * mm, f"Página {self._pageNumber} de {total}")
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)


def _build_pdf(title, empresa, story, *, landscape_page=False):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4) if landscape_page else A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm, title=title)
    styles = getSampleStyleSheet()
    company_line = f"RNC: {empresa.rnc or '—'}"
    if getattr(empresa, "direccion", ""):
        company_line += f" · {empresa.direccion}"
    header = [Paragraph(f"<b>{empresa.nombre}</b>", styles["Title"]), Paragraph(company_line, styles["Normal"]), Paragraph(title, styles["Heading2"]), Spacer(1, 5 * mm)]
    doc.build(header + story, canvasmaker=_NumberedCanvas)
    return output.getvalue()


def _styled_table(rows, widths=None, font_size=8):
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#b8c2cc")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
    ]))
    return table


def payslip_pdf(detail):
    snap, employee, period = detail.snapshot, detail.snapshot["employee"], detail.snapshot["period"]
    template = _template(detail.nomina.empresa, "VOLANTE")
    styles = getSampleStyleSheet()
    income_rows = [["Ingresos", "Monto"], ["Salario", _money(detail.salario_periodo)], ["Horas extra", _money(detail.horas_extra)], ["Otros ingresos", _money(detail.otros_ingresos)], ["Total bruto", _money(detail.ingresos)]]
    deduction_rows = [["Deducciones empleado", "Monto"], ["AFP/SVDS", _money(detail.afp_empleado)], ["SFS", _money(detail.sfs_empleado)], ["ISR", _money(detail.isr)], ["Otros descuentos", _money(detail.otros_descuentos)], ["Total deducciones", _money(detail.deducciones)]]
    loan_notes = []
    for line in detail.lineas.filter(snapshot__fuente="prestamo"):
        s = line.snapshot
        loan_notes.append(Paragraph(f"Préstamo empleado · Cuota {s.get('numero')}/{s.get('total')} &nbsp;&nbsp; <b>{_money(line.monto)}</b><br/>Saldo pendiente después de esta cuota: {_money(Decimal(s.get('saldo_posterior', '0')))}", styles["Normal"]))
    story = [Paragraph(template.encabezado, styles["Normal"]) if template and template.encabezado else Spacer(1, 1), Paragraph(f"Nómina: {detail.nomina.numero} · Período: {period['desde']} a {period['hasta']}", styles["Normal"]), Paragraph(f"Empleado: {employee['nombre']} · Código: {employee['codigo']} · Cédula: {employee['identificacion']}", styles["Normal"]), Paragraph(f"Puesto: {employee['puesto']} · Ingreso: {employee['fecha_ingreso']} · Salario mensual: {_money(Decimal(employee['salario_mensual']))}", styles["Normal"]), Spacer(1, 4 * mm), _styled_table(income_rows, [110 * mm, 55 * mm]), Spacer(1, 4 * mm), _styled_table(deduction_rows, [110 * mm, 55 * mm]), Spacer(1, 3 * mm)] + loan_notes + [Spacer(1, 5 * mm), Paragraph(f"<b>NETO A PAGAR: {_money(detail.neto)}</b>", styles["Heading2"]), Paragraph((template.pie if template else "") or "Documento privado generado desde el snapshot histórico de la nómina.", styles["Normal"])]
    ReciboNomina.objects.update_or_create(detalle=detail, defaults={"numero": f"VOL-{detail.nomina.numero}-{employee['codigo']}", "snapshot": snap})
    return _build_pdf("Volante de pago", detail.nomina.empresa, story)


def payroll_pdf(payroll):
    styles = getSampleStyleSheet()
    rows = [["Empleado", "Bruto", "AFP", "SFS", "ISR", "Otros desc.", "Neto"]]
    for detail in payroll.detalles.select_related("empleado").order_by("empleado__apellidos"):
        rows.append([f"{detail.empleado.codigo} · {detail.empleado.nombres} {detail.empleado.apellidos}", _money(detail.ingresos), _money(detail.afp_empleado), _money(detail.sfs_empleado), _money(detail.isr), _money(detail.otros_descuentos), _money(detail.neto)])
    rows.append(["TOTALES", _money(payroll.total_ingresos), _money(payroll.total_afp), _money(payroll.total_sfs), _money(payroll.total_isr), _money(payroll.total_otros_descuentos), _money(payroll.total_neto)])
    details = list(payroll.detalles.select_related("empleado").order_by("empleado__apellidos"))
    story = [Paragraph(f"Referencia: {payroll.numero} · Estado: {payroll.estado}", styles["Normal"]), Paragraph(f"Período: {payroll.periodo.desde} a {payroll.periodo.hasta}", styles["Normal"]), Spacer(1, 4 * mm), _styled_table(rows, font_size=7)]
    incomes = [["Empleado", "Horas extra", "Otros ingresos", "Total adicional"]] + [[f"{d.empleado.codigo} · {d.empleado.nombres} {d.empleado.apellidos}", _money(d.horas_extra), _money(d.otros_ingresos), _money(d.horas_extra+d.otros_ingresos)] for d in details if d.horas_extra or d.otros_ingresos]
    if len(incomes) > 1:
        story += [PageBreak(), Paragraph("OTROS INGRESOS", styles["Heading2"]), _styled_table(incomes)]
    discounts = [["Empleado", "Otros descuentos", "AFP", "SFS", "ISR"]] + [[f"{d.empleado.codigo} · {d.empleado.nombres} {d.empleado.apellidos}", _money(d.otros_descuentos), _money(d.afp_empleado), _money(d.sfs_empleado), _money(d.isr)] for d in details if d.otros_descuentos]
    if len(discounts) > 1:
        story += [PageBreak(), Paragraph("OTROS DESCUENTOS", styles["Heading2"]), _styled_table(discounts)]
    obligations = [["RESUMEN DE OBLIGACIONES", "Monto"], ["AFP trabajadores", _money(payroll.total_afp)], ["SFS trabajadores", _money(payroll.total_sfs)], ["ISR", _money(payroll.total_isr)], ["Aportes patronales TSS/INFOTEP", _money(payroll.total_aportes_patronales)], ["Neto a pagar", _money(payroll.total_neto)], ["Costo total empresa", _money(payroll.total_ingresos + payroll.total_aportes_patronales)]]
    story += [PageBreak(), Paragraph("RESUMEN DE OBLIGACIONES", styles["Heading2"]), _styled_table(obligations, [105 * mm, 55 * mm])]
    return _build_pdf("Resumen consolidado de nómina", payroll.empresa, story, landscape_page=True)


def payslips_zip(payroll):
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for detail in payroll.detalles.select_related("empleado"):
            archive.writestr(f"{detail.empleado.codigo}-{payroll.numero}.pdf", payslip_pdf(detail))
    return output.getvalue()


def payroll_xlsx(payroll):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Nómina RD"
    sheet.append(["Código", "Cédula", "Empleado", "Cargo", "Fecha ingreso", "Salario período", "Horas extra", "Otros ingresos", "Bruto", "AFP trabajador", "SFS trabajador", "ISR", "Otros descuentos", "SFS empleador", "SVDS empleador", "SRL", "INFOTEP", "Total descuentos", "Neto período", "Costo patronal"])
    for d in payroll.detalles.select_related("empleado__puesto"):
        e = d.empleado
        sheet.append([e.codigo, e.identificacion, f"{e.nombres} {e.apellidos}", e.puesto.nombre, e.fecha_ingreso, d.salario_periodo, d.horas_extra, d.otros_ingresos, d.ingresos, d.afp_empleado, d.sfs_empleado, d.isr, d.otros_descuentos, d.sfs_empleador, d.svds_empleador, d.srl_empleador, d.infotep_empleador, d.deducciones, d.neto, d.aportes])
    sheet.freeze_panes = "A2"
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = min(max(len(str(c.value or "")) for c in column) + 2, 30)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def settlement_pdf(settlement, *, letter=False):
    styles = getSampleStyleSheet()
    employee = settlement.snapshot["employee"]
    title = "Carta de liquidación" if letter else "Cálculo de Prestaciones Laborales y Derechos Adquiridos"
    template = _template(settlement.empresa, "LIQUIDACION" if letter else "PRESTACIONES")
    if letter:
        body = (template.cuerpo if template and template.cuerpo else "Por medio de la presente se entrega el desglose de prestaciones laborales y derechos adquiridos calculados con la información registrada.")
        story = [Paragraph(f"Fecha: {settlement.fecha}", styles["Normal"]), Spacer(1, 4 * mm), Paragraph(f"Señor(a): {employee['nombre']} · Cédula {employee['identificacion']}", styles["Normal"]), Spacer(1, 5 * mm), Paragraph(body, styles["BodyText"]), Spacer(1, 6 * mm), Paragraph(f"Total calculado: <b>{_money(settlement.total)}</b>", styles["Heading2"]), Spacer(1, 15 * mm), Paragraph(f"{(template.firmante if template else '') or 'Responsable de RRHH'}<br/>{(template.cargo_firmante if template else '')}", styles["Normal"])]
    else:
        rows = [["Concepto", "Días", "Base", "Fórmula", "Monto", "Referencia"]]
        for item in settlement.prestaciones.all():
            rows.append([item.tipo, str(item.dias), _money(item.base), item.formula, _money(item.monto), item.referencia_legal])
        rows.append(["TOTAL", "", "", "", _money(settlement.total), ""])
        story = [Paragraph(f"Empleado: {employee['nombre']} · Cédula: {employee['identificacion']} · Código: {employee['codigo']}", styles["Normal"]), Paragraph(f"Ingreso: {employee['fecha_ingreso']} · Salida: {settlement.fecha_salida} · Tipo: {settlement.tipo_terminacion}", styles["Normal"]), Paragraph(f"Salario promedio: {_money(settlement.salario_promedio)} · Salario diario: {_money(settlement.salario_diario)}", styles["Normal"]), Spacer(1, 4 * mm), _styled_table(rows, font_size=7), Spacer(1, 4 * mm), Paragraph(settlement.motivo_revision or "Cálculo automático sujeto a verificación de la información registrada.", styles["Normal"])]
    return _build_pdf(title, settlement.empresa, story, landscape_page=not letter)


def loan_statement_pdf(loan):
    styles = getSampleStyleSheet()
    totals = loan_totals(loan)
    rows = [["Nómina", "Fecha", "Cuota", "Monto", "Saldo resultante"]]
    for item in loan.cuotas_detalle.filter(estado="APLICADA").select_related("nomina").order_by("numero"):
        rows.append([item.nomina.numero, str(item.fecha or "—"), f"{item.numero}/{loan.cuotas}", _money(item.monto), _money(item.saldo_posterior)])
    if len(rows) == 1:
        rows.append(["—", "—", "Sin cuotas aplicadas", _money(0), _money(loan.saldo)])
    story = [Paragraph(f"Empleado: <b>{loan.empleado.nombres} {loan.empleado.apellidos}</b> · Código {loan.empleado.codigo}", styles["Normal"]),
             Paragraph(f"Préstamo: {loan.codigo} · Monto original: {_money(loan.principal)} · Cuota: {_money(loan.monto_cuota)}", styles["Normal"]),
             Paragraph(f"Cuotas pagadas: {totals['cuotas_pagadas']} · Pendientes: {totals['cuotas_pendientes']} · Total pagado: {_money(totals['pagado'])} · Saldo: <b>{_money(loan.saldo)}</b>", styles["Normal"]),
             Spacer(1, 5 * mm), _styled_table(rows, [42*mm, 30*mm, 30*mm, 35*mm, 38*mm])]
    return _build_pdf("Estado de préstamo", loan.empresa, story)


def employee_document_pdf(employee, kind, *, document_request=None):
    styles = getSampleStyleSheet()
    template = _template(employee.empresa, kind)
    labels = {"CONTRATO": "Contrato individual de trabajo", "TEMPORAL": "Contrato individual de trabajo por tiempo determinado", "LABORAL": "Certificación laboral", "CONSULAR": "Carta para fines consulares", "BANCARIA": "Carta dirigida a entidad financiera", "ANEXO": "Anexo de funciones", "EXPEDIENTE": "Expediente ejecutivo del empleado"}
    metadata = document_request.snapshot if document_request else {}
    values = {"empresa": employee.empresa.nombre, "rnc": employee.empresa.rnc or "—", "direccion_empresa": employee.empresa.direccion or "—", "empleado": f"{employee.nombres} {employee.apellidos}", "identificacion": employee.identificacion, "codigo_empleado": employee.codigo, "puesto": employee.puesto.nombre, "departamento": employee.departamento.nombre, "lugar_trabajo": employee.centro.nombre, "salario": _money(employee.salario), "fecha_ingreso": str(employee.fecha_ingreso), "tipo_contrato": employee.tipo_contrato or "No especificado", "entidad_financiera": metadata.get("entidad", ""), "destinatario": metadata.get("destinatario", ""), "proposito": metadata.get("proposito", "")}
    body = (template.cuerpo if template and template.cuerpo else "Documento emitido a solicitud de la parte interesada con base en la información laboral registrada.")
    for key, value in values.items():
        body = body.replace("{{" + key + "}}", str(value))
    recipient = metadata.get("entidad") or metadata.get("destinatario") or "A quien pueda interesar"
    story = [Paragraph(f"Santo Domingo, República Dominicana · {timezone.localdate()}", styles["Normal"]), Spacer(1, 5*mm), Paragraph(f"<b>Señores:</b><br/>{recipient}<br/><b>Asunto:</b> {labels.get(kind, 'Documento laboral')}", styles["BodyText"]), Spacer(1, 5*mm), Paragraph(body.replace("\n", "<br/>"), styles["BodyText"])]
    if kind in {"CONTRATO", "TEMPORAL"}:
        contract = employee.contratos.filter(empresa=employee.empresa).order_by("-version", "-inicio").first()
        end = contract.fin if contract else None
        reason = contract.motivo_temporal if contract else ""
        base = f"{employee.empresa.nombre}, RNC {employee.empresa.rnc or '—'}, y {values['empleado']}, identificación {employee.identificacion}"
        items = [
            ("COMPARECENCIA",f"Comparecen {base}, quienes declaran capacidad y voluntad para contratar."),("CONSIDERANDOS","Las partes reconocen la relación laboral, la información registrada y el deber de buena fe."),("OBJETO",contract.objeto if contract and contract.objeto else f"Prestación de servicios personales como {employee.puesto.nombre}."),("CARGO",f"El cargo es {employee.puesto.nombre}, sujeto a la descripción vigente."),("FUNCIONES","Las funciones, responsabilidades e indicadores constan en el Anexo I."),("DEPARTAMENTO Y DEPENDENCIA",f"Pertenece a {employee.departamento.nombre} y reporta a {employee.supervisor or 'la autoridad designada'}."),("LUGAR DE TRABAJO",contract.lugar_prestacion if contract and contract.lugar_prestacion else f"{employee.centro.nombre}, {employee.centro.direccion or employee.empresa.direccion or 'domicilio registrado'}."),("MODALIDAD",employee.tipo_contrato or (contract.tipo if contract else "INDEFINIDO")),
            ("DURACIÓN",f"Inicia el {contract.inicio if contract else employee.fecha_ingreso}."+(f" Finaliza el {end}; causa temporal: {reason}. La persona trabajadora conoce desde la suscripción la fecha prevista, sin renuncia de derechos." if kind=="TEMPORAL" and end else " Su duración es indefinida salvo terminación conforme al marco aplicable.")),("JORNADA",contract.jornada if contract and contract.jornada else "La jornada será la registrada y comunicada por Gestión Humana."),("HORARIO","El horario y sus cambios legítimos serán comunicados y registrados."),("ASISTENCIA","La asistencia se acreditará mediante los medios autorizados por la empresa."),("PUNTUALIDAD","Se exige puntualidad y reporte oportuno de incidencias."),("SALARIO",f"La base salarial registrada es {_money(contract.salario if contract else employee.salario)} con frecuencia {employee.frecuencia_salario}."),("FORMA, FRECUENCIA Y LUGAR DE PAGO",f"Pago {employee.frecuencia_pago} mediante {employee.forma_pago}, conforme al registro vigente."),("SEGURIDAD SOCIAL","La empresa realizará afiliaciones y aportes conforme a parámetros legales vigentes."),("RETENCIONES FISCALES","Las retenciones se calcularán mediante el motor legal versionado aplicable."),("HORAS EXTRAORDINARIAS","Solo se reconocerán horas aprobadas y registradas por el flujo autorizado."),("DESCANSOS","Se respetarán descansos y pausas aplicables."),("VACACIONES","Las vacaciones se solicitarán, aprobarán y registrarán en Gestión Humana."),("SALARIO DE NAVIDAD","Se calculará conforme a la información salarial y normativa aplicable."),("LICENCIAS","Las licencias requerirán soporte y aprobación cuando corresponda."),("PERMISOS","Los permisos se gestionarán por el procedimiento interno."),("AUSENCIAS","Toda ausencia debe notificarse y justificarse oportunamente."),("TARDANZAS","Las tardanzas serán registradas y tratadas mediante el proceso correspondiente."),("DESCUENTOS PROCEDENTES","Solo se aplicarán descuentos autorizados o legalmente procedentes, con trazabilidad."),("PRÉSTAMOS Y ADELANTOS","Los préstamos y adelantos constarán por escrito y mostrarán cuota y saldo."),("OBLIGACIONES DEL TRABAJADOR","Ejecutar las funciones con diligencia, lealtad, cuidado y respeto."),("OBLIGACIONES DEL EMPLEADOR","Proveer condiciones, remuneración y registros conforme al marco aplicable."),("SEGURIDAD Y SALUD","Cumplir protocolos de prevención, reportar riesgos y utilizar protección requerida."),("HIGIENE","Mantener higiene personal, del puesto y de las herramientas asignadas."),("MANIPULACIÓN DE ALIMENTOS","Cuando aplique, cumplir inocuidad, trazabilidad y controles sanitarios."),("UNIFORMES","Usar y conservar uniformes y equipos conforme a las políticas entregadas."),("BIENES Y EQUIPOS","Custodiar activos, herramientas, credenciales y documentos de la empresa."),("CONFIDENCIALIDAD","Proteger información empresarial, de clientes y de personas durante y después de la relación."),("CONDUCTA","Mantener trato respetuoso y conducta compatible con el ambiente laboral."),("DISCIPLINA","Toda medida disciplinaria seguirá el procedimiento y quedará documentada."),("POLÍTICAS INTERNAS","Las políticas comunicadas y sus versiones forman parte del marco operativo."),("FORMACIÓN","Participar en capacitaciones necesarias para el cargo, seguridad y calidad."),("FUNCIONES Y PROCEDIMIENTOS","Los Anexos I y II identifican funciones y procedimientos por versión."),("MODIFICACIONES Y ADENDAS","Todo cambio posterior a la firma se documentará mediante adenda; el texto firmado permanece inmutable."),("TERMINACIÓN","La terminación se gestionará y documentará conforme a la causa y marco aplicable."),("PRESTACIONES Y DERECHOS","Los derechos adquiridos se calcularán con información verificable y revisión en casos sensibles."),("NO RENUNCIA","Ninguna estipulación implica renuncia anticipada a derechos irrenunciables."),("LEGISLACIÓN","La relación se interpreta conforme al ordenamiento laboral aplicable en República Dominicana."),("REGISTRO","La empresa conservará contrato, anexos, versiones, auditoría y documentos asociados."),("INTEGRIDAD","El contrato y sus anexos constituyen el acuerdo documentado entre las partes."),("ACEPTACIÓN",f"Versión {contract.version if contract else 1}; las partes manifiestan haber leído y comprendido su contenido."),("FIRMAS","Se emiten ejemplares de igual contenido para empleador y trabajador, con testigos cuando corresponda."),
        ]
        reference=(contract.numero if contract else "") or f"CTR-{employee.codigo}-01"
        story = [Paragraph(labels[kind],styles["Title"]),Paragraph(f"{reference} · Versión {contract.version if contract else 1}.0",styles["Normal"]),Spacer(1,8*mm),Paragraph(f"Trabajador: <b>{values['empleado']}</b><br/>Cargo: {employee.puesto.nombre}<br/>Lugar: {employee.centro.nombre}",styles["BodyText"]),PageBreak()] + [Paragraph(f"<b>{index}. {title}</b><br/>{text}", styles["BodyText"]) for index,(title,text) in enumerate(items,1)] + [PageBreak(),Paragraph("FIRMAS",styles["Heading2"]),Spacer(1,22*mm),_styled_table([["Por el empleador","La persona trabajadora","Testigo"],["____________________","____________________","____________________"]],[58*mm,58*mm,58*mm])]
    elif kind == "EXPEDIENTE":
        rows = [["Campo", "Información"],["Código",employee.codigo],["Nombre",values["empleado"]],["Identificación",employee.identificacion],["Puesto",employee.puesto.nombre],["Departamento",employee.departamento.nombre],["Lugar de trabajo",employee.centro.nombre],["Supervisor",str(employee.supervisor or "—")],["Ingreso",str(employee.fecha_ingreso)],["Estado",employee.estado],["Correo",employee.correo or "—"],["Teléfono",employee.telefono or "—"]]
        story = [_styled_table(rows,[48*mm,120*mm]),Spacer(1,5*mm),Paragraph("Este expediente resume la información vigente registrada. Los soportes documentales y el historial auditado permanecen en el repositorio de Gestión Humana.",styles["BodyText"])]
    if kind == "ANEXO":
        description = employee.puesto.descripciones_funciones.filter(empresa=employee.empresa, activa=True).order_by("-version").first()
        if description:
            story += [Spacer(1, 4*mm), Paragraph(f"<b>Objetivo</b><br/>{description.objetivo}", styles["BodyText"]), Paragraph(f"<b>Funciones</b><br/>{description.funciones}", styles["BodyText"]), Paragraph(f"<b>Responsabilidades</b><br/>{description.responsabilidades}", styles["BodyText"]), Paragraph(f"Versión {description.version} · Vigente desde {description.vigente_desde}", styles["Normal"])]
    story += [Spacer(1, 18*mm), Paragraph(f"{(template.firmante if template else '') or 'Responsable de Gestión Humana'}<br/>{(template.cargo_firmante if template else '') or 'Gestión Humana'}", styles["Normal"])]
    return _build_pdf(labels.get(kind, "Documento laboral"), employee.empresa, story)
