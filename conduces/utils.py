from io import BytesIO
from collections import defaultdict, OrderedDict

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# ======================================================
# TEXTO AJUSTADO A UNA CELDA
# ======================================================
def draw_text_fit(c, text, x, y, max_width, font_name="Helvetica-Bold", max_size=5.6, min_size=3.8):
    text = str(text or "")

    font_size = max_size
    while font_size >= min_size:
        if c.stringWidth(text, font_name, font_size) <= max_width:
            c.setFont(font_name, font_size)
            c.drawString(x, y, text)
            return
        font_size -= 0.2

    while c.stringWidth(text + "...", font_name, min_size) > max_width and len(text) > 0:
        text = text[:-1]

    c.setFont(font_name, min_size)
    c.drawString(x, y, text + "...")


# ======================================================
# DIBUJAR CONDUCE INDIVIDUAL
# ======================================================
def dibujar_conduce(c, conduce):
    empresa = conduce.empresa
    centro = conduce.centro

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(306, 748, empresa.nombre)

    c.setFont("Helvetica", 8)
    c.drawCentredString(306, 735, empresa.direccion or "")
    c.drawCentredString(306, 723, empresa.ciudad or "")

    if empresa.correo:
        c.drawCentredString(306, 711, f"Correo.: {empresa.correo}")
        c.drawCentredString(306, 699, f"Teléfono.: {empresa.telefono}")
        c.drawCentredString(306, 687, f"RNC.: {empresa.rnc}")
        top_y = 662
    else:
        c.drawCentredString(306, 711, f"Teléfono.: {empresa.telefono}")
        c.drawCentredString(306, 699, f"RNC.: {empresa.rnc}")
        top_y = 672

    c.setFont("Helvetica-Bold", 8)
    c.drawString(390, top_y, "CONDUCE No.:")
    c.drawString(390, top_y - 18, "FECHA.:")

    c.setFont("Helvetica", 8)
    c.drawString(520, top_y, str(conduce.numero))
    c.drawString(520, top_y - 18, conduce.fecha.strftime("%d/%m/%Y"))

    c.line(520, top_y - 3, 575, top_y - 3)
    c.line(520, top_y - 21, 575, top_y - 21)

    y = top_y - 70

    c.setFont("Helvetica-Bold", 8)
    c.drawString(35, y, "CENTRO EDUCATIVO.:")
    c.drawString(35, y - 20, "DIRECTOR DEL CENTRO.:")
    c.drawString(35, y - 40, "DIRECCION.:")
    c.drawString(35, y - 60, "PROVINCIA:")
    c.drawString(390, y, "CODIGO DE CENTRO:")
    c.drawString(390, y - 20, "TELEFONO:")
    c.drawString(390, y - 60, "REGIONAL/DIST.:")

    c.setFont("Helvetica", 8)
    c.drawString(170, y, (centro.nombre or "")[:42])
    c.drawString(170, y - 20, (centro.director or "")[:42])
    c.drawString(170, y - 40, (centro.direccion or "")[:42])
    c.drawString(170, y - 60, (centro.provincia or "")[:42])

    c.drawString(520, y, centro.codigo or "")
    c.drawString(520, y - 20, centro.telefono or "")
    c.drawString(520, y - 60, centro.regional_distrito or "")

    c.line(170, y - 3, 380, y - 3)
    c.line(170, y - 23, 380, y - 23)
    c.line(170, y - 43, 380, y - 43)
    c.line(170, y - 63, 380, y - 63)

    c.line(520, y - 3, 575, y - 3)
    c.line(520, y - 23, 575, y - 23)
    c.line(520, y - 63, 575, y - 63)

    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(306, y - 105, "DETALLE DE LAS RACIONES ENTREGADAS Y RECIBIDAS")

    tabla_y = y - 145

    c.rect(35, tabla_y, 540, 25)
    c.line(455, tabla_y, 455, tabla_y + 25)

    c.drawCentredString(245, tabla_y + 9, "DESCRIPCION DEL PRODUCTO")
    c.drawCentredString(515, tabla_y + 9, "CANTIDAD")

    c.rect(35, tabla_y - 60, 540, 60)
    c.line(455, tabla_y - 60, 455, tabla_y)

    c.setFont("Helvetica", 10)
    c.drawCentredString(245, tabla_y - 35, conduce.producto)
    c.drawCentredString(515, tabla_y - 35, str(conduce.cantidad))

    obs_y = tabla_y - 95

    c.setFont("Helvetica-Bold", 8)
    c.drawString(35, obs_y, "OBSERVACIONES:")

    c.line(140, obs_y - 3, 575, obs_y - 3)
    c.line(35, obs_y - 25, 575, obs_y - 25)

    if conduce.observaciones:
        c.setFont("Helvetica", 8)
        c.drawString(145, obs_y - 15, conduce.observaciones[:90])

    recibido_y = obs_y - 70

    c.setFont("Helvetica-Bold", 8)
    c.drawString(300, recibido_y, "RECIBIDO POR:")
    c.drawString(300, recibido_y - 20, "NOMBRE:")
    c.drawString(300, recibido_y - 40, "FIRMA:")
    c.drawString(300, recibido_y - 60, "FECHA RECEPCION:")
    c.drawString(300, recibido_y - 80, "HORA DE RECEPCION:")

    c.line(410, recibido_y - 23, 575, recibido_y - 23)
    c.line(410, recibido_y - 43, 575, recibido_y - 43)
    c.line(410, recibido_y - 63, 575, recibido_y - 63)
    c.line(410, recibido_y - 83, 575, recibido_y - 83)

    firma_y = recibido_y - 120

    c.line(35, firma_y, 250, firma_y)
    c.drawString(60, firma_y - 15, "FIRMA Y SELLO DEL SUPLIDOR")
    c.drawString(300, firma_y - 15, "SELLO DEL CENTRO")


