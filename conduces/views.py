import json
from io import BytesIO
from datetime import datetime, date, timedelta

from django.http import HttpResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncMonth
from django.contrib import messages
from django.utils import timezone

from openpyxl import Workbook, load_workbook
from openpyxl.utils.datetime import from_excel

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from .models import Empresa, CentroEducativo, MenuDiario, Conduce
from .utils import (
    generar_pdf_conduce,
    generar_pdf_conduces_masivo,
    generar_pdf_relacion_diaria,
)


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def convertir_fecha(fecha_str):
    if not fecha_str:
        return None

    try:
        return datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def convertir_fecha_excel(fecha):
    if isinstance(fecha, datetime):
        return fecha.date()

    if isinstance(fecha, date):
        return fecha

    if isinstance(fecha, (int, float)):
        return from_excel(fecha).date()

    if isinstance(fecha, str):
        fecha_limpia = fecha.strip()

        for formato in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
            try:
                return datetime.strptime(fecha_limpia, formato).date()
            except ValueError:
                pass

    return None


def obtener_empresa():
    return Empresa.objects.first()


def fecha_corta(fecha):
    return f"{fecha.day}/{fecha.month}/{fecha.year}"


def formatear_fecha_grafico(valor):
    if not valor:
        return ""

    if isinstance(valor, datetime):
        valor = valor.date()

    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")

    return str(valor)


def formatear_mes_grafico(valor):
    meses = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
    }

    if not valor:
        return ""

    if isinstance(valor, datetime):
        valor = valor.date()

    if isinstance(valor, date):
        return f"{meses.get(valor.month, '')} {valor.year}"

    return str(valor)


def nombre_mes(fecha_inicio, fecha_fin):
    meses = {
        1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
        5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
        9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
    }

    if fecha_inicio.month == fecha_fin.month and fecha_inicio.year == fecha_fin.year:
        return f"{meses[fecha_inicio.month]} {fecha_inicio.year}"

    return f"{fecha_inicio.strftime('%d/%m/%Y')} AL {fecha_fin.strftime('%d/%m/%Y')}"


def clasificar_producto(producto, cantidad):
    producto = (producto or "").upper().strip()

    pan = ""
    pan_vegetales = ""
    galleta = ""
    bizcocho = ""

    if "PAN DE ZANAHORIA" in producto:
        pan_vegetales = cantidad
    elif "MUFFIN" in producto or "MUFIN" in producto:
        bizcocho = cantidad
    elif "GALLETA" in producto or "GALLETAS" in producto:
        galleta = cantidad
    elif "BIZCOCHO" in producto or "BISCOCHO" in producto:
        bizcocho = cantidad
    elif "VEGETALES" in producto:
        pan_vegetales = cantidad
    else:
        pan = cantidad

    return pan, pan_vegetales, galleta, bizcocho


def normalizar_producto(nombre):
    if not nombre:
        return "Otros"

    nombre = nombre.lower()

    if "muffin" in nombre or "mufin" in nombre:
        return "Bizcocho"

    if "bizcocho" in nombre or "biscocho" in nombre:
        return "Bizcocho"

    if "pan de zanahoria" in nombre:
        return "Pan con vegetales"

    if "vegetales" in nombre:
        return "Pan con vegetales"

    if "galleta" in nombre:
        return "Galleta"

    if "pan" in nombre:
        return "Pan"

    return "Otros"


# =====================================================
# DASHBOARD / PANEL PRINCIPAL
# =====================================================

def inicio(request):
    hoy = timezone.localdate()
    manana = hoy + timedelta(days=1)
    inicio_mes = hoy.replace(day=1)

    conduces_mes = Conduce.objects.filter(
        fecha__gte=inicio_mes,
        fecha__lte=hoy
    )

    todos_conduces = Conduce.objects.all()

    total_raciones = conduces_mes.aggregate(total=Sum("cantidad"))["total"] or 0
    total_conduces = conduces_mes.count()
    total_centros = CentroEducativo.objects.count()

    menu_manana = MenuDiario.objects.filter(fecha=manana).first()
    producto_manana = menu_manana.producto if menu_manana else "No hay menú registrado"
    fecha_manana = manana.strftime("%d/%m/%Y")

    precio_racion_estimado = 10.18
    proyeccion_ventas = f"{(total_raciones * precio_racion_estimado):,.2f}"

    raciones_por_dia = (
        conduces_mes
        .values("fecha")
        .annotate(total=Sum("cantidad"))
        .order_by("fecha")
    )

    labels_dias = [
        formatear_fecha_grafico(item["fecha"])
        for item in raciones_por_dia
        if item["fecha"]
    ]

    data_dias = [
        item["total"] or 0
        for item in raciones_por_dia
        if item["fecha"]
    ]

    productos = {}

    for conduce in conduces_mes:
        producto = normalizar_producto(conduce.producto)
        productos[producto] = productos.get(producto, 0) + (conduce.cantidad or 0)

    labels_productos = list(productos.keys())
    data_productos = list(productos.values())

    resumen_meses = (
        todos_conduces
        .annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(
            total_raciones=Sum("cantidad"),
            total_conduces=Count("id")
        )
        .order_by("-mes")
    )

    return render(request, "inicio.html", {
        "total_raciones": total_raciones,
        "total_conduces": total_conduces,
        "total_centros": total_centros,
        "producto_manana": producto_manana,
        "fecha_manana": fecha_manana,
        "proyeccion_ventas": proyeccion_ventas,
        "labels_dias": labels_dias,
        "data_dias": data_dias,
        "labels_productos": labels_productos,
        "data_productos": data_productos,
        "resumen_meses": resumen_meses,
    })


# =====================================================
# PLANTILLAS EXCEL
# =====================================================