# ======================================================
# PDF INDIVIDUAL
# ======================================================
def generar_pdf_conduce(conduce):
    file_name = f"conduce_{conduce.numero}.pdf"
    c = canvas.Canvas(file_name, pagesize=letter)
    dibujar_conduce(c, conduce)
    c.save()
    return file_name


# ======================================================
# PDF MASIVO DE CONDUCES
# ======================================================
def generar_pdf_conduces_masivo(conduces):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    for conduce in conduces:
        dibujar_conduce(c, conduce)
        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


# ======================================================
# RELACIÓN DIARIA PDF
# ======================================================
def generar_pdf_relacion_diaria(conduces):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    conduces = list(conduces)

    if not conduces:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 750, "No hay conduces válidos para generar la relación diaria.")
        c.save()
        buffer.seek(0)
        return buffer

    conduces.sort(
        key=lambda conduce: (
            conduce.fecha,
            int(conduce.numero) if str(conduce.numero).isdigit() else 0,
            conduce.centro.orden_carga,
            conduce.centro.nombre,
        )
    )

    conduces_por_fecha = OrderedDict()
    for conduce in conduces:
        conduces_por_fecha.setdefault(conduce.fecha, []).append(conduce)

    meses = {
        1: "ENERO",
        2: "FEBRERO",
        3: "MARZO",
        4: "ABRIL",
        5: "MAYO",
        6: "JUNIO",
        7: "JULIO",
        8: "AGOSTO",
        9: "SEPTIEMBRE",
        10: "OCTUBRE",
        11: "NOVIEMBRE",
        12: "DICIEMBRE",
    }

    # Tabla centrada en la hoja carta
    page_width, page_height = letter
    table_width = 540
    x_inicio = (page_width - table_width) / 2
    x_fin = x_inicio + table_width

    x_fecha = x_inicio
    x_conduce = x_inicio + 45
    x_codigo = x_inicio + 95
    x_nombre = x_inicio + 155
    x_pan = x_inicio + 365
    x_pan_veg = x_inicio + 410
    x_galleta = x_inicio + 460
    x_bizcocho = x_inicio + 500
    x_fin = x_inicio + 540

    alto_header = 34
    alto_fila = 16

    columnas = [
        x_fecha,
        x_conduce,
        x_codigo,
        x_nombre,
        x_pan,
        x_pan_veg,
        x_galleta,
        x_bizcocho,
        x_fin,
    ]

    def dibujar_encabezado_pagina(empresa, fecha):
        mes_texto = f"{meses.get(fecha.month, '')} {fecha.year}"

        # Datos empresa un poco más grandes, centrados y con margen superior
        c.setFont("Helvetica-Bold", 8.8)
        c.drawCentredString(page_width / 2, 742, empresa.nombre or "")

        c.setFont("Helvetica", 7.2)
        c.drawCentredString(page_width / 2, 729, empresa.direccion or "")
        c.drawCentredString(page_width / 2, 718, empresa.ciudad or "")

        if empresa.correo:
            c.drawCentredString(page_width / 2, 707, f"Correo.: {empresa.correo}")
            c.drawCentredString(page_width / 2, 696, f"Telefono.: {empresa.telefono or ''}")
            c.drawCentredString(page_width / 2, 685, f"RNC.:{empresa.rnc or ''}")
            titulo_y = 660
            mes_y = 640
            tabla_y_actual = 585
        else:
            c.drawCentredString(page_width / 2, 707, f"Telefono.: {empresa.telefono or ''}")
            c.drawCentredString(page_width / 2, 696, f"RNC.:{empresa.rnc or ''}")
            titulo_y = 665
            mes_y = 645
            tabla_y_actual = 590

        c.setFont("Helvetica-Bold", 10.5)
        c.drawCentredString(page_width / 2, titulo_y, "RELACION DE CONDUCE")

        c.setFont("Helvetica-Bold", 7.4)
        texto_mes = f"MES {mes_texto}"
        c.drawCentredString(page_width / 2, mes_y, texto_mes)

        ancho_mes = c.stringWidth(texto_mes, "Helvetica-Bold", 7.4)
        c.setLineWidth(0.5)
        c.line(page_width / 2 - ancho_mes / 2, mes_y - 2, page_width / 2 + ancho_mes / 2, mes_y - 2)

        # Encabezado tabla
        c.setLineWidth(0.5)
        c.setFillGray(0.85)
        c.rect(x_inicio, tabla_y_actual, table_width, alto_header, fill=1, stroke=1)
        c.setFillGray(0)

        for x in columnas[1:-1]:
            c.line(x, tabla_y_actual, x, tabla_y_actual + alto_header)

        c.setFont("Helvetica-Bold", 5.1)

        c.drawCentredString((x_fecha + x_conduce) / 2, tabla_y_actual + 13, "FECHA")

        c.drawCentredString((x_conduce + x_codigo) / 2, tabla_y_actual + 19, "NO. DE")
        c.drawCentredString((x_conduce + x_codigo) / 2, tabla_y_actual + 9, "CONDUCE")

        c.drawCentredString((x_codigo + x_nombre) / 2, tabla_y_actual + 22, "CODIGO DEL")
        c.drawCentredString((x_codigo + x_nombre) / 2, tabla_y_actual + 13, "CENTRO")
        c.drawCentredString((x_codigo + x_nombre) / 2, tabla_y_actual + 4, "EDUCATIVO")

        c.drawCentredString((x_nombre + x_pan) / 2, tabla_y_actual + 13, "NOMBRE DEL CENTRO EDUCATIVO")

        c.drawCentredString((x_pan + x_pan_veg) / 2, tabla_y_actual + 13, "PAN")

        c.drawCentredString((x_pan_veg + x_galleta) / 2, tabla_y_actual + 19, "PAN CON")
        c.drawCentredString((x_pan_veg + x_galleta) / 2, tabla_y_actual + 9, "VEGETALE")

        c.drawCentredString((x_galleta + x_bizcocho) / 2, tabla_y_actual + 13, "GALLETA")
        c.drawCentredString((x_bizcocho + x_fin) / 2, tabla_y_actual + 13, "BIZCOCHO")

        return tabla_y_actual - alto_fila

    primera_pagina = True

    for fecha, lista_conduces in conduces_por_fecha.items():
        if not primera_pagina:
            c.showPage()

        primera_pagina = False
        empresa = lista_conduces[0].empresa
        y = dibujar_encabezado_pagina(empresa, fecha)

        total_por_producto = defaultdict(int)

        for conduce in lista_conduces:
            if y < 95:
                c.showPage()
                y = dibujar_encabezado_pagina(empresa, fecha)

            producto = (conduce.producto or "").upper().strip()
            cantidad = conduce.cantidad or 0
            fecha_texto = f"{conduce.fecha.day}/{conduce.fecha.month}/{conduce.fecha.year}"

            c.setLineWidth(0.5)
            c.rect(x_inicio, y, table_width, alto_fila, fill=0, stroke=1)

            for x in columnas[1:-1]:
                c.line(x, y, x, y + alto_fila)

            c.setFont("Helvetica-Bold", 5.6)

            c.drawCentredString((x_fecha + x_conduce) / 2, y + 5, fecha_texto)
            c.drawCentredString((x_conduce + x_codigo) / 2, y + 5, str(conduce.numero))
            c.drawCentredString((x_codigo + x_nombre) / 2, y + 5, str(conduce.centro.codigo))

            max_nombre_width = (x_pan - x_nombre) - 6
            draw_text_fit(
                c,
                conduce.centro.nombre,
                x_nombre + 3,
                y + 5,
                max_nombre_width,
                font_name="Helvetica-Bold",
                max_size=5.5,
                min_size=3.7,
            )

            c.setFont("Helvetica-Bold", 5.6)

            if "PAN DE ZANAHORIA" in producto:
               c.drawCentredString((x_pan_veg + x_galleta) / 2, y + 5, str(cantidad))
               total_por_producto["PAN CON VEGETALES"] += cantidad

            elif "MUFFIN" in producto or "MUFIN" in producto:
                 c.drawCentredString((x_bizcocho + x_fin) / 2, y + 5, str(cantidad))
                 total_por_producto["BIZCOCHO"] += cantidad

            elif "GALLETA" in producto or "GALLETAS" in producto:
                 c.drawCentredString((x_galleta + x_bizcocho) / 2, y + 5, str(cantidad))
                 total_por_producto["GALLETA"] += cantidad

            elif "BIZCOCHO" in producto or "BISCOCHO" in producto:
                 c.drawCentredString((x_bizcocho + x_fin) / 2, y + 5, str(cantidad))
                 total_por_producto["BIZCOCHO"] += cantidad

            else:
                c.drawCentredString((x_pan + x_pan_veg) / 2, y + 5, str(cantidad))
                total_por_producto["PAN"] += cantidad

            y -= alto_fila

        if y < 80:
            c.showPage()
            y = dibujar_encabezado_pagina(empresa, fecha)

        # TOTAL con celdas combinadas
        c.setFont("Helvetica-Bold", 6)
        c.setLineWidth(0.5)

        c.rect(x_inicio, y, table_width, alto_fila, fill=0, stroke=1)

        for x in [x_pan, x_pan_veg, x_galleta, x_bizcocho]:
            c.line(x, y, x, y + alto_fila)

        c.drawCentredString((x_inicio + x_pan) / 2, y + 5, "TOTAL")

        c.drawCentredString((x_pan + x_pan_veg) / 2, y + 5, f"{total_por_producto['PAN']:,}")

        c.drawCentredString(
            (x_pan_veg + x_galleta) / 2,
            y + 5,
            f"{total_por_producto['PAN CON VEGETALES']:,}"
            if total_por_producto["PAN CON VEGETALES"]
            else "-"
        )

        c.drawCentredString(
            (x_galleta + x_bizcocho) / 2,
            y + 5,
            f"{total_por_producto['GALLETA']:,}"
            if total_por_producto["GALLETA"]
            else "-"
        )

        c.drawCentredString(
            (x_bizcocho + x_fin) / 2,
            y + 5,
            f"{total_por_producto['BIZCOCHO']:,}"
            if total_por_producto["BIZCOCHO"]
            else "-"
        )

        c.setLineWidth(1.4)
        c.line(x_inicio, y, x_fin, y)
        c.setLineWidth(0.5)

        y -= 25

        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(x_inicio + 35, y, "FIRMA Y SELLO DEL SUPLIDOR")

    c.save()
    buffer.seek(0)
    return buffer