def descargar_plantilla_centros(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Centros"

    ws.append([
        "codigo",
        "nombre",
        "director",
        "telefono",
        "direccion",
        "provincia",
        "regional_distrito",
        "matricula",
        "latitud",
        "longitud",
    ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="plantilla_centros.xlsx"'
    wb.save(response)
    return response


def descargar_plantilla_menu(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Menu"
    ws.append(["fecha", "producto"])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="plantilla_menu.xlsx"'
    wb.save(response)
    return response


# =====================================================
# GESTIÓN DE CENTROS
# =====================================================

def pantalla_carga_centros(request):
    q = request.GET.get("q", "").strip()

    centros = CentroEducativo.objects.all().order_by("orden_carga", "id")

    if q:
        centros = centros.filter(
            Q(codigo__icontains=q) |
            Q(nombre__icontains=q) |
            Q(director__icontains=q) |
            Q(provincia__icontains=q) |
            Q(regional_distrito__icontains=q)
        )

    total_centros = centros.count()
    centros_con_ubicacion = centros.exclude(
        latitud__isnull=True
    ).exclude(
        longitud__isnull=True
    ).count()

    return render(request, "carga_centros.html", {
        "centros": centros,
        "q": q,
        "total_centros": total_centros,
        "centros_con_ubicacion": centros_con_ubicacion,
    })


def crear_centro(request):
    if request.method == "POST":
        codigo = request.POST.get("codigo", "").strip()
        nombre = request.POST.get("nombre", "").strip()

        if not codigo or not nombre:
            messages.error(request, "El código y el nombre del centro son obligatorios.")
            return redirect("carga_centros")

        CentroEducativo.objects.create(
            codigo=codigo,
            nombre=nombre,
            director=request.POST.get("director", "").strip(),
            telefono=request.POST.get("telefono", "").strip(),
            direccion=request.POST.get("direccion", "").strip(),
            provincia=request.POST.get("provincia", "").strip(),
            regional_distrito=request.POST.get("regional_distrito", "").strip(),
            matricula=int(request.POST.get("matricula") or 0),
            latitud=request.POST.get("latitud", "").strip().replace(",", ".") or None,
            longitud=request.POST.get("longitud", "").strip().replace(",", ".") or None,
            orden_carga=CentroEducativo.objects.count() + 1,
        )

        messages.success(request, "Centro creado correctamente.")

    return redirect("carga_centros")


def editar_centro(request, centro_id):
    centro = get_object_or_404(CentroEducativo, id=centro_id)

    if request.method == "POST":
        centro.codigo = request.POST.get("codigo", "").strip()
        centro.nombre = request.POST.get("nombre", "").strip()
        centro.director = request.POST.get("director", "").strip()
        centro.telefono = request.POST.get("telefono", "").strip()
        centro.direccion = request.POST.get("direccion", "").strip()
        centro.provincia = request.POST.get("provincia", "").strip()
        centro.regional_distrito = request.POST.get("regional_distrito", "").strip()
        centro.matricula = int(request.POST.get("matricula") or 0)
        centro.latitud = request.POST.get("latitud", "").strip().replace(",", ".") or None
        centro.longitud = request.POST.get("longitud", "").strip().replace(",", ".") or None
        centro.save()

        messages.success(request, "Centro actualizado correctamente.")
        return redirect("carga_centros")

    return render(request, "editar_centro.html", {
        "centro": centro
    })


def eliminar_centro(request, centro_id):
    centro = get_object_or_404(CentroEducativo, id=centro_id)

    if request.method == "POST":
        centro.delete()
        messages.success(request, "Centro eliminado correctamente.")

    return redirect("carga_centros")


def cargar_centros_excel(request):
    if request.method == "POST":
        archivo = request.FILES.get("archivo")

        if not archivo:
            messages.error(request, "Debe seleccionar un archivo.")
            return redirect("carga_centros")

        wb = load_workbook(archivo)
        ws = wb.active

        for indice, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=1):
            datos = list(row)

            while len(datos) < 10:
                datos.append(None)

            codigo, nombre, director, telefono, direccion, provincia, regional_distrito, matricula, latitud, longitud = datos[:10]

            if codigo and nombre:
                CentroEducativo.objects.update_or_create(
                    codigo=str(codigo).strip(),
                    defaults={
                        "nombre": str(nombre).strip(),
                        "director": str(director or ""),
                        "telefono": str(telefono or ""),
                        "direccion": str(direccion or ""),
                        "provincia": str(provincia or ""),
                        "regional_distrito": str(regional_distrito or ""),
                        "matricula": int(matricula or 0),
                        "latitud": str(latitud).replace(",", ".") if latitud else None,
                        "longitud": str(longitud).replace(",", ".") if longitud else None,
                        "orden_carga": indice,
                    },
                )

        messages.success(request, "Centros cargados correctamente.")
        return redirect("carga_centros")

    return redirect("carga_centros")


# =====================================================
# MAPA DE CENTROS
# =====================================================

def mapa_centros(request):
    codigo = request.GET.get("codigo", "").strip()

    centros_con_ubicacion = (
        CentroEducativo.objects
        .exclude(latitud__isnull=True)
        .exclude(longitud__isnull=True)
        .order_by("codigo")
    )

    centro_buscado = None

    if codigo:
        centro_buscado = CentroEducativo.objects.filter(codigo__iexact=codigo).first()

    centros_json = []

    for centro in centros_con_ubicacion:
        centros_json.append({
            "codigo": str(centro.codigo),
            "nombre": str(centro.nombre),
            "director": centro.director or "",
            "telefono": centro.telefono or "",
            "direccion": centro.direccion or "",
            "provincia": centro.provincia or "",
            "distrito": centro.regional_distrito or "",
            "matricula": centro.matricula or 0,
            "latitud": float(centro.latitud),
            "longitud": float(centro.longitud),
        })

    mensaje_ubicacion = None

    if centro_buscado:
        if centro_buscado.latitud and centro_buscado.longitud:
            mensaje_ubicacion = "Este centro ya tiene ubicación registrada y se muestra en el mapa."
        else:
            mensaje_ubicacion = "Este centro no tiene ubicación registrada. Puedes agregar latitud y longitud."

    return render(request, "mapa_centros.html", {
        "centros": centros_con_ubicacion,
        "centro_buscado": centro_buscado,
        "codigo": codigo,
        "centros_json": json.dumps(centros_json),
        "mensaje_ubicacion": mensaje_ubicacion,
    })


def actualizar_ubicacion_centro(request):
    if request.method == "POST":
        centro_id = request.POST.get("centro_id")
        latitud = request.POST.get("latitud", "").strip().replace(",", ".")
        longitud = request.POST.get("longitud", "").strip().replace(",", ".")

        centro = get_object_or_404(CentroEducativo, id=centro_id)

        if not latitud or not longitud:
            messages.error(request, "Debe completar latitud y longitud.")
            return redirect(f"/centros/mapa/?codigo={centro.codigo}")

        centro.latitud = latitud
        centro.longitud = longitud
        centro.save()

        messages.success(request, f"Ubicación agregada correctamente al centro {centro.codigo}.")
        return redirect(f"/centros/mapa/?codigo={centro.codigo}")

    return redirect("mapa_centros")


# =====================================================
# GESTIÓN DE MENÚ
# =====================================================

def pantalla_carga_menu(request):
    q = request.GET.get("q", "").strip()

    menus = MenuDiario.objects.all().order_by("-fecha")

    if q:
        menus = menus.filter(
            Q(producto__icontains=q) |
            Q(fecha__icontains=q)
        )

    return render(request, "carga_menu.html", {
        "menus": menus,
        "q": q,
    })


def crear_menu_diario(request):
    if request.method == "POST":
        fecha = request.POST.get("fecha")
        producto = request.POST.get("producto", "").strip()

        if fecha and producto:
            MenuDiario.objects.update_or_create(
                fecha=fecha,
                defaults={"producto": producto}
            )
            messages.success(request, "Menú creado correctamente.")
        else:
            messages.error(request, "Debe completar la fecha y el producto.")

    return redirect("carga_menu")


def editar_menu_diario(request, menu_id):
    menu = get_object_or_404(MenuDiario, id=menu_id)

    if request.method == "POST":
        fecha = request.POST.get("fecha")
        producto = request.POST.get("producto", "").strip()

        if fecha and producto:
            menu.fecha = fecha
            menu.producto = producto
            menu.save()
            messages.success(request, "Menú actualizado correctamente.")
            return redirect("carga_menu")

        messages.error(request, "Debe completar la fecha y el producto.")

    return render(request, "editar_menu.html", {
        "menu": menu
    })


def eliminar_menu_diario(request, menu_id):
    menu = get_object_or_404(MenuDiario, id=menu_id)

    if request.method == "POST":
        menu.delete()
        messages.success(request, "Menú eliminado correctamente.")

    return redirect("carga_menu")


def cargar_menu_excel(request):
    if request.method == "POST":
        archivo = request.FILES.get("archivo")

        if not archivo:
            messages.error(request, "Debe seleccionar un archivo.")
            return redirect("carga_menu")

        wb = load_workbook(archivo)
        ws = wb.active

        for row in ws.iter_rows(min_row=2, values_only=True):
            fecha, producto = row
            fecha = convertir_fecha_excel(fecha)

            if fecha and producto:
                MenuDiario.objects.update_or_create(
                    fecha=fecha,
                    defaults={"producto": str(producto).strip()},
                )

        messages.success(request, "Menú cargado correctamente.")
        return redirect("carga_menu")

    return redirect("carga_menu")


# =====================================================
# GENERACIÓN DE CONDUCES
# =====================================================

def generar_conduces_automaticos(request):
    empresas = Empresa.objects.all()

    if request.method == "POST":
        empresa_id = request.POST.get("empresa")
        numero_inicial = request.POST.get("numero_inicial", "").strip()
        fecha_desde = request.POST.get("fecha_desde")
        fecha_hasta = request.POST.get("fecha_hasta")

        if not empresa_id or not fecha_desde or not fecha_hasta:
            messages.error(request, "Debe completar empresa y fechas.")
            return redirect("generar_conduces")

        empresa = get_object_or_404(Empresa, id=empresa_id)

        fecha_desde = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
        fecha_hasta = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()

        if fecha_desde > fecha_hasta:
            messages.error(request, "La fecha desde no puede ser mayor que la fecha hasta.")
            return redirect("generar_conduces")

        centros = CentroEducativo.objects.all().order_by("orden_carga", "id")
        menus = MenuDiario.objects.filter(
            fecha__range=[fecha_desde, fecha_hasta]
        ).order_by("fecha")

        if not centros.exists():
            messages.error(request, "No hay centros cargados.")
            return redirect("generar_conduces")

        if not menus.exists():
            messages.error(request, "No hay menú cargado para ese rango de fechas.")
            return redirect("generar_conduces")

        def obtener_largo_formato(valor):
            return len(str(valor)) if str(valor).startswith("0") else None

        ultimo = Conduce.objects.filter(empresa=empresa).order_by("-id").first()

        if numero_inicial:
            numero = int(numero_inicial)
            largo = obtener_largo_formato(numero_inicial)
        elif ultimo:
            numero = int(ultimo.numero) + 1
            largo = obtener_largo_formato(ultimo.numero)
        else:
            numero = 1
            largo = None

        total_generados = 0

        for menu in menus:
            for centro in centros:
                existe = Conduce.objects.filter(
                    empresa=empresa,
                    fecha=menu.fecha,
                    centro=centro,
                ).exists()

                if not existe:
                    numero_final = str(numero).zfill(largo) if largo else str(numero)

                    Conduce.objects.create(
                        empresa=empresa,
                        numero=numero_final,
                        fecha=menu.fecha,
                        centro=centro,
                        producto=menu.producto,
                        cantidad=centro.matricula,
                        estado="borrador",
                    )

                    numero += 1
                    total_generados += 1

        messages.success(request, f"Se generaron {total_generados} conduces.")
        return redirect("generar_conduces")

    return render(request, "generar_conduces.html", {"empresas": empresas})


# =====================================================
# BÚSQUEDA / EDICIÓN / ELIMINACIÓN DE CONDUCES
# =====================================================

def buscar_conduces(request):
    conduces = (
        Conduce.objects
        .select_related("centro", "empresa")
        .all()
        .order_by("-fecha", "-id")
    )

    q = request.GET.get("q", "").strip()
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()
    estado = request.GET.get("estado", "").strip()

    if q:
        conduces = conduces.filter(
            Q(numero__icontains=q) |
            Q(producto__icontains=q) |
            Q(centro__nombre__icontains=q) |
            Q(centro__codigo__icontains=q)
        )

    if fecha_desde:
        conduces = conduces.filter(fecha__gte=fecha_desde)

    if fecha_hasta:
        conduces = conduces.filter(fecha__lte=fecha_hasta)

    if estado:
        conduces = conduces.filter(estado=estado)

    return render(request, "buscar_conduces.html", {
        "conduces": conduces,
        "q": q,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "estado": estado,
    })


def editar_conduce(request, conduce_id):
    conduce = get_object_or_404(Conduce, id=conduce_id)

    if request.method == "POST":
        conduce.numero = request.POST.get("numero")
        conduce.fecha = request.POST.get("fecha")
        conduce.producto = request.POST.get("producto")
        conduce.cantidad = request.POST.get("cantidad")
        conduce.estado = request.POST.get("estado")
        conduce.observaciones = request.POST.get("observaciones")
        conduce.save()

        messages.success(request, "Conduce actualizado correctamente.")
        return redirect("buscar_conduces")

    return render(request, "editar_conduce.html", {
        "conduce": conduce
    })


def eliminar_conduce(request, conduce_id):
    conduce = get_object_or_404(Conduce, id=conduce_id)

    if request.method == "POST":
        conduce.delete()
        messages.success(request, "Conduce eliminado correctamente.")

    return redirect("buscar_conduces")


def anular_conduce(request, conduce_id):
    conduce = get_object_or_404(Conduce, id=conduce_id)
    conduce.estado = "anulado"
    conduce.save()

    messages.success(request, "Conduce anulado correctamente.")
    return redirect("buscar_conduces")


def vista_conduce(request, conduce_id):
    conduce = get_object_or_404(Conduce, id=conduce_id)
    return render(request, "vista_conduce.html", {"conduce": conduce})


# =====================================================
# ACCIONES MASIVAS
# =====================================================

def acciones_conduces(request):
    if request.method == "POST":
        ids = request.POST.getlist("conduces")
        accion = request.POST.get("accion")

        if not ids:
            messages.error(request, "Debe seleccionar al menos un conduce.")
            return redirect("buscar_conduces")

        conduces = list(
            Conduce.objects
            .filter(id__in=ids)
            .select_related("centro", "empresa")
        )

        conduces.sort(
            key=lambda c: (
                c.fecha,
                int(c.numero) if str(c.numero).isdigit() else 0,
                c.centro.orden_carga,
                c.centro.nombre,
            )
        )

        if accion == "anular":
            Conduce.objects.filter(id__in=ids).update(estado="anulado")
            messages.success(request, "Conduces anulados correctamente.")
            return redirect("buscar_conduces")

        if accion == "entregado":
            Conduce.objects.filter(id__in=ids).update(estado="entregado")
            messages.success(request, "Conduces marcados como entregados.")
            return redirect("buscar_conduces")

        if accion == "pdf_ver":
            pdf = generar_pdf_conduces_masivo(conduces)
            return FileResponse(pdf, content_type="application/pdf")

        if accion == "pdf_descargar":
            pdf = generar_pdf_conduces_masivo(conduces)
            response = FileResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="conduces_seleccionados.pdf"'
            return response

        if accion == "relacion_diaria_pdf":
            conduces_validos = [
                conduce for conduce in conduces if conduce.estado != "anulado"
            ]
            pdf = generar_pdf_relacion_diaria(conduces_validos)
            return FileResponse(pdf, content_type="application/pdf")

    return redirect("buscar_conduces")


# =====================================================
# PDF CONDUCE INDIVIDUAL
# =====================================================

def visualizar_pdf_conduce(request, conduce_id):
    conduce = get_object_or_404(Conduce, id=conduce_id)
    archivo_pdf = generar_pdf_conduce(conduce)

    return FileResponse(
        open(archivo_pdf, "rb"),
        content_type="application/pdf"
    )


# =====================================================
# RELACIÓN DIARIA
# =====================================================

def generar_relacion_diaria_pdf(request):
    fecha = request.GET.get("fecha")

    if not fecha:
        return HttpResponse(
            "Debe enviar una fecha. Ejemplo: /relacion-diaria/pdf/?fecha=2026-03-02",
            status=400
        )

    fecha = convertir_fecha(fecha)

    if not fecha:
        return HttpResponse(
            "Formato de fecha inválido. Use el formato YYYY-MM-DD.",
            status=400
        )

    conduces = (
        Conduce.objects
        .filter(fecha=fecha)
        .exclude(estado="anulado")
        .select_related("empresa", "centro")
        .order_by("numero")
    )

    if not conduces.exists():
        return HttpResponse("No hay conduces válidos para esa fecha.", status=404)

    pdf = generar_pdf_relacion_diaria(conduces)

    return FileResponse(
        pdf,
        content_type="application/pdf",
        filename="relacion_diaria.pdf"
    )


# =====================================================
# RELACIÓN GENERAL
# =====================================================

def generar_relacion_general_pdf(request):
    empresa = obtener_empresa()

    if not empresa:
        return HttpResponse(
            "Debe registrar una empresa antes de generar la relación general.",
            status=400
        )

    fecha_inicio = convertir_fecha(request.GET.get("fecha_inicio"))
    fecha_fin = convertir_fecha(request.GET.get("fecha_fin"))

    if not fecha_inicio or not fecha_fin:
        return HttpResponse(
            "Debe seleccionar fecha inicio y fecha final.",
            status=400
        )

    if fecha_inicio > fecha_fin:
        return HttpResponse(
            "La fecha de inicio no puede ser mayor que la fecha final.",
            status=400
        )

    conduces = (
        Conduce.objects
        .filter(fecha__range=[fecha_inicio, fecha_fin])
        .exclude(estado="anulado")
        .select_related("centro", "empresa")
        .order_by("fecha", "numero")
    )

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    page_width, page_height = letter

    table_width = 540
    x_tabla = (page_width - table_width) / 2
    tabla_top_y = 600

    col_widths = [43, 50, 58, 210, 45, 55, 40, 39]
    filas_por_pagina = 38
    row_height = 13
    header_height = 30

    meses_texto = nombre_mes(fecha_inicio, fecha_fin)

    estilo_nombre = ParagraphStyle(
        name="NombreCentro",
        fontName="Helvetica",
        fontSize=5.4,
        leading=6,
        alignment=TA_LEFT,
    )

    estilo_header = ParagraphStyle(
        name="Header",
        fontName="Helvetica-Bold",
        fontSize=5.2,
        leading=5.8,
        alignment=TA_CENTER,
    )

    encabezados = [
        Paragraph("FECHA", estilo_header),
        Paragraph("NO. DE<br/>CONDUCE", estilo_header),
        Paragraph("CODIGO DEL<br/>CENTRO<br/>EDUCATIVO", estilo_header),
        Paragraph("NOMBRE DEL CENTRO EDUCATIVO", estilo_header),
        Paragraph("PAN", estilo_header),
        Paragraph("PAN CON<br/>VEGETALE", estilo_header),
        Paragraph("GALLETA", estilo_header),
        Paragraph("BIZCOCHO", estilo_header),
    ]

    filas = []
    total_pan = 0
    total_pan_vegetales = 0
    total_galleta = 0
    total_bizcocho = 0

    for conduce in conduces:
        cantidad = conduce.cantidad or 0

        pan, pan_vegetales, galleta, bizcocho = clasificar_producto(
            conduce.producto,
            cantidad
        )

        total_pan += pan if pan != "" else 0
        total_pan_vegetales += pan_vegetales if pan_vegetales != "" else 0
        total_galleta += galleta if galleta != "" else 0
        total_bizcocho += bizcocho if bizcocho != "" else 0

        filas.append([
            fecha_corta(conduce.fecha),
            str(conduce.numero),
            conduce.centro.codigo,
            Paragraph((conduce.centro.nombre or "").upper(), estilo_nombre),
            f"{pan:,}" if pan != "" else "",
            f"{pan_vegetales:,}" if pan_vegetales != "" else "",
            f"{galleta:,}" if galleta != "" else "",
            f"{bizcocho:,}" if bizcocho != "" else "",
        ])

    paginas_tabla = max(1, (len(filas) + filas_por_pagina - 1) // filas_por_pagina)
    total_paginas = paginas_tabla

    def dibujar_encabezado(pagina_actual):
        pdf.setFont("Helvetica-Bold", 8.8)
        pdf.drawCentredString(page_width / 2, 742, (empresa.nombre or "").upper())

        pdf.setFont("Helvetica", 7.2)
        pdf.drawCentredString(page_width / 2, 729, empresa.direccion or "")
        pdf.drawCentredString(page_width / 2, 718, f"Ciudad {empresa.ciudad or ''}")

        if empresa.correo:
            pdf.drawCentredString(page_width / 2, 707, f"Correo.: {empresa.correo}")
            pdf.drawCentredString(page_width / 2, 696, f"Telefono.: {empresa.telefono or ''}")
            pdf.drawCentredString(page_width / 2, 685, f"RNC.:{empresa.rnc or ''}")
            titulo_y = 660
            mes_y = 640
        else:
            pdf.drawCentredString(page_width / 2, 707, f"Telefono.: {empresa.telefono or ''}")
            pdf.drawCentredString(page_width / 2, 696, f"RNC.:{empresa.rnc or ''}")
            titulo_y = 665
            mes_y = 645

        pdf.setFont("Helvetica-Bold", 10.5)
        pdf.drawCentredString(page_width / 2, titulo_y, "RELACION DE CONDUCE")

        texto_mes = f"MES  {meses_texto}"
        pdf.setFont("Helvetica-Bold", 7.4)
        pdf.drawCentredString(page_width / 2, mes_y, texto_mes)

        ancho_mes = pdf.stringWidth(texto_mes, "Helvetica-Bold", 7.4)
        pdf.setLineWidth(0.5)
        pdf.line(
            (page_width / 2) - (ancho_mes / 2),
            mes_y - 3,
            (page_width / 2) + (ancho_mes / 2),
            mes_y - 3
        )

        pdf.setFont("Helvetica", 7)
        pdf.drawCentredString(page_width / 2, 55, f"{pagina_actual} DE {total_paginas}")

    pagina = 1
    indice = 0
    ultima_y_tabla = tabla_top_y

    while indice < len(filas):
        dibujar_encabezado(pagina)

        bloque = filas[indice:indice + filas_por_pagina]
        data = [encabezados] + bloque
        row_heights = [header_height] + [row_height] * len(bloque)

        tabla = Table(
            data,
            colWidths=col_widths,
            rowHeights=row_heights,
            repeatRows=1
        )

        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 5.2),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 5.4),
            ("ALIGN", (0, 1), (2, -1), "CENTER"),
            ("ALIGN", (4, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            ("LEADING", (0, 1), (-1, -1), 13),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))

        ancho_tabla, alto_tabla = tabla.wrap(0, 0)
        y_tabla = tabla_top_y - alto_tabla

        tabla.drawOn(pdf, x_tabla, y_tabla)
        ultima_y_tabla = y_tabla

        indice += filas_por_pagina

        if indice < len(filas):
            pdf.showPage()
            pagina += 1

    if not filas:
        dibujar_encabezado(pagina)

    y_total = ultima_y_tabla - 14

    if y_total < 90:
        y_total = 90

    total_data = [[
        "",
        "",
        "",
        "TOTAL",
        "-" if int(total_pan or 0) == 0 else f"{total_pan:,}",
        "-" if int(total_pan_vegetales or 0) == 0 else f"{total_pan_vegetales:,}",
        "-" if int(total_galleta or 0) == 0 else f"{total_galleta:,}",
        "-" if int(total_bizcocho or 0) == 0 else f"{total_bizcocho:,}",
    ]]

    tabla_total = Table(total_data, colWidths=col_widths, rowHeights=[14])

    tabla_total.setStyle(TableStyle([
        ("SPAN", (0, 0), (3, 0)),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
        ("LINEABOVE", (0, 0), (-1, 0), 1.4, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 6.5),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    tabla_total.wrap(0, 0)
    tabla_total.drawOn(pdf, x_tabla, y_total)

    y_firma = y_total - 38

    if y_firma < 70:
        y_firma = 70

    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.line(x_tabla + 20, y_firma, x_tabla + 195, y_firma)
    pdf.drawString(x_tabla + 30, y_firma - 12, "FIRMA Y SELLO DEL SUPLIDOR")

    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="relacion_general_conduces.pdf"'
    return response