import json
from io import BytesIO
from datetime import datetime, date, timedelta
from decimal import Decimal
from urllib.parse import urlencode

from .utils import suscripcion_requerida 
from django.http import HttpResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction
from django.db.models import Q, Sum, Count, F
from django.db.models.functions import TruncMonth
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .decorators import (
    modulo_requerido,
    permiso_eliminar_conduce_requerido,
    puede_eliminar_conduce,
)

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from openpyxl import Workbook, load_workbook
from openpyxl.utils.datetime import from_excel
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.utils import ImageReader

from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout

import os
import json
import logging
import secrets
import urllib.request
import urllib.error

from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from auditoria.services import registrar_evento
from core.transactional_email import (
    safe_delivery_error,
    send_transactional_email,
)

try:
    import qrcode
except ImportError:
    qrcode = None

from .models import (
    Empresa,
    CentroEducativo,
    MenuDiario,
    Conduce,
    ProductoFacturacion,
    ComprobanteFiscal,
    RangoComprobanteGubernamental,
    Factura,
    DetalleFactura,
    Plan,
    EmpresaSaaS,
    Suscripcion,
    PerfilUsuario,
    CodigoValidacion,
    DiaNoDocencia,
    CalendarioEscolar,
    DiaCalendarioEscolar,
    FechaOficialCalendario,
    ProgramaMenu,
    VersionProgramaMenu,
    ItemCicloMenu,
    AsignacionProgramaCentro,
    ProgramacionMenuEscolar,
    AnalisisDocumentoCalendario,
    TotalMensualCalendario,
)
from .calendar_document_service import analizar_documento_calendario
from .menu_planning import (
    activar_calendario,
    contar_docencia_regular,
    materializar_programacion,
    puede_gestionar_planificacion,
    previsualizar_asignacion,
)

from .utils import (
    generar_pdf_conduce,
    generar_pdf_conduces_masivo,
    generar_pdf_relacion_diaria,
    suscripcion_requerida,
)


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

logger_verificacion_email = logging.getLogger("conduces.verificacion_email")
logger_menu_documento = logging.getLogger("conduces.menu_documento")

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



def obtener_empresa(request):
    """
    Resuelve la empresa operativa de la petición usando
    la fuente central de contexto multiempresa de SASTRE.

    El modo soporte continúa deshabilitado en esta fase.
    """
    from .tenant_context import obtener_empresa_request

    return obtener_empresa_request(
        request,
        permitir_soporte=True,
    )



def fecha_corta(fecha):
    return f"{fecha.day}/{fecha.month}/{fecha.year}"


def fecha_larga_es(fecha):
    meses = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }

    return f"{fecha.day:02d} de {meses[fecha.month]} de {fecha.year}"


def formato_monto(valor):
    if valor is None:
        valor = Decimal("0.00")

    return f"{Decimal(valor):,.2f}"


def formato_cantidad(valor):
    if valor is None:
        return "0"

    return str(int(valor))


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
        1: "Ene",
        2: "Feb",
        3: "Mar",
        4: "Abr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Ago",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dic",
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

    if fecha_inicio.month == fecha_fin.month and fecha_inicio.year == fecha_fin.year:
        return f"{meses[fecha_inicio.month]} {fecha_inicio.year}"

    return f"{fecha_inicio.strftime('%d/%m/%Y')} AL {fecha_fin.strftime('%d/%m/%Y')}"


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


def clasificar_categoria_factura(producto):
    producto = (producto or "").upper().strip()

    if "PAN DE ZANAHORIA" in producto:
        return "PAN_CON_VEGETALES"

    if "MUFFIN" in producto or "MUFIN" in producto:
        return "BIZCOCHO"

    if "BIZCOCHO" in producto or "BISCOCHO" in producto:
        return "BIZCOCHO"

    if "GALLETA" in producto or "GALLETAS" in producto:
        return "GALLETA"

    if "VEGETALES" in producto:
        return "PAN_CON_VEGETALES"

    return "PAN"


# =====================================================
# DASHBOARD / PANEL PRINCIPAL
# =====================================================

@login_required(login_url="login_usuario")
@suscripcion_requerida
def inicio(request):
    empresa = obtener_empresa(request)
    if not empresa:
        messages.error(request, "Debe configurar su empresa antes de continuar.")
        return redirect("login_usuario")

    from comercial.models_o2c4 import CuentaPorCobrar, FacturaVenta
    from compras.p2p_models import OrdenCompraEnterprise, RecepcionCompra
    from contabilidad.models import CuentaPorPagarEnterprise
    from core.models import NavegacionReciente
    from inventario.models import ProductoInventario
    from rrhh.models import Empleado

    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    fin_eventos = hoy + timedelta(days=7)
    manana = hoy + timedelta(days=1)

    conduces_diarios = list(
        Conduce.objects.filter(empresa=empresa, fecha__range=(inicio_mes, hoy))
        .values("fecha").annotate(total=Sum("cantidad"), documentos=Count("id"))
        .order_by("fecha")
    )
    total_raciones = sum((item["total"] or 0) for item in conduces_diarios)
    total_conduces = sum(item["documentos"] for item in conduces_diarios)
    total_centros = CentroEducativo.objects.filter(empresa=empresa).count()
    menu_manana = MenuDiario.objects.filter(empresa=empresa, fecha=manana).only("producto", "fecha").first()

    ventas = FacturaVenta.objects.filter(empresa=empresa).aggregate(
        mes=Sum("total", filter=Q(fecha__range=(inicio_mes, hoy))),
        dia=Sum("total", filter=Q(fecha=hoy)),
    )
    cobros = {"mes": 0}
    compras = {"mes": 0, "aprobar": 0}
    pagos = {"mes": 0}
    cxc = CuentaPorCobrar.objects.filter(empresa=empresa).aggregate(
        saldo_total=Sum("saldo", filter=~Q(estado__in=["COBRADA", "CANCELADA"])),
        vencidas=Count("id", filter=Q(fecha_vencimiento__lt=hoy, saldo__gt=0)),
        corriente=Sum("saldo", filter=Q(bucket_aging="CORRIENTE")),
        vencida=Sum("saldo", filter=~Q(bucket_aging="CORRIENTE")),
    )
    cxp = CuentaPorPagarEnterprise.objects.filter(empresa=empresa).aggregate(
        saldo_total=Sum("saldo", filter=~Q(estado__in=["PAGADA", "ANULADA"])),
        por_vencer=Count("id", filter=Q(vence_el__range=(hoy, fin_eventos), saldo__gt=0)),
        corriente=Sum("saldo", filter=Q(bucket_aging="CORRIENTE")),
        vencida=Sum("saldo", filter=~Q(bucket_aging="CORRIENTE")),
    )
    pedidos = {"hoy": 0, "urgentes": 0}
    entregas = {"pendientes": 0}
    planes = {"atrasados": 0}
    produccion = {"planificada": 0, "realizada": 0}
    inventario = ProductoInventario.objects.filter(empresa=empresa, activo=True).aggregate(
        criticos=Count("id", filter=Q(stock_actual__lte=F("stock_minimo"))),
    )
    recepciones_pendientes = RecepcionCompra.objects.filter(
        empresa=empresa, estado__in=["BORRADOR", "EN_PROCESO", "PARCIAL", "CON_DIFERENCIAS"]
    ).count()
    ordenes_compra_pendientes = OrdenCompraEnterprise.objects.filter(empresa=empresa).exclude(estado__in=["CERRADA", "CANCELADA", "FACTURADA"]).count()
    empleados_activos = Empleado.objects.filter(empresa=empresa, estado="ACTIVO").count()

    zero = Decimal("0")
    money = lambda value: value or zero
    kpis = (
        {"label": "Ventas del mes", "value": money(ventas["mes"]), "kind": "currency", "period": "Mes actual", "icon": "i-chart", "tone": "primary", "route": "comercial:dashboard"},
        {"label": "Cobros del mes", "value": money(cobros["mes"]), "kind": "currency", "period": "Mes actual", "icon": "i-bank", "tone": "success", "route": "comercial:o2c_full_dashboard"},
        {"label": "Compras del mes", "value": money(compras["mes"]), "kind": "currency", "period": "Mes actual", "icon": "i-cart", "tone": "neutral", "route": "compras:p2p_dashboard"},
        {"label": "Pagos del mes", "value": money(pagos["mes"]), "kind": "currency", "period": "Mes actual", "icon": "i-bank", "tone": "neutral", "route": "contabilidad:dashboard_enterprise"},
        {"label": "CxC pendiente", "value": money(cxc["saldo_total"]), "kind": "currency", "period": "Saldo abierto", "icon": "i-file", "tone": "warning", "route": "comercial:o2c_full_dashboard"},
        {"label": "CxP pendiente", "value": money(cxp["saldo_total"]), "kind": "currency", "period": "Saldo abierto", "icon": "i-file", "tone": "warning", "route": "contabilidad:dashboard_enterprise"},
        {"label": "Producción del día", "value": money(produccion["realizada"]), "kind": "number", "period": "Unidades realizadas", "icon": "i-box", "tone": "success", "route": "inventario:produccion_dashboard"},
        {"label": "Inventario crítico", "value": inventario["criticos"], "kind": "number", "period": "Productos bajo mínimo", "icon": "i-box", "tone": "danger", "route": "inventario:dashboard"},
    )
    attention_candidates = (
        ("CRÍTICA", "Facturas vencidas", cxc["vencidas"], "Cuentas por cobrar fuera de plazo", "comercial:o2c_full_dashboard", "danger"),
        ("ALTA", "Pagos por vencer", cxp["por_vencer"], "Próximos 7 días", "contabilidad:dashboard_enterprise", "warning"),
        ("ALTA", "Pedidos urgentes", pedidos["urgentes"], "Pedidos abiertos con prioridad urgente", "comercial:pedidos_dashboard", "warning"),
        ("MEDIA", "Entregas pendientes", entregas["pendientes"], "Pendientes, en ruta o en sitio", "comercial:o2c_full_dashboard", "info"),
        ("ALTA", "Producción atrasada", planes["atrasados"], "Planes anteriores sin cierre", "inventario:produccion_dashboard", "warning"),
        ("CRÍTICA", "Inventario crítico", inventario["criticos"], "Productos por debajo del mínimo", "inventario:dashboard", "danger"),
    )
    attention = [
        {"priority": priority, "title": title, "count": count, "reference": reference, "date": hoy, "route": route, "tone": tone}
        for priority, title, count, reference, route, tone in attention_candidates
        if count
    ][:6]

    activity = list(
        NavegacionReciente.objects.filter(empresa=empresa, usuario=request.user)
        .only("modulo", "etiqueta", "url", "visitado")[:8]
    )
    quick_actions = [
        {"label": "Nuevo cliente", "route": "comercial:cliente_crear", "icon": "i-users", "allowed": request.user.has_perm("comercial.add_cliente")},
        {"label": "Nueva cotización", "route": "comercial:cotizacion_crear", "icon": "i-file", "allowed": request.user.has_perm("comercial.add_cotizacionventa")},
        {"label": "Nuevo pedido", "route": "comercial:pedido_crear", "icon": "i-cart", "allowed": request.user.has_perm("comercial.add_pedido")},
        {"label": "Generar conduce", "route": "generar_conduces", "icon": "i-file", "allowed": empresa.modulo_conduces},
        {"label": "Registrar compra", "route": "compras:solicitud_crear", "icon": "i-cart", "allowed": empresa.modulo_compras and request.user.has_perm("compras.add_solicitudcompra")},
        {"label": "Facturar", "route": "facturacion", "icon": "i-file", "allowed": empresa.modulo_facturacion},
        {"label": "Registrar cobro", "route": "comercial:fin_cobro_registrar", "icon": "i-bank", "allowed": request.user.has_perm("comercial.registrar_cobro")},
        {"label": "Registrar pago", "route": "contabilidad:dashboard_enterprise", "icon": "i-bank", "allowed": request.user.has_perm("contabilidad.add_ordenpago")},
        {"label": "Ver reportes", "route": "comercial:o2c_reportes", "icon": "i-chart", "allowed": request.user.has_perm("comercial.view_facturaventa")},
    ]
    quick_actions = [item for item in quick_actions if item["allowed"]]
    hour = timezone.localtime().hour
    greeting = "Buenos días" if hour < 12 else "Buenas tardes" if hour < 19 else "Buenas noches"
    chart_data = {
        "sales": [float(money(ventas["mes"])), float(money(cobros["mes"]))],
        "purchases": [float(money(compras["mes"])), float(money(pagos["mes"]))],
        "production": [float(money(produccion["planificada"])), float(money(produccion["realizada"]))],
        "aging": [float(money(cxc["corriente"])), float(money(cxc["vencida"])), float(money(cxp["corriente"])), float(money(cxp["vencida"]))],
    }
    return render(request, "inicio.html", {
        "empresa": empresa, "greeting": greeting, "today": hoy,
        "orders_today": pedidos["hoy"], "pending_deliveries": entregas["pendientes"],
        "kpis": kpis, "attention": attention, "activity": activity,
        "quick_primary": quick_actions[:6],
        "quick_more": quick_actions[6:], "chart_data": chart_data,
        "has_financial_chart": any(chart_data["sales"]),
        "has_purchase_chart": any(chart_data["purchases"]),
        "has_production_chart": any(chart_data["production"]),
        "has_aging_chart": any(chart_data["aging"]),
        "total_raciones": total_raciones, "total_conduces": total_conduces,
        "total_centros": total_centros,
        "proyeccion_mes": Decimal(total_raciones) * Decimal("10.18"),
        "conduces_diarios": conduces_diarios,
        "production_labels": [formatear_fecha_grafico(item["fecha"]) for item in conduces_diarios],
        "production_values": [float(item["total"] or 0) for item in conduces_diarios],
        "production_average": (total_raciones / len(conduces_diarios)) if conduces_diarios else 0,
        "production_max": max((item["total"] or 0 for item in conduces_diarios), default=0),
        "production_min": min((item["total"] or 0 for item in conduces_diarios), default=0),
        "menu_manana": menu_manana, "tomorrow": manana,
        "centros_sin_menu": 0 if menu_manana else total_centros,
        "recepciones_pendientes": recepciones_pendientes,
        "financial": {"estimated": Decimal(total_raciones) * Decimal("10.18"), "billed": money(ventas["mes"]), "cxc": money(cxc["saldo_total"]), "cxp": money(cxp["saldo_total"]), "overdue_cxc": cxc["vencidas"], "overdue_cxp": cxp["por_vencer"]},
        "executive": {"sales_today": money(ventas["dia"]), "pending_purchase_orders": ordenes_compra_pendientes, "low_stock": inventario["criticos"], "active_employees": empleados_activos, "accounts_receivable": money(cxc["saldo_total"])},
    })


# =====================================================
# PLANTILLAS EXCEL
# =====================================================

@login_required(login_url="login_usuario")
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

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="plantilla_centros.xlsx"'
    wb.save(response)
    return response


@login_required(login_url="login_usuario")
def descargar_plantilla_menu(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Menu"
    ws.append(["fecha", "producto"])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="plantilla_menu.xlsx"'
    wb.save(response)
    return response


# =====================================================
# GESTIÓN DE CENTROS
# =====================================================

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_centros")
def pantalla_carga_centros(request):
    empresa = obtener_empresa(request)
    q = request.GET.get("q", "").strip()

    centros = CentroEducativo.objects.filter(empresa=empresa).order_by("orden_carga", "id")

    if q:
        centros = centros.filter(
            Q(codigo__icontains=q) |
            Q(nombre__icontains=q) |
            Q(director__icontains=q) |
            Q(provincia__icontains=q) |
            Q(regional_distrito__icontains=q)
        )

    total_centros = centros.count()
    centros_con_ubicacion = centros.exclude(latitud__isnull=True).exclude(longitud__isnull=True).count()

    return render(request, "carga_centros.html", {
        "empresa": empresa,
        "centros": centros,
        "q": q,
        "total_centros": total_centros,
        "centros_con_ubicacion": centros_con_ubicacion,
    })


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_centros")
def crear_centro(request):
    empresa = obtener_empresa(request)

    if request.method == "POST":
        codigo = request.POST.get("codigo", "").strip()
        nombre = request.POST.get("nombre", "").strip()

        if not codigo or not nombre:
            messages.error(request, "El código y el nombre del centro son obligatorios.")
            return redirect("carga_centros")

        existe = CentroEducativo.objects.filter(empresa=empresa, codigo=codigo).exists()
        if existe:
            messages.error(request, "Ya existe un centro con ese código para esta empresa.")
            return redirect("carga_centros")

        CentroEducativo.objects.create(
            empresa=empresa,
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
            orden_carga=CentroEducativo.objects.filter(empresa=empresa).count() + 1,
        )

        messages.success(request, "Centro creado correctamente.")

    return redirect("carga_centros")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_centros")
def editar_centro(request, centro_id):
    empresa = obtener_empresa(request)
    centro = get_object_or_404(CentroEducativo, id=centro_id, empresa=empresa)

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

    return render(request, "editar_centro.html", {"empresa": empresa, "centro": centro})


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_centros")
def eliminar_centro(request, centro_id):
    empresa = obtener_empresa(request)
    centro = get_object_or_404(CentroEducativo, id=centro_id, empresa=empresa)

    if request.method == "POST":
        centro.delete()
        messages.success(request, "Centro eliminado correctamente.")

    return redirect("carga_centros")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_centros")
def cargar_centros_excel(request):
    empresa = obtener_empresa(request)

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
                    empresa=empresa,
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

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_centros")
def mapa_centros(request):
    empresa = obtener_empresa(request)
    codigo = request.GET.get("codigo", "").strip()

    centros_con_ubicacion = (
        CentroEducativo.objects
        .filter(empresa=empresa)
        .exclude(latitud__isnull=True)
        .exclude(longitud__isnull=True)
        .order_by("codigo")
    )

    centro_buscado = None

    if codigo:
        centro_buscado = CentroEducativo.objects.filter(empresa=empresa, codigo__iexact=codigo).first()

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
        "empresa": empresa,
        "centros": centros_con_ubicacion,
        "centro_buscado": centro_buscado,
        "codigo": codigo,
        "centros_json": json.dumps(centros_json),
        "mensaje_ubicacion": mensaje_ubicacion,
    })


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_centros")
def actualizar_ubicacion_centro(request):
    empresa = obtener_empresa(request)

    if request.method == "POST":
        centro_id = request.POST.get("centro_id")
        latitud = request.POST.get("latitud", "").strip().replace(",", ".")
        longitud = request.POST.get("longitud", "").strip().replace(",", ".")

        centro = get_object_or_404(CentroEducativo, id=centro_id, empresa=empresa)

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

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
def pantalla_carga_menu(request):
    empresa = obtener_empresa(request)
    q = request.GET.get("q", "").strip()

    menus = MenuDiario.objects.filter(empresa=empresa).order_by("-fecha")

    if q:
        menus = menus.filter(
            Q(producto__icontains=q) |
            Q(fecha__icontains=q)
        )

    return render(request, "carga_menu.html", {
        "empresa": empresa,
        "menus": menus,
        "q": q,
    })


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
def crear_menu_diario(request):
    empresa = obtener_empresa(request)

    if request.method == "POST":
        fecha = request.POST.get("fecha")
        producto = request.POST.get("producto", "").strip()

        if fecha and producto:
            MenuDiario.objects.update_or_create(
                empresa=empresa,
                fecha=fecha,
                defaults={"producto": producto}
            )
            messages.success(request, "Menú creado correctamente.")
        else:
            messages.error(request, "Debe completar la fecha y el producto.")

    return redirect("carga_menu")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
def editar_menu_diario(request, menu_id):
    empresa = obtener_empresa(request)
    menu = get_object_or_404(MenuDiario, id=menu_id, empresa=empresa)

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

    return render(request, "editar_menu.html", {"empresa": empresa, "menu": menu})


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
def eliminar_menu_diario(request, menu_id):
    empresa = obtener_empresa(request)
    menu = get_object_or_404(MenuDiario, id=menu_id, empresa=empresa)

    if request.method == "POST":
        menu.delete()
        messages.success(request, "Menú eliminado correctamente.")

    return redirect("carga_menu")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
def cargar_menu_excel(request):
    empresa = obtener_empresa(request)

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
                    empresa=empresa,
                    fecha=fecha,
                    defaults={"producto": str(producto).strip()},
                )

        messages.success(request, "Menú cargado correctamente.")
        return redirect("carga_menu")

    return redirect("carga_menu")


# =====================================================
# GENERACIÓN DE CONDUCES
# =====================================================

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_conduces")
@suscripcion_requerida
def generar_conduces_automaticos(request):
    empresa = obtener_empresa(request)
    empresas = Empresa.objects.filter(id=empresa.id)

    if request.method == "POST":
        numero_inicial = request.POST.get("numero_inicial", "").strip()
        fecha_desde = request.POST.get("fecha_desde")
        fecha_hasta = request.POST.get("fecha_hasta")

        if not fecha_desde or not fecha_hasta:
            messages.error(request, "Debe completar las fechas.")
            return redirect("generar_conduces")

        try:
            fecha_desde = datetime.strptime(
                fecha_desde, "%Y-%m-%d"
            ).date()
            fecha_hasta = datetime.strptime(
                fecha_hasta, "%Y-%m-%d"
            ).date()
        except ValueError:
            messages.error(request, "El rango de fechas no es válido.")
            return redirect("generar_conduces")

        if fecha_desde > fecha_hasta:
            messages.error(
                request,
                "La fecha desde no puede ser mayor que la fecha hasta."
            )
            return redirect("generar_conduces")

        # -------------------------------------------------
        # Fuente operativa:
        # Programación de menú escolar materializada.
        #
        # Cada fila PROGRAMADO/EXTRAORDINARIO ya identifica:
        # fecha + centro + producto.
        # -------------------------------------------------
        programaciones = (
            ProgramacionMenuEscolar.objects
            .filter(
                empresa=empresa,
                fecha__range=[fecha_desde, fecha_hasta],
                estado__in=[
                    ProgramacionMenuEscolar.Estado.PROGRAMADO,
                    ProgramacionMenuEscolar.Estado.EXTRAORDINARIO,
                ],
            )
            .exclude(producto="")
            .select_related(
                "centro",
                "programa",
                "version",
                "asignacion",
            )
            .order_by(
                "fecha",
                "centro__orden_carga",
                "centro_id",
                "id",
            )
        )

        if not programaciones.exists():
            messages.error(
                request,
                "No hay programación de menú escolar disponible "
                "para generar conduces en ese rango de fechas."
            )
            return redirect("generar_conduces")

        def obtener_largo_formato(valor):
            return (
                len(str(valor))
                if str(valor).startswith("0")
                else None
            )

        # La numeración documental considera también conduces
        # eliminados lógicamente para evitar reutilizar números.
        ultimo = (
            Conduce.all_objects
            .filter(empresa=empresa)
            .order_by("-id")
            .first()
        )

        if numero_inicial:
            try:
                numero = int(numero_inicial)
            except ValueError:
                messages.error(
                    request,
                    "El número inicial de conduce debe ser numérico."
                )
                return redirect("generar_conduces")

            largo = obtener_largo_formato(numero_inicial)
            empresa.numero_inicial_conduce = numero_inicial
            empresa.save(update_fields=["numero_inicial_conduce"])

        elif ultimo and ultimo.numero and str(ultimo.numero).isdigit():
            numero = int(ultimo.numero) + 1
            largo = obtener_largo_formato(ultimo.numero)

        else:
            formato_base = str(
                empresa.numero_inicial_conduce or "1"
            )
            numero = int(formato_base)
            largo = obtener_largo_formato(formato_base)

        total_generados = 0
        total_existentes = 0

        for programacion in programaciones:
            # Un centro debe tener como máximo un conduce operativo
            # por fecha. También revisamos bajas lógicas para no
            # recrear silenciosamente un documento eliminado.
            existe = Conduce.all_objects.filter(
                empresa=empresa,
                fecha=programacion.fecha,
                centro=programacion.centro,
            ).exists()

            if existe:
                total_existentes += 1
                continue

            numero_final = (
                str(numero).zfill(largo)
                if largo
                else str(numero)
            )

            Conduce.objects.create(
                empresa=empresa,
                numero=numero_final,
                fecha=programacion.fecha,
                centro=programacion.centro,
                producto=programacion.producto,
                cantidad=programacion.centro.matricula,
                estado="borrador",
            )

            numero += 1
            total_generados += 1

        if total_generados:
            mensaje = (
                f"Se generaron {total_generados} conduces "
                f"desde la programación de menú escolar."
            )
            if total_existentes:
                mensaje += (
                    f" {total_existentes} ya existían y no "
                    f"se duplicaron."
                )
            messages.success(request, mensaje)
        else:
            messages.info(
                request,
                "No se generaron conduces nuevos. "
                f"{total_existentes} conduces del rango ya existían."
            )

        return redirect("generar_conduces")

    return render(
        request,
        "generar_conduces.html",
        {
            "empresa": empresa,
            "empresas": empresas,
        },
    )


# =====================================================
# BÚSQUEDA / EDICIÓN / ELIMINACIÓN DE CONDUCES
# =====================================================

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_conduces")
def buscar_conduces(request):
    empresa = obtener_empresa(request)

    conduces = (
        Conduce.objects
        .select_related("centro", "empresa")
        .filter(empresa=empresa)
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
        "empresa": empresa,
        "conduces": conduces,
        "q": q,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "estado": estado,
        "puede_eliminar_conduce": puede_eliminar_conduce(request.user),
    })


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_conduces")
def editar_conduce(request, conduce_id):
    empresa = obtener_empresa(request)
    conduce = get_object_or_404(Conduce, id=conduce_id, empresa=empresa)

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

    return render(request, "editar_conduce.html", {"empresa": empresa, "conduce": conduce})


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_conduces")
@permiso_eliminar_conduce_requerido
@require_POST
def eliminar_conduce(request, conduce_id):
    empresa = obtener_empresa(request)
    conduce = get_object_or_404(
        Conduce.all_objects,
        id=conduce_id,
        empresa=empresa,
    )

    numero = conduce.numero
    with transaction.atomic():
        eliminado = conduce.eliminar_logicamente(request.user)
        if eliminado:
            registrar_evento(
                empresa=empresa,
                accion="CAMBIAR_ESTADO",
                modulo="conduces",
                descripcion=f"Conduce {numero} eliminado logicamente.",
                usuario=request.user,
                objeto=conduce,
                request=request,
                datos_anteriores={"eliminado": False},
                datos_nuevos={"eliminado": True},
            )

    if eliminado:
        messages.success(request, f"Conduce {numero} eliminado correctamente.")
    else:
        messages.info(request, f"El conduce {numero} ya se encontraba eliminado.")

    return redirect("buscar_conduces")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_conduces")
def anular_conduce(request, conduce_id):
    empresa = obtener_empresa(request)

    conduce = get_object_or_404(
        Conduce,
        id=conduce_id,
        empresa=empresa,
    )

    if request.method != "POST":
        messages.error(
            request,
            "La anulación del conduce debe confirmarse desde el formulario.",
        )
        return redirect("vista_conduce", conduce_id=conduce.id)

    if conduce.estado == "anulado":
        messages.info(
            request,
            f"El conduce {conduce.numero} ya se encuentra anulado.",
        )
        return redirect("vista_conduce", conduce_id=conduce.id)

    motivo = request.POST.get("motivo_anulacion", "").strip()

    if not motivo:
        messages.error(
            request,
            "Debe indicar el motivo de anulación del conduce.",
        )
        return redirect("vista_conduce", conduce_id=conduce.id)

    conduce.estado = "anulado"
    conduce.observaciones = motivo
    conduce.save(update_fields=("estado", "observaciones"))

    messages.success(
        request,
        f"Conduce {conduce.numero} anulado correctamente. "
        "El motivo quedó registrado para fines documentales.",
    )

    return redirect("vista_conduce", conduce_id=conduce.id)



@login_required(login_url="login_usuario")
@modulo_requerido("modulo_conduces")
def vista_conduce(request, conduce_id):
    empresa = obtener_empresa(request)
    conduce = get_object_or_404(Conduce, id=conduce_id, empresa=empresa)
    return render(request, "vista_conduce.html", {"empresa": empresa, "conduce": conduce})


# =====================================================
# ACCIONES MASIVAS
# =====================================================

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_conduces")
def acciones_conduces(request):
    empresa = obtener_empresa(request)

    if request.method == "POST":
        ids_raw = request.POST.getlist("conduces")
        accion = request.POST.get("accion")

        ids = []

        for valor in ids_raw:
            valor_limpio = (
                str(valor)
                .replace("\xa0", "")
                .replace(" ", "")
                .strip()
            )

            if valor_limpio.isdigit():
                ids.append(int(valor_limpio))

        if not ids:
            messages.error(request, "Debe seleccionar al menos un conduce.")
            return redirect("buscar_conduces")

        conduces_qs = (
            Conduce.objects
            .filter(empresa=empresa, id__in=ids)
            .select_related("centro", "empresa")
        )

        conduces = list(conduces_qs)

        conduces.sort(
            key=lambda c: (
                c.fecha,
                int(c.numero) if str(c.numero).isdigit() else 0,
                c.centro.orden_carga,
                c.centro.nombre,
            )
        )

        if accion == "anular":
            motivo_anulacion = request.POST.get(
                "motivo_anulacion",
                "",
            ).strip()

            if not motivo_anulacion:
                messages.error(
                    request,
                    "Debe indicar el motivo de anulación de los conduces seleccionados.",
                )
                return redirect("buscar_conduces")

            conduces_a_anular = conduces_qs.exclude(estado="anulado")

            cantidad_anulados = conduces_a_anular.count()

            conduces_a_anular.update(
                estado="anulado",
                observaciones=motivo_anulacion,
            )

            messages.success(
                request,
                f"{cantidad_anulados} conduce(s) anulado(s) correctamente. "
                "El motivo quedó registrado para fines documentales.",
            )
            return redirect("buscar_conduces")

        if accion == "entregado":
            conduces_qs.update(estado="entregado")
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
                conduce for conduce in conduces
                if conduce.estado != "anulado"
            ]
            pdf = generar_pdf_relacion_diaria(conduces_validos)
            return FileResponse(pdf, content_type="application/pdf")

    return redirect("buscar_conduces")


# =====================================================
# PDF CONDUCE INDIVIDUAL
# =====================================================

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_conduces")
def visualizar_pdf_conduce(request, conduce_id):
    empresa = obtener_empresa(request)
    conduce = get_object_or_404(Conduce, id=conduce_id, empresa=empresa)
    archivo_pdf = generar_pdf_conduce(conduce)

    return FileResponse(open(archivo_pdf, "rb"), content_type="application/pdf")


# =====================================================
# RELACIÓN DIARIA
# =====================================================

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
def generar_relacion_diaria_pdf(request):
    empresa = obtener_empresa(request)

    fecha = request.GET.get("fecha")
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    if fecha:
        fecha = convertir_fecha(fecha)

        if not fecha:
            return HttpResponse(
                "Formato de fecha inválido. Use el formato YYYY-MM-DD.",
                status=400
            )

        conduces = (
            Conduce.objects
            .filter(empresa=empresa, fecha=fecha)
            .exclude(estado="anulado")
            .select_related("empresa", "centro")
            .order_by("fecha", "numero")
        )

    else:
        fecha_inicio = convertir_fecha(fecha_inicio)
        fecha_fin = convertir_fecha(fecha_fin)

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
            .filter(empresa=empresa, fecha__range=[fecha_inicio, fecha_fin])
            .exclude(estado="anulado")
            .select_related("empresa", "centro")
            .order_by("fecha", "numero")
        )

    if not conduces.exists():
        return HttpResponse(
            "No hay conduces válidos para esa fecha o rango seleccionado.",
            status=404
        )

    pdf = generar_pdf_relacion_diaria(conduces)

    return FileResponse(
        pdf,
        content_type="application/pdf",
        filename="relacion_diaria.pdf"
    )
@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
def preparar_nota_aclaratoria(request):
    """
    Compatibilidad con el flujo anterior.

    Cualquier acceso antiguo a Preparar nota aclaratoria
    es enviado al nuevo motor documental conservando el
    rango de fechas seleccionado.
    """
    from urllib.parse import urlencode
    from django.urls import reverse

    fecha_inicio = request.GET.get("fecha_inicio", "").strip()
    fecha_fin = request.GET.get("fecha_fin", "").strip()

    parametros = {}

    if fecha_inicio:
        parametros["fecha_inicio"] = fecha_inicio

    if fecha_fin:
        parametros["fecha_fin"] = fecha_fin

    url = reverse("nuevo_documento_institucional")

    if parametros:
        url += "?" + urlencode(parametros)

    return redirect(url)

# =====================================================
# NOTA ACLARATORIA
# =====================================================

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
def generar_nota_aclaratoria_pdf(request):
    empresa = obtener_empresa(request)

    fecha_inicio = convertir_fecha(request.GET.get("fecha_inicio"))
    fecha_fin = convertir_fecha(request.GET.get("fecha_fin"))

    comentario = request.GET.get("comentario", "").strip()
    firmante = request.GET.get("firmante", "").strip() or empresa.nombre
    cargo = request.GET.get("cargo", "").strip() or "Representante autorizado"

    if not fecha_inicio or not fecha_fin:
        return HttpResponse("Debe seleccionar fecha inicio y fecha final.", status=400)

    if fecha_inicio > fecha_fin:
        return HttpResponse("La fecha de inicio no puede ser mayor que la fecha final.", status=400)

    conduces = (
        Conduce.objects
        .filter(
            empresa=empresa,
            fecha__range=[fecha_inicio, fecha_fin],
            estado="anulado"
        )
        .select_related("centro", "empresa")
        .order_by("fecha", "numero")
    )

    dias_no_docencia = DiaNoDocencia.objects.filter(
        empresa=empresa,
        fecha__range=[fecha_inicio, fecha_fin],
        activo=True
    ).order_by("fecha")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    width, height = letter
    margen_x = 55
    ancho_texto = width - (margen_x * 2)

    dias_semana = {
        0: "Lunes",
        1: "Martes",
        2: "Miércoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sábado",
        6: "Domingo",
    }

    meses_texto = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }

    estilo_texto = ParagraphStyle(
        name="TextoNota",
        fontName="Helvetica",
        fontSize=8.2,
        leading=12,
        alignment=TA_LEFT,
    )

    estilo_centro = ParagraphStyle(
        name="CentroNota",
        fontName="Helvetica",
        fontSize=5.7,
        leading=6.6,
        alignment=TA_LEFT,
    )

    def fecha_larga(fecha):
        return f"{fecha.day} de {meses_texto[fecha.month]} de {fecha.year}"

    def dibujar_pagina():
        pdf.setFont("Helvetica", 7)
        pdf.drawCentredString(
            width / 2,
            25,
            f"Página {pdf.getPageNumber()}"
        )

    def dibujar_encabezado():
        y = 745

        if empresa.logo:
            try:
                with empresa.logo.storage.open(
                    empresa.logo.name,
                    "rb",
                ) as archivo_logo:
                    logo = ImageReader(
                        BytesIO(archivo_logo.read())
                    )
                pdf.drawImage(
                    logo,
                    width / 2 - 45,
                    704,
                    width=90,
                    height=52,
                    preserveAspectRatio=True,
                    mask="auto"
                )
                y = 698
            except Exception:
                pass

        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawCentredString(width / 2, y, (empresa.nombre or "").upper())

        y -= 12
        pdf.setFont("Helvetica", 7)
        pdf.drawCentredString(width / 2, y, empresa.direccion or "")

        y -= 10
        pdf.drawCentredString(width / 2, y, f"Teléfono.: {empresa.telefono or ''}")

        y -= 10
        pdf.drawCentredString(width / 2, y, f"RNC.: {empresa.rnc or ''}")

        return y - 30

    def nueva_pagina_con_encabezado():
        dibujar_pagina()
        pdf.showPage()
        return dibujar_encabezado()

    y = dibujar_encabezado()

    ciudad = empresa.ciudad or "Santo Domingo Este"

    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(width - margen_x, y, ciudad)

    y -= 11
    pdf.drawRightString(width - margen_x, y, fecha_larga(timezone.localdate()))

    y -= 30

    pdf.setFont("Helvetica-Bold", 8.2)
    pdf.drawString(margen_x, y, "Señores:")

    y -= 12
    pdf.drawString(margen_x, y, "Instituto Nacional de Bienestar Estudiantil (INABIE)")

    y -= 12
    pdf.setFont("Helvetica", 8)
    pdf.drawString(margen_x, y, "Su despacho.-")

    y -= 36

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(margen_x, y, "NOTA ACLARATORIA")

    y -= 35

    pdf.setFont("Helvetica", 8.2)
    pdf.drawString(margen_x, y, "Estimados señores:")

    y -= 24

    if conduces.exists():
        texto_intro = (
            "Por medio de la presente, dejamos constancia de que los centros educativos "
            "que se detallan a continuación no recibieron el suministro de alimentos sólidos "
            "en las fechas indicadas, debido a la suspensión de la docencia."
        )
    elif dias_no_docencia.exists():
        texto_intro = (
            "Por medio de la presente, dejamos constancia de los días no laborables, "
            "feriados o de no docencia registrados para el período indicado."
        )
    else:
        texto_intro = (
            "Por medio de la presente, dejamos constancia de que no se registran conduces "
            "anulados ni días no laborables para el período indicado."
        )

    parrafo_intro = Paragraph(texto_intro, estilo_texto)
    _, alto_intro = parrafo_intro.wrap(ancho_texto, 90)
    parrafo_intro.drawOn(pdf, margen_x, y - alto_intro)

    y = y - alto_intro - 16

    col_widths = [39, 49, 58, 210, 40, 50, 40, 40]

    def crear_tabla(tabla_data):
        tabla = Table(tabla_data, colWidths=col_widths, repeatRows=1)

        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 4.9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 5.5),
            ("ALIGN", (0, 1), (2, -1), "CENTER"),
            ("ALIGN", (4, 1), (-1, -1), "CENTER"),

            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black),

            ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))

        return tabla

    if conduces.exists():
        data = [[
            "FECHA",
            "NO. DE\nCONDUCE",
            "CÓDIGO DEL\nCENTRO\nEDUCATIVO",
            "NOMBRE DEL CENTRO EDUCATIVO",
            "PAN",
            "PAN CON\nVEGETALES",
            "GALLETA",
            "BIZCOCHO",
        ]]

        total_pan = 0
        total_pan_vegetales = 0
        total_galleta = 0
        total_bizcocho = 0

        for conduce in conduces:
            cantidad = conduce.cantidad or 0
            pan, pan_vegetales, galleta, bizcocho = clasificar_producto(conduce.producto, cantidad)

            total_pan += pan if pan != "" else 0
            total_pan_vegetales += pan_vegetales if pan_vegetales != "" else 0
            total_galleta += galleta if galleta != "" else 0
            total_bizcocho += bizcocho if bizcocho != "" else 0

            data.append([
                conduce.fecha.strftime("%d/%m/%Y"),
                str(conduce.numero),
                str(conduce.centro.codigo),
                Paragraph((conduce.centro.nombre or "").upper(), estilo_centro),
                f"{pan:,}" if pan != "" else "",
                f"{pan_vegetales:,}" if pan_vegetales != "" else "",
                f"{galleta:,}" if galleta != "" else "",
                f"{bizcocho:,}" if bizcocho != "" else "",
            ])

        data.append([
            "",
            "",
            "",
            "TOTAL",
            "-" if int(total_pan or 0) == 0 else f"{total_pan:,}",
            "-" if int(total_pan_vegetales or 0) == 0 else f"{total_pan_vegetales:,}",
            "-" if int(total_galleta or 0) == 0 else f"{total_galleta:,}",
            "-" if int(total_bizcocho or 0) == 0 else f"{total_bizcocho:,}",
        ])

        encabezado_tabla = data[0]
        filas_tabla = data[1:]
        indice = 0

        while indice < len(filas_tabla):
            espacio_disponible = y - 80

            if espacio_disponible < 90:
                y = nueva_pagina_con_encabezado()
                espacio_disponible = y - 80

            max_filas = len(filas_tabla) - indice
            tabla = None
            alto_tabla = 0
            filas_que_caben = 0

            for cantidad_filas in range(max_filas, 0, -1):
                bloque = filas_tabla[indice:indice + cantidad_filas]
                tabla_data = [encabezado_tabla] + bloque
                tabla_prueba = crear_tabla(tabla_data)

                _, alto_prueba = tabla_prueba.wrap(0, 0)

                if alto_prueba <= espacio_disponible:
                    tabla = tabla_prueba
                    alto_tabla = alto_prueba
                    filas_que_caben = cantidad_filas
                    break

            if tabla is None:
                y = nueva_pagina_con_encabezado()
                continue

            tabla.drawOn(pdf, margen_x, y - alto_tabla)

            y = y - alto_tabla - 18
            indice += filas_que_caben

    if dias_no_docencia.exists():
        texto_posterior = (
            "En las fechas detalladas a continuación no se realizó la entrega de raciones "
            "alimentarias a los centros educativos, debido a la suspensión oficial de la "
            "docencia por motivo de días feriados nacionales establecidos en el calendario "
            "laboral y escolar correspondiente."
        )

        parrafo_posterior = Paragraph(texto_posterior, estilo_texto)
        _, alto_posterior = parrafo_posterior.wrap(ancho_texto, 90)

        if y - alto_posterior < 100:
            y = nueva_pagina_con_encabezado()

        parrafo_posterior.drawOn(pdf, margen_x, y - alto_posterior)
        y = y - alto_posterior - 20

        contador = 1

        for dia in dias_no_docencia:
            fecha = dia.fecha

            titulo_dia = (
                f"{contador}. {dias_semana[fecha.weekday()]} "
                f"{fecha.day} de {meses_texto[fecha.month]} de {fecha.year}"
            )

            detalle_dia = f"{dia.motivo}. {dia.observacion or ''}"

            if y < 125:
                y = nueva_pagina_con_encabezado()

            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(margen_x, y, titulo_dia)

            y -= 15

            parrafo_dia = Paragraph(detalle_dia, estilo_texto)
            _, alto_dia = parrafo_dia.wrap(ancho_texto, 85)

            parrafo_dia.drawOn(pdf, margen_x, y - alto_dia)
            y = y - alto_dia - 16

            contador += 1

    if comentario:
        if y < 125:
            y = nueva_pagina_con_encabezado()

        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(margen_x, y, "Información adicional:")

        y -= 14

        parrafo_comentario = Paragraph(comentario, estilo_texto)
        _, alto_comentario = parrafo_comentario.wrap(ancho_texto, 95)

        parrafo_comentario.drawOn(pdf, margen_x, y - alto_comentario)
        y = y - alto_comentario - 24

    cierre = (
        "Sin otro particular, quedamos a la orden para cualquier información adicional "
        "que se requiera."
    )

    parrafo_cierre = Paragraph(cierre, estilo_texto)
    _, alto_cierre = parrafo_cierre.wrap(ancho_texto, 70)

    if y - alto_cierre < 135:
        y = nueva_pagina_con_encabezado()

    parrafo_cierre.drawOn(pdf, margen_x, y - alto_cierre)
    y = y - alto_cierre - 38

    if y < 130:
        y = nueva_pagina_con_encabezado()

    pdf.setFont("Helvetica", 8.2)
    pdf.drawString(margen_x, y, "Atentamente:")

    y -= 58

    pdf.line(margen_x, y, margen_x + 220, y)

    y -= 12

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(margen_x, y, firmante.upper())

    y -= 10

    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(margen_x, y, cargo.upper())

    dibujar_pagina()

    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="nota_aclaratoria.pdf"'
    return response


# =====================================================
# RELACIÓN GENERAL
# =====================================================

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
def generar_relacion_general_pdf(request):
    empresa = obtener_empresa(request)

    if not empresa:
        return HttpResponse("Debe registrar una empresa antes de generar la relación general.", status=400)

    fecha_inicio = convertir_fecha(request.GET.get("fecha_inicio"))
    fecha_fin = convertir_fecha(request.GET.get("fecha_fin"))

    if not fecha_inicio or not fecha_fin:
        return HttpResponse("Debe seleccionar fecha inicio y fecha final.", status=400)

    if fecha_inicio > fecha_fin:
        return HttpResponse("La fecha de inicio no puede ser mayor que la fecha final.", status=400)

    conduces = (
        Conduce.objects
        .filter(empresa=empresa, fecha__range=[fecha_inicio, fecha_fin])
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

    filas_por_pagina = 35
    row_height = 13
    header_height = 30
    alto_total = 14
    margen_inferior_seguro = 95

    meses_texto = nombre_mes(fecha_inicio, fecha_fin)

    estilo_nombre = ParagraphStyle(
        name="NombreCentro",
        fontName="Helvetica",
        fontSize=5.4,
        leading=6,
        alignment=TA_LEFT
    )

    estilo_header = ParagraphStyle(
        name="Header",
        fontName="Helvetica-Bold",
        fontSize=5.2,
        leading=5.8,
        alignment=TA_CENTER
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
        pan, pan_vegetales, galleta, bizcocho = clasificar_producto(conduce.producto, cantidad)

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

    def crear_tabla_principal(data, row_heights):
        tabla = Table(data, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)

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

        return tabla

    def crear_tabla_total():
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

        tabla_total = Table(total_data, colWidths=col_widths, rowHeights=[alto_total])

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

        return tabla_total

    pagina = 1
    indice = 0
    ultima_y_tabla = tabla_top_y

    while indice < len(filas):
        dibujar_encabezado(pagina)

        bloque = filas[indice:indice + filas_por_pagina]
        data = [encabezados] + bloque
        row_heights = [header_height] + [row_height] * len(bloque)

        tabla = crear_tabla_principal(data, row_heights)

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
        ultima_y_tabla = tabla_top_y

    tabla_total = crear_tabla_total()
    _, alto_tabla_total = tabla_total.wrap(0, 0)

    espacio_necesario = alto_tabla_total + 48
    y_total = ultima_y_tabla - 14

    if y_total < margen_inferior_seguro + espacio_necesario:
        pdf.showPage()
        pagina += 1
        total_paginas += 1
        dibujar_encabezado(pagina)
        y_total = tabla_top_y - alto_tabla_total

    tabla_total.drawOn(pdf, x_tabla, y_total)

    y_firma = y_total - 38

    if y_firma < 70:
        pdf.showPage()
        pagina += 1
        total_paginas += 1
        dibujar_encabezado(pagina)
        y_firma = tabla_top_y - 40

    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.line(x_tabla + 20, y_firma, x_tabla + 195, y_firma)
    pdf.drawString(x_tabla + 30, y_firma - 12, "FIRMA Y SELLO DEL SUPLIDOR")

    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="relacion_general_conduces.pdf"'
    return response


# =====================================================
# GESTIÓN DE FACTURACIÓN
# =====================================================

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def facturacion(request):
    empresa = obtener_empresa(request)

    empresas = Empresa.objects.filter(id=empresa.id)
    productos = ProductoFacturacion.objects.filter(empresa=empresa).order_by("id")
    comprobantes = ComprobanteFiscal.objects.filter(empresa=empresa).order_by("ncf")
    comprobantes_disponibles = ComprobanteFiscal.objects.filter(empresa=empresa, usado=False).order_by("ncf")
    facturas = Factura.objects.select_related("empresa", "comprobante").filter(empresa=empresa).order_by("-fecha_factura", "-id")

    total_facturado = facturas.exclude(estado="anulada").aggregate(total=Sum("total"))["total"] or 0
    total_itbis = facturas.exclude(estado="anulada").aggregate(total=Sum("itbis"))["total"] or 0

    return render(request, "facturacion.html", {
        "empresa": empresa,
        "empresas": empresas,
        "productos": productos,
        "comprobantes": comprobantes,
        "comprobantes_disponibles": comprobantes_disponibles,
        "facturas": facturas,
        "total_facturado": total_facturado,
        "total_itbis": total_itbis,
    })


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def crear_producto_facturacion(request):
    empresa = obtener_empresa(request)

    if request.method == "POST":
        categoria = request.POST.get("categoria")
        nombre_factura = request.POST.get("nombre", "").strip()
        precio = request.POST.get("precio_sin_itbis", "0").replace(",", ".")
        aplica_itbis = request.POST.get("aplica_itbis") == "on"
        porcentaje_itbis = request.POST.get("porcentaje_itbis", "18").replace(",", ".")

        ProductoFacturacion.objects.update_or_create(
            empresa=empresa,
            categoria=categoria,
            defaults={
                "nombre_factura": nombre_factura,
                "precio_sin_itbis": Decimal(precio),
                "aplica_itbis": aplica_itbis,
                "porcentaje_itbis": Decimal(porcentaje_itbis),
                "activo": True,
            }
        )

        messages.success(request, "Producto de facturación guardado correctamente.")

    return redirect("facturacion")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def editar_producto_facturacion(request, producto_id):
    empresa = obtener_empresa(request)
    producto = get_object_or_404(ProductoFacturacion, id=producto_id, empresa=empresa)

    if request.method == "POST":
        producto.categoria = request.POST.get("categoria")
        producto.nombre_factura = request.POST.get("nombre_factura", "").strip()
        producto.precio_sin_itbis = Decimal(request.POST.get("precio_sin_itbis", "0").replace(",", "."))
        producto.aplica_itbis = request.POST.get("aplica_itbis") == "on"
        producto.porcentaje_itbis = Decimal(request.POST.get("porcentaje_itbis", "18").replace(",", "."))
        producto.activo = request.POST.get("activo") == "on"
        producto.save()

        messages.success(request, "Producto actualizado correctamente.")
        return redirect("facturacion")

    return render(request, "editar_producto_facturacion.html", {"empresa": empresa, "producto": producto})


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def eliminar_producto_facturacion(request, producto_id):
    empresa = obtener_empresa(request)
    producto = get_object_or_404(ProductoFacturacion, id=producto_id, empresa=empresa)

    if request.method == "POST":
        producto.delete()
        messages.success(request, "Producto eliminado correctamente.")

    return redirect("facturacion")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def crear_comprobante_fiscal(request):
    empresa = obtener_empresa(request)

    if request.method == "POST":
        tipo = request.POST.get("tipo", "B15").strip().upper()
        ncf = request.POST.get("ncf", "").strip().upper()
        fecha_validez = request.POST.get("fecha_validez")

        if not ncf or not fecha_validez:
            messages.error(request, "Debe completar el NCF/e-NCF y la fecha de validez.")
            return redirect("facturacion")

        if tipo != "OTRO" and not ncf.startswith(tipo):
            messages.error(request, f"El NCF/e-NCF debe iniciar con {tipo}. Ejemplo: {tipo}00000001.")
            return redirect("facturacion")

        comprobante, creado = ComprobanteFiscal.objects.get_or_create(
            empresa=empresa,
            ncf=ncf,
            defaults={
                "tipo": tipo,
                "fecha_validez": fecha_validez,
                "usado": False,
            }
        )

        if not creado:
            comprobante.tipo = tipo
            comprobante.fecha_validez = fecha_validez
            comprobante.save()
            messages.success(request, "Comprobante actualizado correctamente.")
        else:
            messages.success(request, "Comprobante registrado correctamente.")

    return redirect("facturacion")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def crear_rango_ncf(request):
    empresa = obtener_empresa(request)

    if request.method == "POST":
        tipo = request.POST.get("tipo", "B15").strip().upper()
        prefijo = request.POST.get("prefijo", tipo).strip().upper()
        desde = int(request.POST.get("desde"))
        hasta = int(request.POST.get("hasta"))
        fecha_validez = request.POST.get("fecha_validez")

        if desde > hasta:
            messages.error(request, "El rango indicado no es válido.")
            return redirect("facturacion")

        if tipo != "OTRO" and prefijo != tipo:
            messages.error(request, f"El prefijo debe coincidir con el tipo seleccionado: {tipo}.")
            return redirect("facturacion")

        RangoComprobanteGubernamental.objects.create(
            prefijo=prefijo,
            numero_desde=desde,
            numero_hasta=hasta,
            fecha_validez=fecha_validez,
        )

        creados = 0

        for numero in range(desde, hasta + 1):
            ncf = f"{prefijo}{str(numero).zfill(8)}"

            _, created = ComprobanteFiscal.objects.get_or_create(
                empresa=empresa,
                ncf=ncf,
                defaults={
                    "tipo": tipo,
                    "fecha_validez": fecha_validez,
                    "usado": False,
                }
            )

            if created:
                creados += 1

        messages.success(request, f"{creados} comprobantes creados correctamente.")

    return redirect("facturacion")


@transaction.atomic
@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
@suscripcion_requerida
def generar_factura(request):
    empresa = obtener_empresa(request)

    if request.method != "POST":
        return redirect("facturacion")

    fecha_inicio = request.POST.get("fecha_inicio")
    fecha_fin = request.POST.get("fecha_fin")
    comprobante_id = request.POST.get("comprobante")
    bloques = int(request.POST.get("bloques") or 1)

    if not fecha_inicio or not fecha_fin:
        messages.error(request, "Debe completar fecha inicio y fecha fin.")
        return redirect("facturacion")

    fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

    conduces = (
        Conduce.objects
        .filter(empresa=empresa, fecha__range=[fecha_inicio, fecha_fin])
        .exclude(estado="anulado")
        .select_related("centro", "empresa")
        .order_by("fecha", "numero")
    )

    if not conduces.exists():
        messages.error(request, "No existen conduces válidos para ese período.")
        return redirect("facturacion")

    if comprobante_id:
        comprobante = get_object_or_404(ComprobanteFiscal, id=comprobante_id, empresa=empresa, usado=False)
    else:
        comprobante = ComprobanteFiscal.objects.filter(empresa=empresa, usado=False).order_by("ncf").first()

    if not comprobante:
        messages.error(request, "No hay comprobantes disponibles.")
        return redirect("facturacion")

    productos_config = {p.categoria: p for p in ProductoFacturacion.objects.filter(empresa=empresa, activo=True)}
    categorias_requeridas = ["PAN", "PAN_CON_VEGETALES", "GALLETA", "BIZCOCHO"]

    for categoria in categorias_requeridas:
        if categoria not in productos_config:
            messages.error(request, f"Falta configurar el producto de facturación: {categoria}.")
            return redirect("facturacion")

    cantidades = {"PAN": 0, "PAN_CON_VEGETALES": 0, "GALLETA": 0, "BIZCOCHO": 0}

    for conduce in conduces:
        categoria = clasificar_categoria_factura(conduce.producto)
        cantidades[categoria] += conduce.cantidad or 0

    conduces_lista = list(conduces)

    def numero_orden(conduce):
        try:
            return int(conduce.numero)
        except Exception:
            return 0

    conduces_lista.sort(key=numero_orden)

    conduce_inicial = conduces_lista[0].numero
    conduce_final = conduces_lista[-1].numero

    fecha_factura = max(c.fecha for c in conduces_lista)
    primera_entrega = min(c.fecha for c in conduces_lista)
    ultima_entrega = max(c.fecha for c in conduces_lista)

    factura = Factura.objects.create(
        empresa=empresa,
        comprobante=comprobante,
        fecha_factura=fecha_factura,
        fecha_inicio=primera_entrega,
        fecha_fin=ultima_entrega,
        cantidad_conduces=len(conduces_lista),
        conduce_inicial=conduce_inicial,
        conduce_final=conduce_final,
        bloques=bloques,
        estado="emitida",
    )

    subtotal_exento = Decimal("0.00")
    subtotal_gravado = Decimal("0.00")

    for categoria, cantidad in cantidades.items():
        producto_config = productos_config[categoria]
        precio = producto_config.precio_sin_itbis
        valor = Decimal(cantidad) * precio

        DetalleFactura.objects.create(
            factura=factura,
            producto=producto_config.nombre_factura,
            categoria=categoria,
            cantidad=cantidad,
            precio_sin_itbis=precio,
            aplica_itbis=producto_config.aplica_itbis,
            valor=valor,
        )

        if producto_config.aplica_itbis:
            subtotal_gravado += valor
        else:
            subtotal_exento += valor

    subtotal = subtotal_exento + subtotal_gravado

    porcentaje_itbis = Decimal("18.00")
    productos_gravados = ProductoFacturacion.objects.filter(empresa=empresa, activo=True, aplica_itbis=True)

    if productos_gravados.exists():
        porcentaje_itbis = productos_gravados.first().porcentaje_itbis

    itbis = subtotal_gravado * (porcentaje_itbis / Decimal("100"))
    total = subtotal + itbis

    factura.subtotal_exento = subtotal_exento
    factura.subtotal_gravado = subtotal_gravado
    factura.subtotal = subtotal
    factura.itbis = itbis
    factura.total = total
    factura.save()

    comprobante.usado = True
    comprobante.fecha_uso = timezone.localdate()
    comprobante.save()

    messages.success(request, f"Factura generada correctamente con NCF {comprobante.ncf}.")

    return redirect("facturacion")


@transaction.atomic
@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def editar_factura(request, factura_id):
    empresa = obtener_empresa(request)

    factura = get_object_or_404(
        Factura.objects.select_related("comprobante", "empresa"),
        id=factura_id,
        empresa=empresa
    )

    comprobantes_disponibles = ComprobanteFiscal.objects.filter(empresa=empresa, usado=False).order_by("ncf")

    if request.method == "POST":
        factura.bloques = int(request.POST.get("bloques", 1))
        factura.estado = request.POST.get("estado", factura.estado)

        comprobante_id = request.POST.get("comprobante")

        if comprobante_id:
            nuevo = get_object_or_404(ComprobanteFiscal, id=comprobante_id, empresa=empresa)

            if factura.comprobante and factura.comprobante.id != nuevo.id:
                factura.comprobante.usado = False
                factura.comprobante.fecha_uso = None
                factura.comprobante.save()

            factura.comprobante = nuevo
            nuevo.usado = True
            nuevo.fecha_uso = timezone.localdate()
            nuevo.save()

        factura.es_electronica = request.POST.get("es_electronica") == "on"
        factura.encf = request.POST.get("encf") or None
        factura.codigo_seguridad = request.POST.get("codigo_seguridad") or None
        factura.url_qr = request.POST.get("url_qr") or None

        fecha_firma = request.POST.get("fecha_firma_digital")

        if fecha_firma:
            factura.fecha_firma_digital = datetime.strptime(fecha_firma, "%Y-%m-%dT%H:%M")
        else:
            factura.fecha_firma_digital = None

        factura.save()

        messages.success(request, "Factura actualizada correctamente.")
        return redirect("facturacion")

    return render(request, "editar_factura.html", {
        "empresa": empresa,
        "factura": factura,
        "comprobantes_disponibles": comprobantes_disponibles,
    })


@transaction.atomic
@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def anular_factura(request, factura_id):
    empresa = obtener_empresa(request)

    factura = get_object_or_404(
        Factura.objects.select_related("comprobante"),
        id=factura_id,
        empresa=empresa
    )

    if request.method == "POST":
        factura.estado = "anulada"
        factura.save()

        messages.success(request, "Factura anulada correctamente. El NCF permanece utilizado.")

    return redirect("facturacion")


@transaction.atomic
@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def eliminar_factura(request, factura_id):
    empresa = obtener_empresa(request)

    factura = get_object_or_404(
        Factura.objects.select_related("comprobante"),
        id=factura_id,
        empresa=empresa
    )

    if request.method == "POST":
        comprobante = factura.comprobante

        if comprobante:
            comprobante.usado = False
            comprobante.fecha_uso = None
            comprobante.save()

        factura.delete()

        messages.success(request, "Factura eliminada. El NCF quedó disponible nuevamente.")

    return redirect("facturacion")


def construir_url_qr_ecf(factura):
    empresa = factura.empresa
    comprobante = factura.comprobante

    encf = factura.encf or (comprobante.ncf if comprobante else "")

    if not factura.codigo_seguridad or not factura.fecha_firma_digital:
        return ""

    parametros = {
        "RncEmisor": empresa.rnc or "",
        "RncComprador": factura.cliente_rnc or "",
        "ENCF": encf,
        "FechaEmision": factura.fecha_factura.strftime("%d-%m-%Y"),
        "MontoTotal": formato_monto(factura.total).replace(",", ""),
        "FechaFirma": factura.fecha_firma_digital.strftime("%d-%m-%Y %H:%M:%S"),
        "CodigoSeguridad": factura.codigo_seguridad,
    }

    return "https://ecf.dgii.gov.do/ecf/ConsultaTimbre?" + urlencode(parametros)


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def pdf_factura(request, factura_id):
    empresa_usuario = obtener_empresa(request)

    factura = get_object_or_404(
        Factura.objects.select_related("empresa", "comprobante"),
        id=factura_id,
        empresa=empresa_usuario
    )

    detalles = factura.detalles.all().order_by("id")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    empresa = factura.empresa
    comprobante = factura.comprobante

    margin_left = 58
    margin_right = 58
    content_width = width - margin_left - margin_right

    x_left = margin_left
    x_right = 382

    y = 710

    pdf.setFont("Helvetica", 8)
    pdf.drawString(x_left, y, (empresa.nombre or "").upper())

    y -= 12
    pdf.drawString(x_left, y, empresa.direccion or "")

    y -= 12
    pdf.drawString(x_left, y, f"Ciudad {empresa.ciudad or ''}")

    y -= 12
    pdf.drawString(x_left, y, f"Teléfono  {empresa.telefono or ''}")

    y -= 12
    pdf.drawString(x_left, y, f"RNC-{empresa.rnc or ''}")

    y -= 12
    pdf.drawString(x_left, y, f"FECHA: {factura.fecha_factura.strftime('%d/%m/%Y')}")

    y_right = 710

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(x_right, y_right, "FACTURA GUBERNAMENTAL")

    pdf.setFont("Helvetica-Bold", 7)
    y_right -= 14
    pdf.drawString(x_right, y_right, f"NCF_{comprobante.ncf if comprobante else ''}")

    y_right -= 12
    pdf.drawString(x_right, y_right, f"VALIDO HASTA: {comprobante.fecha_validez.strftime('%d/%m/%Y') if comprobante else ''}")

    y = 575

    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawString(x_left, y, "CLIENTE :")
    pdf.drawString(x_left, y - 13, "RNC")

    pdf.drawString(160, y, factura.cliente_nombre.upper())
    pdf.drawString(160, y - 13, factura.cliente_rnc)

    y = 505

    pdf.setFont("Helvetica", 7)
    pdf.drawString(x_left, y, "Periodo de factura")

    periodo = f"Del {fecha_larga_es(factura.fecha_inicio)} al {fecha_larga_es(factura.fecha_fin)}"

    pdf.drawString(150, y, periodo)
    pdf.line(145, y - 2, 390, y - 2)

    y -= 26

    pdf.drawString(x_left, y, "Cantidad de conduces")
    pdf.line(150, y - 2, 245, y - 2)
    pdf.drawCentredString(197, y, str(factura.cantidad_conduces))

    pdf.drawString(265, y, "del No.")
    pdf.line(315, y - 2, 390, y - 2)
    pdf.drawCentredString(352, y, str(factura.conduce_inicial or ""))

    pdf.drawString(405, y, "al")
    pdf.line(430, y - 2, 505, y - 2)
    pdf.drawCentredString(467, y, str(factura.conduce_final or ""))

    y -= 14
    pdf.drawString(x_left, y, "Bloques")
    pdf.line(95, y - 2, 145, y - 2)
    pdf.drawCentredString(120, y, str(factura.bloques))

    data = [["PRODUCTO", "CANTIDAD", "PRECIO SIN ITEBIS", "VALOR RD$"]]

    for detalle in detalles:
        data.append([
            detalle.producto.upper(),
            formato_cantidad(detalle.cantidad),
            formato_monto(detalle.precio_sin_itbis),
            formato_monto(detalle.valor),
        ])

    table_x = margin_left
    table_top_y = 440

    col_producto = 120
    col_cantidad = 120
    col_precio = 170
    col_valor = content_width - col_producto - col_cantidad - col_precio

    row_heights = [18] + [26] * (len(data) - 1)
    table_height = sum(row_heights)
    table_bottom_y = table_top_y - table_height

    tabla = Table(data, colWidths=[col_producto, col_cantidad, col_precio, col_valor], rowHeights=row_heights)

    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 6.8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, -1), 6.8),
        ("ALIGN", (0, 1), (1, -1), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("RIGHTPADDING", (2, 1), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    tabla.wrapOn(pdf, width, height)
    tabla.drawOn(pdf, table_x, table_bottom_y)

    valor_col_x = table_x + col_producto + col_cantidad + col_precio
    valor_col_width = col_valor

    total_label_x = table_x + col_producto
    total_box_x = valor_col_x
    total_y = table_bottom_y - 24
    box_height = 24

    totales = [
        ("SUB-TOTAL PRODUCTOS EXENTOS", factura.subtotal_exento),
        ("SUB-TOTAL PRODUCTOS GRAVADOS", factura.subtotal_gravado),
        ("SUBTOTAL", factura.subtotal),
        ("ITBIS", factura.itbis),
        ("TOTAL", factura.total),
    ]

    for label, value in totales:
        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawString(total_label_x, total_y + 8, label)

        pdf.setFillColor(colors.lightgrey)
        pdf.rect(total_box_x, total_y, valor_col_width, box_height, fill=1, stroke=1)
        pdf.setFillColor(colors.black)

        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawRightString(total_box_x + valor_col_width - 5, total_y + 8, formato_monto(value))

        total_y -= box_height

    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawCentredString(width / 2, 155, "FIRMA Y SELLO DE LA EMPRESA")

    if factura.es_electronica and qrcode is not None:
        url_qr = factura.url_qr or construir_url_qr_ecf(factura)

        if url_qr:
            qr_img = qrcode.make(url_qr)
            qr_buffer = BytesIO()
            qr_img.save(qr_buffer, format="PNG")
            qr_buffer.seek(0)

            qr_reader = ImageReader(qr_buffer)

            qr_x = 58
            qr_y = 55
            qr_size = 95

            pdf.drawImage(qr_reader, qr_x, qr_y, qr_size, qr_size)

            pdf.setFont("Helvetica", 6)
            pdf.drawString(qr_x, qr_y - 10, f"Código de Seguridad: {factura.codigo_seguridad or ''}")

            if factura.fecha_firma_digital:
                pdf.drawString(qr_x, qr_y - 20, f"Fecha de Firma Digital: {factura.fecha_firma_digital.strftime('%d-%m-%Y %H:%M:%S')}")

    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="factura_{factura.id}.pdf"'
    return response


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def editar_comprobante(request, comprobante_id):
    empresa = obtener_empresa(request)
    comprobante = get_object_or_404(ComprobanteFiscal, id=comprobante_id, empresa=empresa)

    if request.method == "POST":
        if comprobante.usado:
            messages.error(request, "No se puede editar un comprobante ya utilizado.")
            return redirect("facturacion")

        comprobante.ncf = request.POST.get("ncf")
        comprobante.tipo = request.POST.get("tipo")
        comprobante.fecha_validez = request.POST.get("fecha_validez")
        comprobante.save()

        messages.success(request, "Comprobante actualizado correctamente.")
        return redirect("facturacion")

    return redirect("facturacion")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_facturacion")
def eliminar_comprobante(request, comprobante_id):
    empresa = obtener_empresa(request)
    comprobante = get_object_or_404(ComprobanteFiscal, id=comprobante_id, empresa=empresa)

    if comprobante.usado:
        messages.error(request, "No se puede eliminar un comprobante ya utilizado.")
    else:
        comprobante.delete()
        messages.success(request, "Comprobante eliminado correctamente.")

    return redirect("facturacion")


# =====================================================
# AUTENTICACIÓN / REGISTRO / VALIDACIÓN
# =====================================================

REENVIO_CODIGO_COOLDOWN_SEGUNDOS = 60
MAX_INTENTOS_CODIGO = 5


class ReenvioCodigoEnCooldown(Exception):
    def __init__(self, segundos_restantes):
        self.segundos_restantes = segundos_restantes
        super().__init__("reenviar_codigo_en_cooldown")


def _causa_email_segura(error):
    """Return diagnostic metadata without SMTP payloads, addresses or secrets."""
    causa = type(error).__name__
    errno = getattr(error, "errno", None)
    if errno is not None:
        causa = f"{causa}:errno={errno}"
    return causa


def _registrar_fallo_email(evento, user_id, error):
    details = safe_delivery_error(error)
    logger_verificacion_email.error(
        "%s_FALLIDO user_id=%s causa=%s status=%s request_id=%s",
        evento,
        user_id,
        details["category"],
        details["status"] or "n/a",
        details["request_id"] or "n/a",
    )


@transaction.atomic
def enviar_codigo_correo(user, tipo="correo", flujo="ENVIO_INICIAL"):
    evento = f"VERIFICACION_EMAIL_{flujo}"
    logger_verificacion_email.info(
        "%s_INICIADO user_id=%s tipo=%s",
        evento,
        user.pk,
        tipo,
    )

    if not user.email:
        error = ValueError("usuario_sin_email")
        _registrar_fallo_email(evento, user.pk, error)
        raise error

    if flujo == "REENVIO":
        ultimo = (
            CodigoValidacion.objects.filter(user=user, tipo=tipo, usado=False)
            .order_by("-creado_en")
            .first()
        )
        if ultimo and ultimo.esta_vigente():
            transcurridos = int((timezone.now() - ultimo.creado_en).total_seconds())
            if transcurridos < REENVIO_CODIGO_COOLDOWN_SEGUNDOS:
                restantes = REENVIO_CODIGO_COOLDOWN_SEGUNDOS - transcurridos
                logger_verificacion_email.warning(
                    "%s_FALLIDO user_id=%s causa=cooldown segundos_restantes=%s",
                    evento,
                    user.pk,
                    restantes,
                )
                raise ReenvioCodigoEnCooldown(restantes)

    CodigoValidacion.objects.filter(
        user=user,
        tipo=tipo,
        usado=False
    ).update(usado=True)

    codigo = CodigoValidacion.objects.create(
        user=user,
        tipo=tipo
    )

    asunto = "Código de verificación - SASTRE ERP"

    mensaje = f"""
Hola {user.username},

Tu código de validación es:

{codigo.codigo}

Este código vence en 15 minutos.

SASTRE ERP
"""

    try:
        result = send_transactional_email(
            subject=asunto,
            text=mensaje,
            recipients=[user.email],
            from_email=settings.DEFAULT_FROM_EMAIL,
            idempotency_key=f"verificacion/{flujo.lower()}/{codigo.pk}",
        )
    except Exception as error:
        _registrar_fallo_email(evento, user.pk, error)
        raise

    logger_verificacion_email.info(
        "%s_ENVIADO user_id=%s tipo=%s provider=%s message_id=%s",
        evento,
        user.pk,
        tipo,
        result.provider,
        result.message_id,
    )

    return codigo


@transaction.atomic
def registro(request):
    if request.method == "POST":
        nombre_usuario = (
            request.POST.get("username", "") or
            request.POST.get("nombre_usuario", "") or
            request.POST.get("nombre", "")
        ).strip()

        correo = (
            request.POST.get("email", "") or
            request.POST.get("correo", "")
        ).strip().lower()

        password = (
            request.POST.get("password1", "") or
            request.POST.get("password", "")
        )

        confirmar_password = (
            request.POST.get("password2", "") or
            request.POST.get("confirmar_password", "")
        )

        if not nombre_usuario or not correo or not password or not confirmar_password:
            messages.error(request, "Debe completar todos los campos obligatorios.")
            return redirect("registro")

        if password != confirmar_password:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect("registro")

        usuario_existente = User.objects.filter(username=correo).first()

        if usuario_existente:
            if not usuario_existente.is_active:
                request.session["usuario_pendiente_id"] = usuario_existente.id

                try:
                    enviar_codigo_correo(
                        usuario_existente,
                        tipo="correo",
                        flujo="REENVIO",
                    )
                    messages.warning(
                        request,
                        "Este correo ya inició registro. Te reenviamos el código de validación."
                    )
                except ReenvioCodigoEnCooldown as error:
                    messages.info(
                        request,
                        f"Espera {error.segundos_restantes} segundos antes de solicitar otro código.",
                    )
                except Exception:
                    messages.error(
                        request,
                        "El servicio de correo no está disponible temporalmente. Intenta más tarde.",
                    )

                return redirect("verificar_correo")

            messages.error(request, "Ya existe una cuenta registrada con este correo.")
            return redirect("registro")

        try:
            plan_basico = Plan.objects.filter(nombre__iexact="Básico").first()

            if not plan_basico:
                plan_basico = Plan.objects.create(
                    nombre="Básico",
                    precio=1500,
                    limite_conduces=500,
                    limite_usuarios=3,
                    almacenamiento_gb=1
                )

            empresa_saas = EmpresaSaaS.objects.create(
                nombre="Mi empresa",
                rnc="",
                correo=correo,
                activa=True
            )

            user = User.objects.create_user(
                username=correo,
                email=correo,
                password=password,
                first_name=nombre_usuario,
                is_active=False
            )

            Empresa.objects.create(
                usuario=user,
                nombre="Mi empresa",
                rnc="",
                telefono="",
                correo=correo,
                numero_inicial_conduce="0001",
            )

            PerfilUsuario.objects.create(
                user=user,
                empresa=empresa_saas,
                rol="admin_empresa",
                correo_validado=False,
                activo=True
            )

            Suscripcion.objects.create(
                empresa=empresa_saas,
                plan=plan_basico,
                estado="prueba",
                fecha_inicio=timezone.now().date(),
                fecha_fin=timezone.now().date() + timedelta(days=15),
                en_prueba=True
            )

            enviar_codigo_correo(user, tipo="correo")

            request.session["usuario_pendiente_id"] = user.id

            messages.success(
                request,
                "Cuenta creada correctamente. Te enviamos un código de validación al correo."
            )

            return redirect("verificar_correo")

        except Exception as e:
            transaction.set_rollback(True)
            logger_verificacion_email.error(
                "VERIFICACION_EMAIL_REGISTRO_FALLIDO causa=%s",
                _causa_email_segura(e),
            )

            messages.error(
                request,
                "No pudimos entregar el correo de verificación. El alta no fue completada; intenta más tarde."
            )

            return redirect("registro")

    return render(request, "registro.html")


def verificar_correo(request):
    user_id = request.session.get("usuario_pendiente_id")

    if not user_id:
        messages.error(request, "No hay usuario pendiente de validación.")
        return redirect("login_usuario")

    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        codigo_ingresado = request.POST.get("codigo", "").strip()

        with transaction.atomic():
            codigo = (
                CodigoValidacion.objects.select_for_update()
                .filter(user=user, tipo="correo", usado=False)
                .order_by("-creado_en")
                .first()
            )

            if not codigo:
                messages.error(request, "No hay un código activo. Solicita uno nuevo.")
                return redirect("verificar_correo")

            if not codigo.esta_vigente():
                codigo.usado = True
                codigo.save(update_fields=["usado"])
                messages.error(request, "El código expiró. Solicita uno nuevo.")
                return redirect("verificar_correo")

            if not secrets.compare_digest(codigo.codigo, codigo_ingresado):
                codigo.intentos_fallidos += 1
                if codigo.intentos_fallidos >= MAX_INTENTOS_CODIGO:
                    codigo.usado = True
                    codigo.save(update_fields=["intentos_fallidos", "usado"])
                    messages.error(
                        request,
                        "Superaste el máximo de intentos. Solicita un código nuevo.",
                    )
                else:
                    codigo.save(update_fields=["intentos_fallidos"])
                    messages.error(request, "Código incorrecto.")
                return redirect("verificar_correo")

            codigo.usado = True
            codigo.save(update_fields=["usado"])

        user.is_active = True
        user.save()

        perfil = PerfilUsuario.objects.filter(user=user).first()

        if perfil:
            perfil.correo_validado = True
            perfil.save()
            request.session["empresa_id"] = perfil.empresa.id if perfil.empresa else None

        login(request, user)
        request.session.pop("usuario_pendiente_id", None)

        messages.success(request, "Correo validado correctamente. Bienvenido.")
        return redirect("inicio")

    return render(request, "verificar_correo.html", {"correo": user.email})


@require_POST
def reenviar_codigo_correo(request):
    user_id = request.session.get("usuario_pendiente_id")

    if not user_id:
        logger_verificacion_email.info(
            "VERIFICACION_EMAIL_REENVIO_INICIADO user_id=ausente tipo=correo"
        )
        logger_verificacion_email.warning(
            "VERIFICACION_EMAIL_REENVIO_FALLIDO user_id=ausente causa=sesion_sin_usuario_pendiente"
        )
        messages.error(request, "No hay usuario pendiente de validación.")
        return redirect("login_usuario")

    user = get_object_or_404(User, id=user_id)

    try:
        enviar_codigo_correo(user, tipo="correo", flujo="REENVIO")
        messages.success(request, "Te enviamos un nuevo código de validación.")
    except ReenvioCodigoEnCooldown as error:
        messages.info(
            request,
            f"Espera {error.segundos_restantes} segundos antes de solicitar otro código.",
        )
    except Exception:
        messages.error(
            request,
            "El servicio de correo no está disponible temporalmente. Intenta más tarde.",
        )

    return redirect("verificar_correo")


def login_usuario(request):
    if request.method == "POST":
        correo = (
            request.POST.get("correo", "") or
            request.POST.get("username", "") or
            request.POST.get("email", "")
        ).strip().lower()

        password = request.POST.get("password", "")
        remember = request.POST.get("remember_me")

        user = authenticate(request, username=correo, password=password)

        if user is None:
            messages.error(request, "Correo o contraseña incorrectos.")
            return redirect("login_usuario")

        if not user.is_active:
            request.session["usuario_pendiente_id"] = user.id

            try:
                enviar_codigo_correo(user, tipo="correo", flujo="REENVIO")
                messages.warning(
                    request,
                    "Debes validar tu correo. Te enviamos un nuevo código."
                )
            except ReenvioCodigoEnCooldown as error:
                messages.info(
                    request,
                    f"Debes validar tu correo. Espera {error.segundos_restantes} segundos para solicitar otro código.",
                )
            except Exception:
                messages.warning(
                    request,
                    "Tu cuenta está pendiente de validación y el servicio de correo no está disponible temporalmente."
                )

            return redirect("verificar_correo")

        perfil = PerfilUsuario.objects.filter(user=user).first()

        if not perfil or not perfil.activo:
            messages.error(request, "Usuario inactivo. Contacte al administrador.")
            return redirect("login_usuario")

        login(request, user)

        if not remember:
            request.session.set_expiry(0)

        request.session["empresa_id"] = perfil.empresa.id if perfil.empresa else None

        return redirect("inicio")

    return render(request, "login.html")


def logout_usuario(request):
    logout(request)
    return redirect("login_usuario")

@login_required(login_url="login_usuario")
def mi_empresa(request):
    empresa = obtener_empresa(request)

    if not empresa:
        messages.error(request, "No se encontró una empresa asociada a este usuario.")
        return redirect("inicio")

    perfil = PerfilUsuario.objects.filter(user=request.user).first()

    if request.method == "POST":
        empresa.nombre = request.POST.get("nombre", "").strip()
        empresa.rnc = request.POST.get("rnc", "").strip()
        empresa.direccion = request.POST.get("direccion", "").strip()
        empresa.telefono = request.POST.get("telefono", "").strip()
        empresa.ciudad = request.POST.get("ciudad", "").strip()
        empresa.correo = request.POST.get("correo", "").strip()
        empresa.firmante_predeterminado = request.POST.get(
            "firmante_predeterminado",
            "",
        ).strip()

        empresa.cargo_firmante_predeterminado = request.POST.get(
            "cargo_firmante_predeterminado",
            "",
        ).strip()
        empresa.numero_inicial_conduce = request.POST.get("numero_inicial_conduce", "0001").strip()

        if request.FILES.get("logo"):
            empresa.logo = request.FILES.get("logo")

        if request.FILES.get("firma_autorizada"):
            empresa.firma_autorizada = request.FILES.get("firma_autorizada")

        if request.FILES.get("sello_institucional"):
            empresa.sello_institucional = request.FILES.get("sello_institucional")

        # Permite retirar los recursos sin afectar el logo.
        if request.POST.get("eliminar_firma_autorizada") == "1":
            if empresa.firma_autorizada:
                empresa.firma_autorizada.delete(save=False)
            empresa.firma_autorizada = None

        if request.POST.get("eliminar_sello_institucional") == "1":
            if empresa.sello_institucional:
                empresa.sello_institucional.delete(save=False)
            empresa.sello_institucional = None

        empresa.modulo_conduces = request.POST.get("modulo_conduces") == "on"
        empresa.modulo_centros = request.POST.get("modulo_centros") == "on"
        empresa.modulo_menu = request.POST.get("modulo_menu") == "on"
        empresa.modulo_facturacion = request.POST.get("modulo_facturacion") == "on"
        empresa.modulo_reportes = request.POST.get("modulo_reportes") == "on"
        empresa.modulo_rutas = request.POST.get("modulo_rutas") == "on"
        empresa.modulo_nomina = request.POST.get("modulo_nomina") == "on"
        empresa.modulo_inventario = request.POST.get("modulo_inventario") == "on"

        empresa.save()

        messages.success(request, "Datos de la empresa actualizados correctamente.")
        return redirect("mi_empresa")

    usuarios = PerfilUsuario.objects.filter(
        empresa=perfil.empresa
    ).select_related("user") if perfil and perfil.empresa else []

    return render(request, "mi_empresa.html", {
        "empresa": empresa,
        "usuarios": usuarios,
        "perfil": perfil,
    })


@login_required(login_url="login_usuario")
def crear_usuario_empresa(request):
    empresa = obtener_empresa(request)
    perfil_actual = PerfilUsuario.objects.filter(user=request.user).first()

    if not perfil_actual or perfil_actual.rol != "admin_empresa":
        messages.error(request, "No tienes permisos para crear usuarios.")
        return redirect("mi_empresa")

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()
        correo = request.POST.get("correo", "").strip().lower()
        password = request.POST.get("password", "").strip()
        rol = request.POST.get("rol", "consulta").strip()

        if not nombre or not correo or not password:
            messages.error(request, "Debe completar nombre, correo y contraseña.")
            return redirect("mi_empresa")

        if User.objects.filter(username=correo).exists() or User.objects.filter(email=correo).exists():
            messages.error(request, "Ya existe un usuario con ese correo.")
            return redirect("mi_empresa")

        user = User.objects.create(
            username=correo,
            email=correo,
            first_name=nombre,
            last_name=apellido,
            password=make_password(password),
            is_active=True
        )

        PerfilUsuario.objects.create(
            user=user,
            empresa=perfil_actual.empresa,
            rol=rol,
            correo_validado=True,
            activo=True
        )

        messages.success(request, "Usuario creado correctamente.")
        return redirect("mi_empresa")

    return redirect("mi_empresa")
@login_required(login_url="login_usuario")
def cartas_administrativas(request):
    empresa = obtener_empresa(request)

    if not empresa:
        messages.error(request, "No se encontró una empresa asociada.")
        return redirect("inicio")

    return render(request, "cartas_administrativas.html", {
        "empresa": empresa
    })


@login_required(login_url="login_usuario")
def generar_carta_pdf(request):
    empresa = obtener_empresa(request)

    if request.method != "POST":
        return redirect("cartas_administrativas")

    destinatario = request.POST.get("destinatario", "").strip()
    institucion = request.POST.get("institucion", "").strip()
    asunto = request.POST.get("asunto", "").strip()
    contenido = request.POST.get("contenido", "").strip()
    firmante = request.POST.get("firmante", "").strip()
    cargo = request.POST.get("cargo", "").strip()
    ciudad = request.POST.get("ciudad", "").strip() or empresa.ciudad or ""
    fecha = timezone.localdate()

    if not destinatario or not asunto or not contenido:
        messages.error(request, "Debe completar destinatario, asunto y contenido.")
        return redirect("cartas_administrativas")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = 735

    # Logo solo para cartas administrativas
    if empresa.logo:
        try:
            with empresa.logo.storage.open(
                empresa.logo.name,
                "rb",
            ) as archivo_logo:
                logo = ImageReader(
                    BytesIO(archivo_logo.read())
                )
            pdf.drawImage(logo, 50, 705, width=75, height=75, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(width / 2, y, (empresa.nombre or "").upper())

    y -= 14
    pdf.setFont("Helvetica", 8)
    if empresa.direccion:
        pdf.drawCentredString(width / 2, y, empresa.direccion)

    y -= 11
    if ciudad:
        pdf.drawCentredString(width / 2, y, ciudad)

    y -= 11
    datos_contacto = []
    if empresa.correo:
        datos_contacto.append(f"Correo: {empresa.correo}")
    if empresa.telefono:
        datos_contacto.append(f"Teléfono: {empresa.telefono}")

    if datos_contacto:
        pdf.drawCentredString(width / 2, y, " | ".join(datos_contacto))

    y -= 11
    if empresa.rnc:
        pdf.drawCentredString(width / 2, y, f"RNC: {empresa.rnc}")

    y -= 45

    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(width - 55, y, f"{ciudad}, {fecha_larga_es(fecha)}")

    y -= 45

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, y, "Señores:")
    y -= 14

    pdf.setFont("Helvetica", 9)
    pdf.drawString(55, y, destinatario)
    y -= 14

    if institucion:
        pdf.drawString(55, y, institucion)
        y -= 14

    y -= 14

    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, y, f"Asunto: {asunto}")
    y -= 30

    pdf.setFont("Helvetica", 9)

    estilo = ParagraphStyle(
        name="CartaContenido",
        fontName="Helvetica",
        fontSize=9,
        leading=14,
        alignment=TA_LEFT,
    )

    contenido_html = contenido.replace("\n", "<br/>")
    parrafo = Paragraph(contenido_html, estilo)

    ancho_texto = width - 110
    alto_disponible = y - 150
    _, alto_parrafo = parrafo.wrap(ancho_texto, alto_disponible)

    parrafo.drawOn(pdf, 55, y - alto_parrafo)

    y = y - alto_parrafo - 55

    pdf.setFont("Helvetica", 9)
    pdf.drawString(55, y, "Atentamente,")

    y -= 55

    pdf.line(55, y, 250, y)

    y -= 13
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(55, y, firmante or empresa.nombre or "")

    y -= 12
    pdf.setFont("Helvetica", 9)
    pdf.drawString(55, y, cargo or "Representante autorizado")

    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="carta_administrativa.pdf"'
    return response

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
def calendario_escolar(request):
    empresa = obtener_empresa(request)

    dias = DiaNoDocencia.objects.filter(
        empresa=empresa
    ).order_by("fecha")

    return render(request, "calendario_escolar.html", {
        "dias": dias,
    })

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
def agregar_dia_no_docencia(request):
    empresa = obtener_empresa(request)

    if request.method == "POST":
        fecha = convertir_fecha(request.POST.get("fecha"))
        tipo = request.POST.get("tipo")
        motivo = request.POST.get("motivo")
        observacion = request.POST.get("observacion")

        if not fecha or not motivo:
            messages.error(request, "Debe completar la fecha y el motivo.")
            return redirect("agregar_dia_no_docencia")

        DiaNoDocencia.objects.create(
            empresa=empresa,
            fecha=fecha,
            tipo=tipo,
            motivo=motivo,
            observacion=observacion,
            activo=True
        )

        messages.success(request, "Día registrado correctamente.")
        return redirect("calendario_escolar")

    return render(request, "agregar_dia_no_docencia.html")

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
def editar_dia_no_docencia(request, dia_id):
    empresa = obtener_empresa(request)

    dia = get_object_or_404(
        DiaNoDocencia,
        id=dia_id,
        empresa=empresa
    )

    if request.method == "POST":
        fecha = convertir_fecha(request.POST.get("fecha"))
        tipo = request.POST.get("tipo")
        motivo = request.POST.get("motivo")
        observacion = request.POST.get("observacion")
        activo = request.POST.get("activo") == "on"

        if not fecha or not motivo:
            messages.error(request, "Debe completar la fecha y el motivo.")
            return redirect("editar_dia_no_docencia", dia_id=dia.id)

        dia.fecha = fecha
        dia.tipo = tipo
        dia.motivo = motivo
        dia.observacion = observacion
        dia.activo = activo
        dia.save()

        messages.success(request, "Día actualizado correctamente.")
        return redirect("calendario_escolar")

    return render(request, "editar_dia_no_docencia.html", {
        "dia": dia,
    })


# =====================================================
# PLANIFICACION DE MENU ESCOLAR (VERSIONADA)
# =====================================================

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
def planificacion_menu_escolar(request):
    empresa = obtener_empresa(request)
    calendarios = CalendarioEscolar.objects.filter(empresa=empresa).prefetch_related("dias")
    programas = ProgramaMenu.objects.filter(
        empresa=empresa
    ).prefetch_related(
        "versiones__items"
    )
    programas_asignables = ProgramaMenu.objects.filter(
        empresa=empresa,
        versiones__estado=VersionProgramaMenu.Estado.ACTIVA,
    ).distinct().order_by("nombre")

    for programa in programas:
        for version in programa.versiones.all():
            items_version = list(version.items.all())

            if programa.modalidad in (
                ProgramaMenu.Modalidad.REGULAR,
                ProgramaMenu.Modalidad.PREPARA,
            ):
                semanas_matriz = range(1, version.semanas_ciclo + 1)
                if programa.modalidad == ProgramaMenu.Modalidad.PREPARA:
                    dias = [
                        (5, "Sábado"),
                        (6, "Domingo"),
                    ]
                else:
                    # La matriz REGULAR conserva exactamente su preparación existente.
                    dias = [
                        (0, "Lunes"),
                        (1, "Martes"),
                        (2, "Miércoles"),
                        (3, "Jueves"),
                        (4, "Viernes"),
                    ]

                posiciones_requeridas = {
                    (semana, dia)
                    for semana in semanas_matriz
                    for dia, _nombre in dias
                }

                mapa_items = {
                    (item.semana, item.dia_semana): item
                    for item in items_version
                    if item.dia_semana in {numero for numero, _nombre in dias}
                }

                posiciones_configuradas = set(mapa_items.keys())

                version.total_posiciones_requeridas = len(
                    posiciones_requeridas
                )

                version.total_posiciones_configuradas = len(
                    posiciones_configuradas & posiciones_requeridas
                )

                version.posiciones_faltantes = (
                    version.total_posiciones_requeridas
                    - version.total_posiciones_configuradas
                )

                version.ciclo_completo = (
                    version.posiciones_faltantes == 0
                )

                version.matriz_ciclo = []
                version.matriz_dias = dias
                version.tiene_importacion_automatica = any(
                    item.observacion == "Importado automáticamente desde documento oficial."
                    for item in items_version
                )

                for semana in semanas_matriz:
                    fila = {
                        "semana": semana,
                        "dias": [],
                    }

                    for numero_dia, nombre_dia in dias:
                        fila["dias"].append({
                            "numero": numero_dia,
                            "nombre": nombre_dia,
                            "item": mapa_items.get(
                                (semana, numero_dia)
                            ),
                        })

                    version.matriz_ciclo.append(fila)

            else:
                version.total_posiciones_requeridas = None
                version.total_posiciones_configuradas = len(
                    items_version
                )
                version.posiciones_faltantes = None
                version.ciclo_completo = bool(items_version)
                version.matriz_ciclo = None
                version.matriz_dias = None
                version.ciclo_completo = version.items.exists()
    asignaciones = AsignacionProgramaCentro.objects.filter(
        centro__empresa=empresa,
        programa__empresa=empresa,
    ).select_related("centro", "programa")
    nombres_dias = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
    for asignacion in asignaciones:
        asignacion.dias_entrega_nombres = " · ".join(
            nombres_dias[dia] for dia in asignacion.dias_entrega if 0 <= dia < len(nombres_dias)
        )

        materializadas = ProgramacionMenuEscolar.objects.filter(
            empresa=empresa,
            asignacion=asignacion,
        ).order_by("fecha")

        asignacion.total_fechas_programadas = materializadas.count()
        primera_programada = materializadas.first()
        ultima_programada = materializadas.last()

        asignacion.programada_desde = (
            primera_programada.fecha if primera_programada else None
        )
        asignacion.programada_hasta = (
            ultima_programada.fecha if ultima_programada else None
        )

        ultima_actualizada = materializadas.order_by(
            "-actualizada_en", "-id"
        ).first()

        asignacion.calendario_programado = (
            ultima_actualizada.calendario if ultima_actualizada else None
        )
    programaciones = ProgramacionMenuEscolar.objects.filter(empresa=empresa).select_related(
        "centro", "programa", "version"
    )[:100]
    calendario_id = request.GET.get("calendario")
    calendario_revision = calendarios.filter(pk=calendario_id).first() if calendario_id else calendarios.first()
    dias_revision = DiaCalendarioEscolar.objects.none()
    resumen_calendario = None
    pagina_dias = None
    filtro_fecha = request.GET.get("fecha", "").strip()
    filtro_clasificacion = request.GET.get("clasificacion", "").strip()
    if calendario_revision:
        dias_revision = calendario_revision.dias.all()
        if filtro_fecha:
            fecha_buscada = convertir_fecha(filtro_fecha)
            dias_revision = dias_revision.filter(fecha=fecha_buscada) if fecha_buscada else dias_revision.none()
        if filtro_clasificacion:
            dias_revision = dias_revision.filter(clasificacion=filtro_clasificacion)
        resumen_calendario = {
            "oficiales": calendario_revision.dias_docencia_oficiales,
            "calculados": contar_docencia_regular(calendario_revision),
            "docencia": calendario_revision.dias.filter(clasificacion=DiaCalendarioEscolar.Clasificacion.DOCENCIA).count(),
            "no_lectivos": calendario_revision.dias.exclude(clasificacion=DiaCalendarioEscolar.Clasificacion.DOCENCIA).count(),
            "excepciones": calendario_revision.dias.exclude(origen="PREVISUALIZACION").count(),
        }
        resumen_calendario["diferencia"] = (
            resumen_calendario["calculados"] - resumen_calendario["oficiales"]
            if resumen_calendario["oficiales"] is not None else None
        )
        pagina_dias = Paginator(dias_revision, 31).get_page(request.GET.get("pagina"))
    analisis_actual = (
        AnalisisDocumentoCalendario.objects.filter(empresa=empresa, calendario=calendario_revision)
        .prefetch_related("totales_mensuales", "eventos")
        .first()
        if calendario_revision else None
    )
    return render(request, "planificacion_menu_escolar.html", {
        "empresa": empresa,
        "calendarios": calendarios,
        "programas": programas,
        "programas_asignables": programas_asignables,
        "asignaciones": asignaciones,
        "programaciones": programaciones,
        "centros": CentroEducativo.objects.filter(empresa=empresa).order_by("nombre"),
        "puede_gestionar": puede_gestionar_planificacion(request.user),
        "modalidades": ProgramaMenu.Modalidad.choices,
        "clasificaciones": DiaCalendarioEscolar.Clasificacion.choices,
        "calendario_revision": calendario_revision,
        "resumen_calendario": resumen_calendario,
        "pagina_dias": pagina_dias,
        "filtro_fecha": filtro_fecha,
        "filtro_clasificacion": filtro_clasificacion,
        "analisis_actual": analisis_actual,
    })


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def crear_calendario_escolar_planificacion(request):
    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    inicio = convertir_fecha(request.POST.get("inicio_docencia"))
    fin = convertir_fecha(request.POST.get("fin_docencia"))
    if not inicio or not fin or inicio > fin:
        messages.error(request, "Indique una vigencia valida para el calendario.")
        return redirect("planificacion_menu_escolar")
    try:
        with transaction.atomic():
            calendario = CalendarioEscolar(
                empresa=empresa,
                nombre=request.POST.get("nombre", "").strip(),
                anio_inicio=int(request.POST.get("anio_inicio")),
                anio_fin=int(request.POST.get("anio_fin")),
                inicio_docencia=inicio,
                fin_docencia=fin,
                dias_docencia_oficiales=(
                    int(request.POST.get("dias_docencia_oficiales"))
                    if request.POST.get("dias_docencia_oficiales") else None
                ),
                estado=CalendarioEscolar.Estado.EN_REVISION,
                documento_fuente=request.FILES.get("documento_fuente"),
            )
            calendario.full_clean()
            calendario.save()
            fechas_oficiales = {
                regla.fecha: regla
                for regla in FechaOficialCalendario.objects.filter(
                    anio_inicio=calendario.anio_inicio,
                    anio_fin=calendario.anio_fin,
                    activa=True,
                    fecha__range=(inicio, fin),
                )
            }
            fecha = inicio
            dias = []
            while fecha <= fin:
                regla = fechas_oficiales.get(fecha)
                if regla:
                    clasificacion = regla.clasificacion
                    motivo = regla.motivo
                    origen = "CATALOGO_OFICIAL"
                else:
                    clasificacion = (
                        DiaCalendarioEscolar.Clasificacion.DOCENCIA
                        if fecha.weekday() < 5
                        else DiaCalendarioEscolar.Clasificacion.NO_LECTIVO
                    )
                    motivo = ""
                    origen = "PREVISUALIZACION"
                dias.append(DiaCalendarioEscolar(
                    calendario=calendario,
                    fecha=fecha,
                    clasificacion=clasificacion,
                    motivo=motivo,
                    origen=origen,
                ))
                fecha += timedelta(days=1)
            DiaCalendarioEscolar.objects.bulk_create(dias)
        messages.success(request, "Calendario cargado como previsualizacion; revise las fechas antes de activarlo.")
    except (ValidationError, ValueError, TypeError) as error:
        messages.error(request, "; ".join(error.messages) if hasattr(error, "messages") else str(error))
    return redirect("planificacion_menu_escolar")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def subir_analizar_calendario(request):
    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    archivo = request.FILES.get("documento_fuente")
    if not archivo:
        messages.error(request, "Seleccione el PDF oficial que desea analizar.")
        return redirect("planificacion_menu_escolar")
    try:
        analisis = analizar_documento_calendario(
            empresa=empresa, usuario=request.user, archivo=archivo, request=request
        )
        if analisis.calendario_id:
            destino = f"{reverse('planificacion_menu_escolar')}?calendario={analisis.calendario_id}"
        else:
            destino = reverse("planificacion_menu_escolar")
        if analisis.estado == AnalisisDocumentoCalendario.Estado.DETECTADO:
            messages.success(request, "Documento analizado: calendario consistente y listo para confirmacion.")
        else:
            messages.warning(request, "Documento conservado y analizado parcialmente; revise advertencias y discrepancias.")
        return redirect(destino)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("planificacion_menu_escolar")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def reanalizar_calendario(request, calendario_id):
    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    calendario = get_object_or_404(CalendarioEscolar, pk=calendario_id, empresa=empresa)
    if not calendario.documento_fuente:
        messages.error(request, "El calendario no conserva un PDF fuente para reanalizar.")
        return redirect(f"{reverse('planificacion_menu_escolar')}?calendario={calendario.pk}")
    with calendario.documento_fuente.open("rb") as fuente:
        copia = ContentFile(fuente.read(), name=os.path.basename(calendario.documento_fuente.name))
    try:
        analisis = analizar_documento_calendario(
            empresa=empresa, usuario=request.user, archivo=copia,
            calendario=calendario, request=request,
        )
        if analisis.estado == AnalisisDocumentoCalendario.Estado.REQUIERE_REVISION:
            messages.warning(request, "Reanalisis completado con advertencias; no se sobrescribio informacion historica protegida.")
        else:
            messages.success(request, "Documento reanalizado y previsualizacion regenerada.")
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    return redirect(f"{reverse('planificacion_menu_escolar')}?calendario={calendario.pk}")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
def descargar_plantilla_calendario_oficial(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Fechas oficiales"
    ws.append(["fecha", "clasificacion", "motivo"])
    ws.append(["2027-04-13", "NO_LECTIVO", "Dia de la ADP"])
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="plantilla_fechas_calendario.xlsx"'
    wb.save(response)
    return response


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def cargar_fechas_calendario_oficial(request, calendario_id):
    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    calendario = get_object_or_404(CalendarioEscolar, pk=calendario_id, empresa=empresa)
    if calendario.estado in (CalendarioEscolar.Estado.ACTIVO, CalendarioEscolar.Estado.CERRADO):
        messages.error(request, "No puede cargar excepciones sobre un calendario activo o cerrado.")
        return redirect(f"{reverse('planificacion_menu_escolar')}?calendario={calendario.pk}")
    archivo = request.FILES.get("archivo")
    if not archivo:
        messages.error(request, "Seleccione el Excel de fechas oficiales.")
        return redirect(f"{reverse('planificacion_menu_escolar')}?calendario={calendario.pk}")
    clasificaciones_validas = {valor for valor, _ in DiaCalendarioEscolar.Clasificacion.choices}
    errores = []
    ajustes = []
    wb = load_workbook(archivo, data_only=True)
    for numero_fila, valores in enumerate(wb.active.iter_rows(min_row=2, values_only=True), start=2):
        fecha = convertir_fecha_excel(valores[0] if len(valores) > 0 else None)
        clasificacion = str(valores[1] or "").strip().upper() if len(valores) > 1 else ""
        motivo = str(valores[2] or "").strip() if len(valores) > 2 else ""
        if not fecha or clasificacion not in clasificaciones_validas or not motivo:
            errores.append(f"Fila {numero_fila}: fecha, clasificacion o motivo invalido.")
            continue
        if not calendario.inicio_docencia <= fecha <= calendario.fin_docencia:
            errores.append(f"Fila {numero_fila}: fecha fuera de la vigencia.")
            continue
        ajustes.append((fecha, clasificacion, motivo))
    if errores:
        messages.error(request, "No se aplicaron cambios. " + " ".join(errores[:5]))
        return redirect(f"{reverse('planificacion_menu_escolar')}?calendario={calendario.pk}")
    with transaction.atomic():
        for fecha, clasificacion, motivo in ajustes:
            dia = calendario.dias.select_for_update().get(fecha=fecha)
            anterior = {"clasificacion": dia.clasificacion, "motivo": dia.motivo}
            dia.clasificacion = clasificacion
            dia.motivo = motivo
            dia.origen = "CARGA_OFICIAL_EXCEL"
            dia.ajustado_por = request.user
            dia.save(update_fields=("clasificacion", "motivo", "origen", "ajustado_por", "ajustado_en"))
            registrar_evento(
                empresa=empresa, accion="EDITAR", modulo="planificacion_menu",
                descripcion=f"Fecha oficial {fecha} aplicada desde Excel: {motivo}.",
                usuario=request.user, objeto=dia, request=request,
                datos_anteriores=anterior,
                datos_nuevos={"clasificacion": clasificacion, "motivo": motivo, "origen": "CARGA_OFICIAL_EXCEL"},
            )
    messages.success(request, f"Se aplicaron {len(ajustes)} fechas oficiales a la previsualizacion.")
    return redirect(f"{reverse('planificacion_menu_escolar')}?calendario={calendario.pk}")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def clasificar_dia_calendario(request, dia_id):
    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    dia = get_object_or_404(DiaCalendarioEscolar, pk=dia_id, calendario__empresa=empresa)
    if dia.calendario.estado in (CalendarioEscolar.Estado.ACTIVO, CalendarioEscolar.Estado.CERRADO):
        messages.error(request, "No puede editar normalmente un calendario activo o cerrado.")
        return redirect("planificacion_menu_escolar")
    anterior = dia.clasificacion
    nueva_clasificacion = request.POST.get("clasificacion", DiaCalendarioEscolar.Clasificacion.REQUIERE_REVISION)
    motivo = request.POST.get("motivo", "").strip()
    if nueva_clasificacion != DiaCalendarioEscolar.Clasificacion.DOCENCIA and not motivo:
        messages.error(request, "Debe registrar el motivo de una fecha no lectiva o excepcional.")
        return redirect(f"{reverse('planificacion_menu_escolar')}?calendario={dia.calendario_id}&fecha={dia.fecha}")
    dia.clasificacion = nueva_clasificacion
    dia.motivo = motivo
    dia.origen = "AJUSTE_MANUAL"
    dia.ajustado_por = request.user
    dia.full_clean()
    dia.save()
    registrar_evento(
        empresa=empresa, accion="EDITAR", modulo="planificacion_menu",
        descripcion=f"Fecha {dia.fecha} reclasificada de {anterior} a {dia.clasificacion}.",
        usuario=request.user, objeto=dia, request=request,
        datos_anteriores={"clasificacion": anterior}, datos_nuevos={"clasificacion": dia.clasificacion},
    )
    messages.success(request, "Fecha actualizada en la previsualizacion.")
    return redirect("planificacion_menu_escolar")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def activar_calendario_escolar_planificacion(request, calendario_id):
    empresa = obtener_empresa(request)
    calendario = get_object_or_404(CalendarioEscolar, pk=calendario_id, empresa=empresa)
    try:
        activar_calendario(
            calendario,
            usuario=request.user,
            request=request,
            forzar=request.POST.get("forzar") == "on",
            justificacion=request.POST.get("justificacion", ""),
        )
        messages.success(request, f"Calendario activado: {contar_docencia_regular(calendario)} dias regulares.")
    except (ValidationError, PermissionDenied) as error:
        if isinstance(error, PermissionDenied):
            raise
        messages.error(request, "; ".join(error.messages))
    return redirect("planificacion_menu_escolar")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def crear_programa_menu(request):
    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    programa = ProgramaMenu(
        empresa=empresa,
        codigo=request.POST.get("codigo", "").strip(),
        nombre=request.POST.get("nombre", "").strip(),
        modalidad=request.POST.get("modalidad", ProgramaMenu.Modalidad.REGULAR),
    )
    try:
        programa.full_clean()
        programa.save()
        messages.success(request, "Programa de menu creado.")
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    return redirect("planificacion_menu_escolar")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def crear_version_programa_menu(request, programa_id):
    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    programa = get_object_or_404(ProgramaMenu, pk=programa_id, empresa=empresa)
    try:
        version = VersionProgramaMenu(
            programa=programa,
            nombre=request.POST.get("nombre", "").strip(),
            vigente_desde=convertir_fecha(request.POST.get("vigente_desde")),
            vigente_hasta=convertir_fecha(request.POST.get("vigente_hasta")),
            semanas_ciclo=int(request.POST.get("semanas_ciclo") or 5),
            fecha_ancla_ciclo=convertir_fecha(request.POST.get("fecha_ancla_ciclo")),
            modo_inicio_ciclo=request.POST.get("modo_inicio_ciclo", VersionProgramaMenu.InicioCiclo.REINICIAR),
            semana_inicial=int(request.POST.get("semana_inicial") or 1),
            estado=VersionProgramaMenu.Estado.BORRADOR,
            documento_fuente=request.FILES.get("documento_fuente"),
            creado_por=request.user,
        )
        version.full_clean()
        version.save()
        messages.success(request, "Version creada en borrador.")
        if version.documento_fuente:
            return redirect("analizar_version_programa_menu", version_id=version.id)
    except (ValidationError, ValueError, TypeError) as error:
        messages.error(request, "; ".join(error.messages) if hasattr(error, "messages") else str(error))
    return redirect("planificacion_menu_escolar")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
def analizar_version_programa_menu(request, version_id):
    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    version = get_object_or_404(VersionProgramaMenu, pk=version_id, programa__empresa=empresa)
    if not version.documento_fuente:
        messages.error(request, "Esta versión no tiene un documento oficial cargado.")
        return redirect("planificacion_menu_escolar")
    try:
        from .menu_document_parser import LocalMenuPDFProvider
        with version.documento_fuente.open("rb") as archivo:
            resultado = LocalMenuPDFProvider().extract(archivo, modalidad=version.programa.modalidad)
    except Exception:
        logger_menu_documento.exception("Error analizando documento de menú version_id=%s", version.id)
        messages.error(request, "No fue posible analizar el documento oficial del menú.")
        return redirect("planificacion_menu_escolar")
    dias = {0:"Lunes",1:"Martes",2:"Miércoles",3:"Jueves",4:"Viernes",5:"Sábado",6:"Domingo"}
    dias_modalidad = [5, 6] if version.programa.modalidad == ProgramaMenu.Modalidad.PREPARA else [0, 1, 2, 3, 4]
    total_esperado = 10 if version.programa.modalidad == ProgramaMenu.Modalidad.PREPARA else 25
    encontrados = {(item.semana, item.dia_semana): item for item in resultado.items}
    matriz = []
    for semana in range(1, resultado.semanas_ciclo + 1):
        fila = {"semana": semana, "items": []}
        for dia in dias_modalidad:
            item = encontrados.get((semana, dia))
            fila["items"].append({"dia": dias[dia], "producto": item.producto if item else "", "detectado": bool(item)})
        matriz.append(fila)
    contexto = {
        "version_menu": version,
        "resultado": resultado,
        "matriz": matriz,
        "dias_columnas": [dias[dia] for dia in dias_modalidad],
        "total_esperado": total_esperado,
        "fecha_uso_sugerida": version.fecha_uso_desde or resultado.vigente_desde,
    }
    return render(request, "menu_analisis_documento.html", contexto)


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def aplicar_documento_programa_menu(request, version_id):
    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    version = get_object_or_404(VersionProgramaMenu, pk=version_id, programa__empresa=empresa)
    if version.estado != VersionProgramaMenu.Estado.BORRADOR:
        messages.error(request, "Solo puede importar el documento sobre una versión en borrador.")
        return redirect("planificacion_menu_escolar")
    if not version.documento_fuente:
        messages.error(request, "Esta versión no tiene un documento oficial cargado.")
        return redirect("planificacion_menu_escolar")
    fecha_uso = convertir_fecha(request.POST.get("fecha_uso_desde"))
    if not fecha_uso:
        messages.error(request, "Seleccione la fecha desde la cual SASTRE utilizará este menú.")
        return redirect("analizar_version_programa_menu", version_id=version.id)
    try:
        from .menu_document_parser import LocalMenuPDFProvider
        with version.documento_fuente.open("rb") as archivo:
            resultado = LocalMenuPDFProvider().extract(archivo, modalidad=version.programa.modalidad)
        total_esperado = 10 if version.programa.modalidad == ProgramaMenu.Modalidad.PREPARA else 25
        if not resultado.completo or len(resultado.items) != total_esperado or resultado.advertencias:
            messages.error(request, f"El documento no contiene una matriz {version.programa.get_modalidad_display()} completa y segura de {total_esperado} posiciones. Revise el análisis antes de aplicarlo.")
            return redirect("analizar_version_programa_menu", version_id=version.id)
        vigencia_oficial = resultado.vigente_desde or version.vigente_desde
        if fecha_uso < vigencia_oficial:
            messages.error(request, "La fecha de uso en SASTRE no puede ser anterior a la vigencia oficial detectada.")
            return redirect("analizar_version_programa_menu", version_id=version.id)
        if version.vigente_hasta and fecha_uso > version.vigente_hasta:
            messages.error(request, "La fecha de uso en SASTRE no puede ser posterior al fin de vigencia de esta versión.")
            return redirect("analizar_version_programa_menu", version_id=version.id)
        with transaction.atomic():
            version.vigente_desde = vigencia_oficial
            version.fecha_uso_desde = fecha_uso
            version.semanas_ciclo = 5
            version.full_clean()
            version.save(update_fields=("vigente_desde", "fecha_uso_desde", "semanas_ciclo"))
            posiciones_detectadas = {(detectado.semana, detectado.dia_semana) for detectado in resultado.items}
            for existente in ItemCicloMenu.objects.filter(version=version):
                if (existente.semana, existente.dia_semana) not in posiciones_detectadas:
                    existente.delete()
            for detectado in resultado.items:
                item, creado = ItemCicloMenu.objects.update_or_create(version=version, semana=detectado.semana, dia_semana=detectado.dia_semana, defaults={"producto": detectado.producto, "es_suministrado": True, "observacion": "Importado automáticamente desde documento oficial."})
                item.full_clean()
                item.save()
            registrar_evento(
                empresa=empresa,
                accion="CREAR",
                modulo="planificacion_menu",
                descripcion=f"Menú oficial aplicado a la versión {version.nombre}: {total_esperado} posiciones.",
                usuario=request.user,
                objeto=version,
                request=request,
                datos_nuevos={
                    "version_id": version.id,
                    "documento": os.path.basename(version.documento_fuente.name),
                    "posiciones": total_esperado,
                    "fecha_uso_desde": fecha_uso.isoformat(),
                },
            )
        messages.success(request, f"Menú oficial aplicado correctamente: {total_esperado} de {total_esperado} posiciones de panadería fueron configuradas.")
        return redirect("planificacion_menu_escolar")
    except (ValidationError, ValueError, TypeError) as error:
        messages.error(request, "; ".join(error.messages) if hasattr(error, "messages") else str(error))
    except Exception:
        logger_menu_documento.exception("Error aplicando documento de menú version_id=%s", version.id)
        messages.error(request, "No fue posible aplicar el documento oficial del menú.")
    return redirect("analizar_version_programa_menu", version_id=version.id)


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def guardar_item_ciclo_menu(request, version_id):
    empresa = obtener_empresa(request)

    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied

    version = get_object_or_404(
        VersionProgramaMenu,
        pk=version_id,
        programa__empresa=empresa,
    )

    if version.estado != VersionProgramaMenu.Estado.BORRADOR:
        messages.error(
            request,
            "Solo puede editar posiciones de una versión en borrador."
        )
        return redirect("planificacion_menu_escolar")

    try:
        semana = int(request.POST.get("semana"))
        dia_semana = int(request.POST.get("dia_semana"))
        producto = request.POST.get("producto", "").strip()
        es_suministrado = request.POST.get("es_suministrado") == "on"
        observacion = request.POST.get("observacion", "").strip()

        item_existente = ItemCicloMenu.objects.filter(
            version=version,
            semana=semana,
            dia_semana=dia_semana,
        ).first()

        if item_existente:
            item_existente.producto = producto
            item_existente.es_suministrado = es_suministrado
            item_existente.observacion = observacion

            item_existente.full_clean(
                exclude=["version", "semana", "dia_semana"]
            )
            item_existente.save(
                update_fields=(
                    "producto",
                    "es_suministrado",
                    "observacion",
                )
            )

            messages.success(
                request,
                "Posición del menú actualizada correctamente."
            )

        else:
            item = ItemCicloMenu(
                version=version,
                semana=semana,
                dia_semana=dia_semana,
                producto=producto,
                es_suministrado=es_suministrado,
                observacion=observacion,
            )

            item.full_clean()
            item.save()

            messages.success(
                request,
                "Posición del menú agregada correctamente."
            )

    except (ValidationError, ValueError, TypeError) as error:
        messages.error(
            request,
            "; ".join(error.messages)
            if hasattr(error, "messages")
            else str(error)
        )

    return redirect("planificacion_menu_escolar")

@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def activar_version_programa_menu(request, version_id):
    empresa = obtener_empresa(request)

    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied

    version = get_object_or_404(
        VersionProgramaMenu,
        pk=version_id,
        programa__empresa=empresa,
    )

    if version.estado != VersionProgramaMenu.Estado.BORRADOR:
        messages.error(
            request,
            "Solo puede activar una versión que se encuentre en borrador."
        )
        return redirect("planificacion_menu_escolar")

    if version.programa.modalidad in (
        ProgramaMenu.Modalidad.REGULAR,
        ProgramaMenu.Modalidad.PREPARA,
    ):
        if not version.fecha_uso_desde:
            messages.error(
                request,
                "Indique desde qué fecha esta versión se utilizará operativamente antes de activarla."
            )
            return redirect("planificacion_menu_escolar")

        if version.semanas_ciclo != 5:
            messages.error(
                request,
                "La versión debe tener exactamente 5 semanas de ciclo antes de activarla."
            )
            return redirect("planificacion_menu_escolar")

        if version.programa.modalidad == ProgramaMenu.Modalidad.PREPARA:
            dias_requeridos = {
                5: "sábado",
                6: "domingo",
            }
        else:
            dias_requeridos = {
                0: "lunes",
                1: "martes",
                2: "miércoles",
                3: "jueves",
                4: "viernes",
            }

        posiciones_existentes = set(
            version.items.filter(
                semana__range=(1, 5),
                dia_semana__in=dias_requeridos.keys(),
            ).values_list("semana", "dia_semana")
        )

        posiciones_requeridas = {
            (semana, dia)
            for semana in range(1, 6)
            for dia in dias_requeridos
        }

        posiciones_faltantes = sorted(
            posiciones_requeridas - posiciones_existentes
        )
        total_requerido = len(posiciones_requeridas)
        total_items = version.items.count()

        if posiciones_faltantes or total_items != total_requerido:
            total_configurado = len(posiciones_requeridas & posiciones_existentes)

            faltantes_texto = [
                f"Semana {semana} · {dias_requeridos[dia]}"
                for semana, dia in posiciones_faltantes
            ]

            detalle_faltantes = ""
            if faltantes_texto:
                vista_faltantes = ", ".join(faltantes_texto[:10])
                if len(faltantes_texto) > 10:
                    vista_faltantes += (
                        f" y {len(faltantes_texto) - 10} posiciones más"
                    )
                detalle_faltantes = f" Faltan: {vista_faltantes}."

            detalle_extra = ""
            if total_items > total_requerido:
                detalle_extra = (
                    f" Además existen {total_items - total_requerido} "
                    "posiciones fuera de la matriz requerida."
                )

            messages.error(
                request,
                (
                    "No se puede activar esta versión. "
                    f"Hay {total_configurado} de {total_requerido} "
                    "posiciones válidas configuradas."
                    f"{detalle_faltantes}{detalle_extra}"
                ),
            )
            return redirect("planificacion_menu_escolar")

    elif not version.items.exists():
        messages.error(
            request,
            "La versión no contiene posiciones de menú configuradas."
        )
        return redirect("planificacion_menu_escolar")

    inicio_nuevo = version.fecha_uso_desde or version.vigente_desde
    fin_nuevo = version.vigente_hasta
    versiones_activas = VersionProgramaMenu.objects.filter(
        programa=version.programa,
        estado=VersionProgramaMenu.Estado.ACTIVA,
    ).exclude(pk=version.pk)
    superpuestas = []
    for activa in versiones_activas:
        inicio_activo = activa.fecha_uso_desde or activa.vigente_desde
        if (fin_nuevo is None or inicio_activo <= fin_nuevo) and (
            activa.vigente_hasta is None or inicio_nuevo <= activa.vigente_hasta
        ):
            superpuestas.append(activa.nombre)
    if superpuestas:
        messages.error(
            request,
            "No se puede activar esta versión porque su período operativo se superpone con "
            f"una versión activa del mismo programa: {', '.join(superpuestas)}. "
            "Cierre o revise primero la vigencia de la versión anterior.",
        )
        return redirect("planificacion_menu_escolar")

    version.estado = VersionProgramaMenu.Estado.ACTIVA
    version.save(update_fields=("estado",))

    messages.success(
        request,
        "Versión de menú activada correctamente."
    )

    return redirect("planificacion_menu_escolar")
@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def eliminar_version_programa_menu(request, version_id):
    from django.db.models.deletion import ProtectedError

    empresa = obtener_empresa(request)

    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied

    version = get_object_or_404(
        VersionProgramaMenu,
        pk=version_id,
        programa__empresa=empresa,
    )

    if version.estado != VersionProgramaMenu.Estado.BORRADOR:
        messages.error(
            request,
            "Solo se pueden eliminar versiones que se encuentren en borrador."
        )
        return redirect("planificacion_menu_escolar")

    try:
        with transaction.atomic():
            version.items.all().delete()
            version.delete()
    except ProtectedError:
        messages.error(
            request,
            "Esta versión no puede eliminarse porque posee información histórica u operativa relacionada."
        )
        return redirect("planificacion_menu_escolar")

    messages.success(
        request,
        "Versión eliminada correctamente."
    )
    return redirect("planificacion_menu_escolar")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def asignar_programa_centro(request):
    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    try:
        centro, programa, dias, vigente_desde, vigente_hasta = _datos_asignacion_desde_post(request, empresa)
        asignacion = AsignacionProgramaCentro(
            centro=centro, programa=programa, modalidad=programa.modalidad,
            dias_entrega=dias,
            vigente_desde=vigente_desde,
            vigente_hasta=vigente_hasta,
            creado_por=request.user,
        )
        asignacion.full_clean()
        asignacion.save()
        registrar_evento(
            empresa=empresa, accion="CREAR", modulo="planificacion_menu",
            descripcion=f"Asignación de menú creada para {centro}.", usuario=request.user,
            objeto=asignacion, request=request,
            datos_nuevos={"centro_id": centro.pk, "programa_id": programa.pk, "dias_entrega": dias,
                          "vigente_desde": vigente_desde.isoformat(),
                          "vigente_hasta": vigente_hasta.isoformat() if vigente_hasta else None},
        )
        messages.success(request, "Programación de entregas asignada al centro.")
    except (ValidationError, ValueError, TypeError) as error:
        messages.error(request, "; ".join(error.messages) if hasattr(error, "messages") else str(error))
    return redirect("planificacion_menu_escolar")


def _datos_asignacion_desde_post(request, empresa):
    centro = get_object_or_404(CentroEducativo, pk=request.POST.get("centro_id"), empresa=empresa)
    programa = get_object_or_404(ProgramaMenu, pk=request.POST.get("programa_id"), empresa=empresa)
    if not programa.versiones.filter(estado=VersionProgramaMenu.Estado.ACTIVA).exists():
        raise ValidationError("El programa seleccionado no tiene ninguna versión activa.")
    dias = sorted({int(valor) for valor in request.POST.getlist("dias_entrega")})
    if not dias:
        raise ValidationError("Seleccione al menos un día de entrega.")
    if any(dia < 0 or dia > 6 for dia in dias):
        raise ValidationError("Los días de entrega deben estar entre lunes y domingo.")
    vigente_desde = convertir_fecha(request.POST.get("vigente_desde"))
    vigente_hasta = convertir_fecha(request.POST.get("vigente_hasta"))
    if not vigente_desde:
        raise ValidationError("La fecha inicial de vigencia es obligatoria.")
    if vigente_hasta and vigente_hasta < vigente_desde:
        raise ValidationError("La vigencia final no puede preceder a la inicial.")
    return centro, programa, dias, vigente_desde, vigente_hasta


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
def editar_asignacion_programa_centro(request, asignacion_id):
    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    asignacion = get_object_or_404(
        AsignacionProgramaCentro.objects.select_related("centro", "programa"),
        pk=asignacion_id, centro__empresa=empresa, programa__empresa=empresa,
    )
    if request.method == "POST":
        try:
            centro, programa, dias, vigente_desde, vigente_hasta = _datos_asignacion_desde_post(request, empresa)
            anteriores = {
                "centro_id": asignacion.centro_id, "programa_id": asignacion.programa_id,
                "dias_entrega": asignacion.dias_entrega, "vigente_desde": asignacion.vigente_desde.isoformat(),
                "vigente_hasta": asignacion.vigente_hasta.isoformat() if asignacion.vigente_hasta else None,
            }
            asignacion.centro = centro
            asignacion.programa = programa
            asignacion.modalidad = programa.modalidad
            asignacion.dias_entrega = dias
            asignacion.vigente_desde = vigente_desde
            asignacion.vigente_hasta = vigente_hasta
            asignacion.full_clean()
            asignacion.save()
            registrar_evento(
                empresa=empresa, accion="EDITAR", modulo="planificacion_menu",
                descripcion=f"Asignación de menú {asignacion.pk} actualizada.", usuario=request.user,
                objeto=asignacion, request=request, datos_anteriores=anteriores,
                datos_nuevos={"centro_id": centro.pk, "programa_id": programa.pk, "dias_entrega": dias,
                              "vigente_desde": vigente_desde.isoformat(),
                              "vigente_hasta": vigente_hasta.isoformat() if vigente_hasta else None},
            )
            messages.success(request, "Asignación actualizada correctamente.")
            return redirect("planificacion_menu_escolar")
        except (ValidationError, ValueError, TypeError) as error:
            messages.error(request, "; ".join(error.messages) if hasattr(error, "messages") else str(error))
    return render(request, "editar_asignacion_programa_centro.html", {
        "asignacion": asignacion,
        "centros": CentroEducativo.objects.filter(empresa=empresa).order_by("nombre"),
        "programas_asignables": ProgramaMenu.objects.filter(
            empresa=empresa, versiones__estado=VersionProgramaMenu.Estado.ACTIVA,
        ).distinct().order_by("nombre"),
        "dias_semana": ((0, "Lun"), (1, "Mar"), (2, "Mié"), (3, "Jue"),
                         (4, "Vie"), (5, "Sáb"), (6, "Dom")),
    })


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def eliminar_asignacion_programa_centro(request, asignacion_id):
    from django.db.models.deletion import ProtectedError

    empresa = obtener_empresa(request)
    if not puede_gestionar_planificacion(request.user):
        raise PermissionDenied
    asignacion = get_object_or_404(
        AsignacionProgramaCentro.objects.select_related("centro", "programa"),
        pk=asignacion_id, centro__empresa=empresa, programa__empresa=empresa,
    )
    referencia = f"{asignacion.centro} · {asignacion.programa}"
    try:
        with transaction.atomic():
            registrar_evento(
                empresa=empresa, accion="OTRO", modulo="planificacion_menu",
                descripcion=f"Asignación de menú eliminada: {referencia}.", usuario=request.user,
                objeto=asignacion, request=request,
                datos_anteriores={"asignacion_id": asignacion.pk, "centro_id": asignacion.centro_id,
                                  "programa_id": asignacion.programa_id,
                                  "dias_entrega": asignacion.dias_entrega},
            )
            asignacion.delete()
    except ProtectedError:
        messages.error(
            request,
            "Esta asignación no puede eliminarse porque posee programación histórica. "
            "El historial y sus snapshots se conservaron sin cambios.",
        )
        return redirect("planificacion_menu_escolar")
    messages.success(request, "Asignación eliminada correctamente.")
    return redirect("planificacion_menu_escolar")



@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
@require_POST
def generar_programacion_menu(request, asignacion_id, calendario_id):
    empresa = obtener_empresa(request)

    asignacion = get_object_or_404(
        AsignacionProgramaCentro,
        pk=asignacion_id,
        centro__empresa=empresa,
        programa__empresa=empresa,
    )

    calendario = get_object_or_404(
        CalendarioEscolar,
        pk=calendario_id,
        empresa=empresa,
    )

    es_actualizacion = request.POST.get("actualizar_programacion") == "1"

    fecha_inicio = convertir_fecha(request.POST.get("fecha_inicio"))
    fecha_fin = convertir_fecha(request.POST.get("fecha_fin"))

    if es_actualizacion:
        existentes = ProgramacionMenuEscolar.objects.filter(
            empresa=empresa,
            asignacion=asignacion,
            calendario=calendario,
        ).order_by("fecha")

        primera = existentes.first()
        ultima = existentes.last()

        if not primera or not ultima:
            messages.error(
                request,
                "No existe una programación materializada que pueda actualizarse."
            )
            return redirect("planificacion_menu_escolar")

        fecha_inicio = primera.fecha
        fecha_fin = ultima.fecha

    try:
        resultados = materializar_programacion(
            asignacion,
            calendario,
            usuario=request.user,
            request=request,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )

        if es_actualizacion:
            messages.success(
                request,
                f"Programación actualizada correctamente: {len(resultados)} fechas revisadas."
            )
        else:
            messages.success(
                request,
                f"Programación generada correctamente: {len(resultados)} fechas."
            )

    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))

    return redirect("planificacion_menu_escolar")


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
def exportar_programacion_excel(request):
    empresa = obtener_empresa(request)

    filas = ProgramacionMenuEscolar.objects.filter(
        empresa=empresa
    ).select_related(
        "centro", "programa", "version"
    ).order_by(
        "fecha", "centro__nombre", "centro_id"
    )

    fecha_inicio = convertir_fecha(request.GET.get("fecha_inicio"))
    fecha_fin = convertir_fecha(request.GET.get("fecha_fin"))
    modalidad = request.GET.get("modalidad", "").strip()

    if fecha_inicio:
        filas = filas.filter(fecha__gte=fecha_inicio)

    if fecha_fin:
        filas = filas.filter(fecha__lte=fecha_fin)

    if modalidad:
        filas = filas.filter(modalidad_snapshot=modalidad)

    primera = filas.first()
    ultima = filas.order_by("-fecha").first()

    periodo_desde = fecha_inicio or (primera.fecha if primera else None)
    periodo_hasta = fecha_fin or (ultima.fecha if ultima else None)

    generado_en = timezone.localtime()
    generado_por = (
        request.user.get_full_name().strip()
        or request.user.get_username()
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Programación menú"
    ws.sheet_view.showGridLines = False

    # --------------------------------------------------------
    # Logo
    # --------------------------------------------------------
    if empresa.logo:
        try:
            with empresa.logo.storage.open(
                empresa.logo.name,
                "rb",
            ) as archivo_logo:
                logo_buffer = BytesIO(
                    archivo_logo.read()
                )

            logo = XLImage(
                logo_buffer
            )

            # Conserva una referencia al stream hasta
            # finalizar la construcción del workbook.
            logo._sastre_buffer = logo_buffer

            proporcion = (
                logo.width / logo.height
                if logo.height else 2
            )

            logo.height = 55
            logo.width = 55 * proporcion

            ws.add_image(
                logo,
                "A1",
            )
        except Exception:
            logger_menu_documento.exception(
                "No fue posible incorporar logo al Excel de programación."
            )

    # --------------------------------------------------------
    # Identidad empresarial
    # --------------------------------------------------------
    ws.merge_cells("C1:J1")
    ws["C1"] = empresa.nombre
    ws["C1"].font = Font(size=18, bold=True)
    ws["C1"].alignment = Alignment(vertical="center")

    ws.merge_cells("C2:J2")
    ws["C2"] = (
        f"RNC: {empresa.rnc or '-'}"
        f"  |  Tel.: {empresa.telefono or '-'}"
        f"  |  Correo: {empresa.correo or '-'}"
    )
    ws["C2"].font = Font(size=9)

    ws.merge_cells("C3:J3")
    direccion_empresa = " · ".join(
        dato for dato in [
            empresa.direccion,
            empresa.ciudad,
        ] if dato
    )
    ws["C3"] = direccion_empresa or "Dirección no registrada"
    ws["C3"].font = Font(size=9)

    ws.merge_cells("A5:J5")
    ws["A5"] = "PROGRAMACIÓN DE MENÚ ESCOLAR"
    ws["A5"].font = Font(size=16, bold=True)
    ws["A5"].alignment = Alignment(horizontal="center")

    periodo_texto = "Todos los registros"
    if periodo_desde or periodo_hasta:
        periodo_texto = (
            f"{periodo_desde.strftime('%d/%m/%Y') if periodo_desde else 'Inicio'}"
            f" – "
            f"{periodo_hasta.strftime('%d/%m/%Y') if periodo_hasta else 'Actualidad'}"
        )

    ws.merge_cells("A6:E6")
    ws["A6"] = f"Período: {periodo_texto}"
    ws["A6"].font = Font(size=9, bold=True)

    ws.merge_cells("F6:J6")
    ws["F6"] = f"Generado: {generado_en:%d/%m/%Y %H:%M}"
    ws["F6"].font = Font(size=9)
    ws["F6"].alignment = Alignment(horizontal="right")

    ws.merge_cells("A7:J7")
    ws["A7"] = f"Generado por: {generado_por}"
    ws["A7"].font = Font(size=9)

    encabezados = [
        "Fecha",
        "Día",
        "Código centro",
        "Centro educativo",
        "Semana",
        "Producto",
        "Programa",
        "Versión",
        "Modalidad",
        "Estado",
    ]

    fila_encabezado = 9

    for columna, valor in enumerate(encabezados, start=1):
        celda = ws.cell(row=fila_encabezado, column=columna, value=valor)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F4E78")
        celda.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )

    borde = Border(
        left=Side(style="thin", color="D9E2F3"),
        right=Side(style="thin", color="D9E2F3"),
        top=Side(style="thin", color="D9E2F3"),
        bottom=Side(style="thin", color="D9E2F3"),
    )

    dias = (
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    )

    fila_actual = fila_encabezado + 1

    for fila in filas:
        codigo_centro = (
            getattr(fila.centro, "codigo", "")
            or getattr(fila.centro, "codigo_centro", "")
            or ""
        )

        codigo_centro = str(codigo_centro).strip()

        if codigo_centro.isdigit():
            codigo_centro = codigo_centro.zfill(5)

        valores = [
            fila.fecha,
            dias[fila.dia_semana],
            codigo_centro,
            fila.centro.nombre,
            fila.semana_ciclo,
            fila.producto or "-",
            fila.programa_snapshot,
            fila.version_snapshot,
            fila.modalidad_snapshot,
            fila.get_estado_display(),
        ]

        for columna, valor in enumerate(valores, start=1):
            celda = ws.cell(
                row=fila_actual,
                column=columna,
                value=valor,
            )
            celda.border = borde
            celda.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

        ws.cell(
            row=fila_actual,
            column=1
        ).number_format = "dd/mm/yyyy"

        # Código del centro como texto para preservar 00154, 00025, etc.
        ws.cell(
            row=fila_actual,
            column=3
        ).number_format = "@"

        # Color visual por tipo de día.
        #
        # Prioridad:
        # 1. SIN_DOCENCIA real
        # 2. Sábado
        # 3. Domingo
        #
        # Esto es únicamente presentación del reporte.
        color_fila = None

        if fila.estado == ProgramacionMenuEscolar.Estado.SIN_DOCENCIA:
            color_fila = "FDE2E2"
        elif fila.fecha.weekday() == 5:
            color_fila = "EAF4FF"
        elif fila.fecha.weekday() == 6:
            color_fila = "FFF4CC"

        if color_fila:
            for columna in range(1, 11):
                ws.cell(
                    row=fila_actual,
                    column=columna
                ).fill = PatternFill(
                    "solid",
                    fgColor=color_fila,
                )

        fila_actual += 1

    anchos = {
        "A": 13,
        "B": 13,
        "C": 16,
        "D": 34,
        "E": 10,
        "F": 30,
        "G": 22,
        "H": 20,
        "I": 14,
        "J": 18,
    }

    for columna, ancho in anchos.items():
        ws.column_dimensions[columna].width = ancho

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[5].height = 26
    ws.row_dimensions[fila_encabezado].height = 30

    ultima_fila = max(fila_actual - 1, fila_encabezado)

    ws.auto_filter.ref = f"A{fila_encabezado}:J{ultima_fila}"
    ws.freeze_panes = f"A{fila_encabezado + 1}"

    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    ws.print_title_rows = f"1:{fila_encabezado}"
    ws.print_area = f"A1:J{ultima_fila}"

    ws.oddFooter.center.text = (
        "Generado por SASTRE ERP"
    )
    ws.oddFooter.right.text = (
        "Página &[Page] de &[Pages]"
    )

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = (
        'attachment; filename="programacion_menu_escolar.xlsx"'
    )

    wb.save(response)
    return response


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_menu")
def exportar_programacion_pdf(request):
    empresa = obtener_empresa(request)

    filas = list(
        ProgramacionMenuEscolar.objects.filter(
            empresa=empresa
        ).select_related(
            "centro", "programa", "version"
        ).order_by(
            "fecha", "centro__nombre", "centro_id"
        )
    )

    fecha_inicio = convertir_fecha(request.GET.get("fecha_inicio"))
    fecha_fin = convertir_fecha(request.GET.get("fecha_fin"))
    modalidad = request.GET.get("modalidad", "").strip()

    if fecha_inicio:
        filas = [
            fila for fila in filas
            if fila.fecha >= fecha_inicio
        ]

    if fecha_fin:
        filas = [
            fila for fila in filas
            if fila.fecha <= fecha_fin
        ]

    if modalidad:
        filas = [
            fila for fila in filas
            if fila.modalidad_snapshot == modalidad
        ]

    periodo_desde = (
        fecha_inicio
        or (min((fila.fecha for fila in filas), default=None))
    )

    periodo_hasta = (
        fecha_fin
        or (max((fila.fecha for fila in filas), default=None))
    )

    generado_en = timezone.localtime()
    generado_por = (
        request.user.get_full_name().strip()
        or request.user.get_username()
    )

    buffer = BytesIO()

    ancho, alto = landscape(letter)
    pdf = canvas.Canvas(
        buffer,
        pagesize=(ancho, alto),
    )

    margen = 36
    filas_por_pagina = 18

    total_paginas = max(
        1,
        (len(filas) + filas_por_pagina - 1)
        // filas_por_pagina
    )

    dias = (
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    )

    estilo_celda = ParagraphStyle(
        "ProgramacionCelda",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#1F2937"),
    )

    estilo_celda_centro = ParagraphStyle(
        "ProgramacionCentro",
        parent=estilo_celda,
        fontSize=7,
        leading=8,
    )

    def texto_seguro(valor):
        texto = str(valor or "-")
        return (
            texto.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def dibujar_encabezado(numero_pagina):
        y_superior = alto - 38

        if empresa.logo:
            try:
                with empresa.logo.storage.open(
                    empresa.logo.name,
                    "rb",
                ) as archivo_logo:
                    logo = ImageReader(
                        BytesIO(
                            archivo_logo.read()
                        )
                    )

                pdf.drawImage(
                    logo,
                    margen,
                    alto - 90,
                    width=92,
                    height=48,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                logger_menu_documento.exception(
                    "No fue posible incorporar logo al PDF de programación."
                )

        x_empresa = 142

        pdf.setFillColor(colors.HexColor("#0F172A"))
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(
            x_empresa,
            y_superior,
            empresa.nombre[:60],
        )

        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(colors.HexColor("#475569"))

        pdf.drawString(
            x_empresa,
            y_superior - 15,
            f"RNC: {empresa.rnc or '-'}",
        )

        contacto = " · ".join(
            dato for dato in [
                empresa.telefono,
                empresa.correo,
            ] if dato
        )

        if contacto:
            pdf.drawString(
                x_empresa,
                y_superior - 28,
                contacto[:90],
            )

        direccion = " · ".join(
            dato for dato in [
                empresa.direccion,
                empresa.ciudad,
            ] if dato
        )

        if direccion:
            pdf.drawString(
                x_empresa,
                y_superior - 41,
                direccion[:100],
            )

        pdf.setFillColor(colors.HexColor("#1F4E78"))
        pdf.setFont("Helvetica-Bold", 17)
        pdf.drawRightString(
            ancho - margen,
            y_superior,
            "PROGRAMACIÓN DE MENÚ ESCOLAR",
        )

        periodo_texto = "Todos los registros"

        if periodo_desde or periodo_hasta:
            periodo_texto = (
                f"{periodo_desde.strftime('%d/%m/%Y') if periodo_desde else 'Inicio'}"
                f" – "
                f"{periodo_hasta.strftime('%d/%m/%Y') if periodo_hasta else 'Actualidad'}"
            )

        pdf.setFillColor(colors.HexColor("#475569"))
        pdf.setFont("Helvetica", 8)

        pdf.drawRightString(
            ancho - margen,
            y_superior - 18,
            f"Período: {periodo_texto}",
        )

        pdf.drawRightString(
            ancho - margen,
            y_superior - 31,
            f"Generado: {generado_en:%d/%m/%Y %H:%M}",
        )

        pdf.drawRightString(
            ancho - margen,
            y_superior - 44,
            f"Usuario: {generado_por}",
        )

        pdf.setStrokeColor(colors.HexColor("#CBD5E1"))
        pdf.line(
            margen,
            alto - 103,
            ancho - margen,
            alto - 103,
        )

        # Pie
        pdf.setStrokeColor(colors.HexColor("#E2E8F0"))
        pdf.line(
            margen,
            30,
            ancho - margen,
            30,
        )

        pdf.setFont("Helvetica", 7)
        pdf.setFillColor(colors.HexColor("#64748B"))

        pdf.drawString(
            margen,
            18,
            "Generado por SASTRE ERP",
        )

        pdf.drawRightString(
            ancho - margen,
            18,
            f"Página {numero_pagina} de {total_paginas}",
        )

    encabezados = [
        "Fecha",
        "Día",
        "Centro educativo",
        "Semana",
        "Producto",
        "Programa / versión",
        "Modalidad",
        "Estado",
    ]

    if not filas:
        dibujar_encabezado(1)

        pdf.setFillColor(colors.HexColor("#475569"))
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(
            ancho / 2,
            alto / 2,
            "No existen registros de programación para los filtros seleccionados.",
        )

        pdf.save()
        buffer.seek(0)

        return FileResponse(
            buffer,
            content_type="application/pdf",
            filename="programacion_menu_escolar.pdf",
        )

    for numero_pagina in range(1, total_paginas + 1):
        inicio = (numero_pagina - 1) * filas_por_pagina
        fin = inicio + filas_por_pagina
        pagina_filas = filas[inicio:fin]

        dibujar_encabezado(numero_pagina)

        datos = [encabezados]

        estados_sin_docencia = []
        filas_sabado = []
        filas_domingo = []

        for indice, fila in enumerate(
            pagina_filas,
            start=1,
        ):
            codigo_centro = (
                getattr(fila.centro, "codigo", "")
                or getattr(fila.centro, "codigo_centro", "")
                or ""
            )

            centro_texto = (
                f"{codigo_centro} · {fila.centro.nombre}"
                if codigo_centro
                else fila.centro.nombre
            )

            programa_version = (
                f"{fila.programa_snapshot} / "
                f"{fila.version_snapshot}"
            )

            datos.append([
                Paragraph(
                    texto_seguro(f"{fila.fecha:%d/%m/%Y}"),
                    estilo_celda,
                ),
                Paragraph(
                    texto_seguro(dias[fila.dia_semana]),
                    estilo_celda,
                ),
                Paragraph(
                    texto_seguro(centro_texto),
                    estilo_celda_centro,
                ),
                Paragraph(
                    texto_seguro(
                        f"S{fila.semana_ciclo}"
                        if fila.semana_ciclo
                        else "-"
                    ),
                    estilo_celda,
                ),
                Paragraph(
                    texto_seguro(fila.producto or "-"),
                    estilo_celda,
                ),
                Paragraph(
                    texto_seguro(programa_version),
                    estilo_celda,
                ),
                Paragraph(
                    texto_seguro(fila.modalidad_snapshot),
                    estilo_celda,
                ),
                Paragraph(
                    texto_seguro(fila.get_estado_display()),
                    estilo_celda,
                ),
            ])

            if (
                fila.estado
                == ProgramacionMenuEscolar.Estado.SIN_DOCENCIA
            ):
                estados_sin_docencia.append(indice)
            elif fila.fecha.weekday() == 5:
                filas_sabado.append(indice)
            elif fila.fecha.weekday() == 6:
                filas_domingo.append(indice)

        tabla = Table(
            datos,
            colWidths=[
                58,
                65,
                175,
                48,
                155,
                125,
                70,
                72,
            ],
            repeatRows=1,
        )

        comandos = [
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#1F4E78"),
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white,
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold",
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, 0),
                7,
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, 0),
                "CENTER",
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP",
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.35,
                colors.HexColor("#D9E2F3"),
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#F8FAFC"),
                ],
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
        ]

        for indice in filas_sabado:
            comandos.append(
                (
                    "BACKGROUND",
                    (0, indice),
                    (-1, indice),
                    colors.HexColor("#EAF4FF"),
                )
            )

        for indice in filas_domingo:
            comandos.append(
                (
                    "BACKGROUND",
                    (0, indice),
                    (-1, indice),
                    colors.HexColor("#FFF4CC"),
                )
            )

        for indice in estados_sin_docencia:
            comandos.append(
                (
                    "BACKGROUND",
                    (0, indice),
                    (-1, indice),
                    colors.HexColor("#FDE2E2"),
                )
            )

        tabla.setStyle(
            TableStyle(comandos)
        )

        ancho_tabla = ancho - (margen * 2)
        _, alto_tabla = tabla.wrap(
            ancho_tabla,
            alto - 165,
        )

        tabla.drawOn(
            pdf,
            margen,
            alto - 125 - alto_tabla,
        )

        if numero_pagina < total_paginas:
            pdf.showPage()

    pdf.save()
    buffer.seek(0)

    return FileResponse(
        buffer,
        content_type="application/pdf",
        filename="programacion_menu_escolar.pdf",
    )

# ===== MOTOR DOCUMENTAL SASTRE 02 =====

from django.db import transaction as documento_transaction
from django.shortcuts import get_object_or_404 as documento_get_object_or_404
from django.views.decorators.http import require_POST as documento_require_POST
from django.utils.html import escape as documento_escape

from .models import (
    DocumentoInstitucional,
    DiaCalendarioEscolar,
    DiaNoDocencia,
)


def _numero_documento_siguiente(empresa, anio):
    prefijo = f"DOC-{anio}-"

    numeros = (
        DocumentoInstitucional.objects
        .filter(
            empresa=empresa,
            numero__startswith=prefijo,
        )
        .values_list("numero", flat=True)
    )

    mayor = 0

    for numero in numeros:
        try:
            mayor = max(
                mayor,
                int(str(numero).rsplit("-", 1)[-1]),
            )
        except (TypeError, ValueError):
            pass

    return f"{prefijo}{mayor + 1:06d}"


def _dias_no_laborables_documento(empresa, fecha_desde, fecha_hasta):
    resultado = []
    fechas = set()

    dias = (
        DiaCalendarioEscolar.objects
        .filter(
            calendario__empresa=empresa,
            calendario__estado="ACTIVO",
            fecha__range=[fecha_desde, fecha_hasta],
        )
        .exclude(
            clasificacion__in=[
                DiaCalendarioEscolar.Clasificacion.DOCENCIA,
                DiaCalendarioEscolar.Clasificacion.REQUIERE_REVISION,
            ]
        )
        .order_by("fecha")
    )

    for dia in dias:
        if (dia.origen or "").upper().startswith("PREVISUALIZACION"):
            continue

        resultado.append({
            "fecha": dia.fecha.isoformat(),
            "clasificacion": dia.clasificacion,
            "clasificacion_texto": dia.get_clasificacion_display(),
            "motivo": dia.motivo or dia.get_clasificacion_display(),
            "origen": dia.origen or "",
            "fuente": "CALENDARIO_ESCOLAR",
        })

        fechas.add(dia.fecha)

    legacy = (
        DiaNoDocencia.objects
        .filter(
            empresa=empresa,
            fecha__range=[fecha_desde, fecha_hasta],
            activo=True,
        )
        .order_by("fecha")
    )

    for dia in legacy:
        if dia.fecha in fechas:
            continue

        resultado.append({
            "fecha": dia.fecha.isoformat(),
            "clasificacion": dia.tipo,
            "clasificacion_texto": dia.get_tipo_display(),
            "motivo": dia.motivo or dia.get_tipo_display(),
            "origen": "LEGACY",
            "fuente": "DIA_NO_DOCENCIA",
        })

    resultado.sort(key=lambda x: x["fecha"])

    return resultado



import re
from html.parser import HTMLParser
from html import escape as _html_escape_documento


class _SanitizadorDocumentoHTML(HTMLParser):
    ETIQUETAS = {
        "p", "br", "strong", "b", "em", "i", "u",
        "ul", "ol", "li", "h1", "h2", "h3",
        "div", "span", "blockquote", "table", "thead", "tbody", "tr", "th", "td",
    }

    ALINEACIONES = {"left", "center", "right", "justify"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.salida = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag not in self.ETIQUETAS:
            return

        atributos_limpios = []

        for nombre, valor in attrs:
            nombre = nombre.lower()
            valor = (valor or "").strip()

            if nombre == "style":
                estilos = []

                for regla in valor.split(";"):
                    if ":" not in regla:
                        continue

                    propiedad, dato = regla.split(":", 1)
                    propiedad = propiedad.strip().lower()
                    dato = dato.strip().lower()

                    if (
                        propiedad == "text-align"
                        and dato in self.ALINEACIONES
                    ):
                        estilos.append(f"text-align:{dato}")

                    elif propiedad == "margin-left":
                        match = re.fullmatch(r"(\d{1,3})px", dato)
                        if match and int(match.group(1)) <= 160:
                            estilos.append(f"margin-left:{dato}")

                    elif propiedad == "font-size":
                        match = re.fullmatch(r"(\d{1,2})px", dato)
                        if match and 10 <= int(match.group(1)) <= 32:
                            estilos.append(f"font-size:{dato}")

                if estilos:
                    atributos_limpios.append(
                        ' style="' +
                        _html_escape_documento(";".join(estilos), quote=True) +
                        '"'
                    )

        self.salida.append(
            "<" + tag + "".join(atributos_limpios) + ">"
        )

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.ETIQUETAS and tag != "br":
            self.salida.append(f"</{tag}>")

    def handle_data(self, data):
        self.salida.append(_html_escape_documento(data))

    def handle_entityref(self, name):
        self.salida.append(f"&{name};")

    def handle_charref(self, name):
        self.salida.append(f"&#{name};")


def _sanitizar_html_documento(valor):
    valor = (valor or "").strip()

    if not valor:
        return ""

    parser = _SanitizadorDocumentoHTML()
    parser.feed(valor)
    parser.close()

    return "".join(parser.salida)



def _conduces_anulados_documento(
    empresa,
    fecha_desde,
    fecha_hasta,
    dias_no_laborables=None,
):
    """
    Snapshot de anulaciones particulares de centros.

    Las fechas generales sin docencia pertenecen al calendario escolar
    y no se duplican como incidencias particulares.
    """
    from datetime import date

    fechas_generales = set()

    for item in (dias_no_laborables or []):
        try:
            fechas_generales.add(
                date.fromisoformat(item.get("fecha", ""))
            )
        except (TypeError, ValueError):
            continue

    qs = (
        Conduce.all_objects
        .filter(
            empresa=empresa,
            estado="anulado",
            fecha__range=[fecha_desde, fecha_hasta],
            eliminado_en__isnull=True,
        )
        .select_related("centro")
        .order_by("fecha", "numero", "id")
    )

    resultado = []

    for conduce in qs:

        # Un feriado/suspensión general no se presenta como
        # incidencia particular de un centro.
        if conduce.fecha in fechas_generales:
            continue

        resultado.append({
            "id": conduce.id,
            "fecha": conduce.fecha.isoformat(),
            "numero": str(conduce.numero or ""),
            "codigo_centro": str(
                getattr(conduce.centro, "codigo", "") or ""
            ),
            "centro": str(
                getattr(conduce.centro, "nombre", "") or ""
            ),
            "producto": str(conduce.producto or ""),
            "cantidad": int(conduce.cantidad or 0),
            "motivo": str(
                (conduce.observaciones or "").strip()
                or "Sin motivo de anulación registrado."
            ),
        })

    return resultado


def _fecha_documental_espanol(fecha):
    meses = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }

    return (
        f"{fecha.day} de "
        f"{meses.get(fecha.month, '')} de "
        f"{fecha.year}"
    )


def _texto_sugerido_nota_aclaratoria(
    fecha_desde,
    fecha_hasta,
    dias_no_laborables,
    conduces_anulados=None,
):
    """
    Redacción institucional basada exclusivamente en hechos
    almacenados en SASTRE.
    """
    from datetime import date

    conduces_anulados = conduces_anulados or []

    desde_texto = _fecha_documental_espanol(fecha_desde)
    hasta_texto = _fecha_documental_espanol(fecha_hasta)

    html = (
        '<p style="text-align:justify;">'
        "Por medio de la presente, tenemos a bien informar y dejar "
        "constancia formal de las incidencias correspondientes al período "
        f"comprendido entre el <strong>{desde_texto}</strong> y el "
        f"<strong>{hasta_texto}</strong>, con el objetivo de documentar "
        "los días sin docencia de carácter general establecidos en el "
        "calendario escolar y las incidencias particulares que hayan "
        "motivado la anulación de conduces durante dicho período."
        "</p>"
    )

    # --------------------------------------------------------
    # DIAS GENERALES
    # --------------------------------------------------------

    html += (
        "<h3>1. DÍAS SIN DOCENCIA DE CARÁCTER GENERAL</h3>"
    )

    if dias_no_laborables:

        html += (
            '<p style="text-align:justify;">'
            "Durante el período indicado, el calendario escolar "
            "registra los siguientes días sin docencia de carácter "
            "general, aplicables a los centros educativos:"
            "</p><ul>"
        )

        for dia in dias_no_laborables:

            try:
                fecha = date.fromisoformat(
                    dia.get("fecha", "")
                )
                fecha_texto = _fecha_documental_espanol(fecha)
            except (TypeError, ValueError):
                fecha_texto = documento_escape(
                    dia.get("fecha", "")
                )

            motivo = documento_escape(
                dia.get("motivo", "")
            )

            clasificacion = documento_escape(
                dia.get("clasificacion_texto", "")
            )

            html += (
                f"<li><strong>{fecha_texto}:</strong> "
                f"{motivo}"
            )

            if (
                clasificacion
                and clasificacion.lower()
                not in motivo.lower()
            ):
                html += f" ({clasificacion})"

            html += ".</li>"

        html += "</ul>"

    else:

        html += (
            '<p style="text-align:justify;">'
            "No se identificaron días sin docencia de carácter general "
            "registrados en el calendario escolar para el período indicado."
            "</p>"
        )

    # --------------------------------------------------------
    # CONDUCES ANULADOS
    # --------------------------------------------------------

    html += (
        "<h3>2. CONDUCES ANULADOS POR INCIDENCIAS PARTICULARES "
        "DE CENTROS EDUCATIVOS</h3>"
    )

    if conduces_anulados:

        html += (
            '<p style="text-align:justify;">'
            "En fechas establecidas con docencia programada, determinados "
            "centros educativos presentaron incidencias particulares que "
            "dieron lugar a la anulación de conduces previamente "
            "generados. El detalle se presenta a continuación:"
            "</p>"
        )

        html += (
            "<table>"
            "<thead>"
            "<tr>"
            "<th>Fecha</th>"
            "<th>No. conduce</th>"
            "<th>Código</th>"
            "<th>Centro educativo</th>"
            "<th>Producto</th>"
            "<th>Cantidad</th>"
            "<th>Motivo de anulación</th>"
            "</tr>"
            "</thead>"
            "<tbody>"
        )

        for item in conduces_anulados:

            try:
                fecha = date.fromisoformat(
                    item.get("fecha", "")
                )
                fecha_texto = fecha.strftime("%d/%m/%Y")
            except (TypeError, ValueError):
                fecha_texto = documento_escape(
                    item.get("fecha", "")
                )

            numero = documento_escape(
                item.get("numero", "")
            )

            codigo = documento_escape(
                item.get("codigo_centro", "")
            )

            centro = documento_escape(
                item.get("centro", "")
            )

            producto = documento_escape(
                item.get("producto", "")
            )

            cantidad = int(
                item.get("cantidad", 0) or 0
            )

            motivo = documento_escape(
                item.get("motivo", "")
            )

            html += (
                "<tr>"
                f"<td>{fecha_texto}</td>"
                f"<td>{numero}</td>"
                f"<td>{codigo}</td>"
                f"<td>{centro}</td>"
                f"<td>{producto}</td>"
                f"<td>{cantidad:,}</td>"
                f"<td>{motivo}</td>"
                "</tr>"
            )

        html += "</tbody></table>"

        html += (
            '<p style="text-align:justify;">'
            "Los conduces relacionados anteriormente corresponden "
            "exclusivamente a anulaciones registradas en SASTRE por "
            "incidencias particulares de los centros educativos en las "
            "fechas indicadas."
            "</p>"
        )

    else:

        html += (
            '<p style="text-align:justify;">'
            "No se identificaron conduces anulados por incidencias "
            "particulares de centros educativos dentro del período "
            "seleccionado."
            "</p>"
        )

    # --------------------------------------------------------
    # CIERRE
    # --------------------------------------------------------

    html += "<h3>3. CONSIDERACIÓN FINAL</h3>"

    html += (
        '<p style="text-align:justify;">'
        "La presente comunicación se emite para los fines "
        "correspondientes, dejando constancia de los días sin docencia "
        "de carácter general registrados en el calendario escolar y de "
        "las incidencias particulares que motivaron la anulación de "
        "conduces durante el período indicado."
        "</p>"
    )

    html += (
        '<p style="text-align:justify;">'
        "Agradecemos su atención y quedamos a disposición para cualquier "
        "información adicional que sea requerida."
        "</p>"
    )

    return _sanitizar_html_documento(html)


def _finalizar_documento_institucional(
    documento,
    empresa,
    usuario,
):
    """
    Congela un documento institucional.

    El PDF final se genera una sola vez y queda almacenado
    como evidencia histórica de la emisión.
    """

    if documento.estado != DocumentoInstitucional.Estado.BORRADOR:
        return False, "Solo los borradores pueden finalizarse."

    # --------------------------------------------------------
    # Completar identidad desde la empresa si aún está vacía.
    # --------------------------------------------------------

    if not documento.firmante:
        documento.firmante = (
            getattr(
                empresa,
                "firmante_predeterminado",
                "",
            )
            or ""
        )

    if not documento.cargo_firmante:
        documento.cargo_firmante = (
            getattr(
                empresa,
                "cargo_firmante_predeterminado",
                "",
            )
            or ""
        )

    # --------------------------------------------------------
    # Validaciones antes de emitir.
    # --------------------------------------------------------

    errores = []

    if not documento.destinatario:
        errores.append("destinatario")

    if not documento.contenido_html:
        errores.append("contenido")

    if not documento.firmante:
        errores.append("nombre del firmante")

    if not documento.cargo_firmante:
        errores.append("cargo del firmante")

    if (
        documento.incluir_firma
        and not getattr(
            empresa,
            "firma_autorizada",
            None,
        )
    ):
        errores.append("imagen de firma autorizada")

    if (
        documento.incluir_sello
        and not getattr(
            empresa,
            "sello_institucional",
            None,
        )
    ):
        errores.append("sello institucional")

    if errores:
        return (
            False,
            "No se puede finalizar. Falta: "
            + ", ".join(errores)
            + "."
        )

    momento = timezone.now()

    # --------------------------------------------------------
    # Snapshot de emisión
    # --------------------------------------------------------

    snapshot = dict(
        documento.datos_snapshot
        or {}
    )

    snapshot["empresa_emision"] = {
        "nombre": empresa.nombre or "",
        "rnc": getattr(empresa, "rnc", "") or "",
        "direccion": getattr(
            empresa,
            "direccion",
            "",
        ) or "",
        "telefono": getattr(
            empresa,
            "telefono",
            "",
        ) or "",
        "ciudad": getattr(
            empresa,
            "ciudad",
            "",
        ) or "",
        "correo": getattr(
            empresa,
            "correo",
            "",
        ) or "",
    }

    snapshot["firma_emision"] = {
        "firmante": documento.firmante,
        "cargo": documento.cargo_firmante,
        "incluir_firma": bool(
            documento.incluir_firma
        ),
        "incluir_sello": bool(
            documento.incluir_sello
        ),
        "firma_archivo": (
            empresa.firma_autorizada.name
            if getattr(
                empresa,
                "firma_autorizada",
                None,
            )
            else ""
        ),
        "sello_archivo": (
            empresa.sello_institucional.name
            if getattr(
                empresa,
                "sello_institucional",
                None,
            )
            else ""
        ),
        "logo_archivo": (
            empresa.logo.name
            if getattr(
                empresa,
                "logo",
                None,
            )
            else ""
        ),
    }

    snapshot["emision"] = {
        "estado": "FINALIZADO",
        "finalizado_en": momento.isoformat(),
        "finalizado_por_id": (
            usuario.id
            if usuario
            else None
        ),
    }

    documento.datos_snapshot = snapshot

    # --------------------------------------------------------
    # Generar PDF definitivo ANTES de cambiar el estado.
    # --------------------------------------------------------

    try:
        pdf_buffer = _pdf_documento_institucional(
            documento,
            empresa,
        )
    except Exception:
        return (
            False,
            "No fue posible generar el PDF definitivo. "
            "El documento continúa como borrador."
        )

    from django.core.files.base import ContentFile

    nombre_pdf = (
        f"{documento.numero}.pdf"
    )

    documento.pdf_final.save(
        nombre_pdf,
        ContentFile(
            pdf_buffer.getvalue()
        ),
        save=False,
    )

    # --------------------------------------------------------
    # WORD HISTORICO DE EMISION
    # --------------------------------------------------------
    #
    # El PDF sigue siendo el artefacto oficial principal.
    # Si Word no pudiera generarse, no bloquea la emisión.
    # --------------------------------------------------------

    try:

        docx_buffer = (
            _docx_documento_institucional(
                documento,
                empresa,
            )
        )

        documento.docx_final.save(
            f"{documento.numero}.docx",
            ContentFile(
                docx_buffer.getvalue()
            ),
            save=False,
        )

    except Exception:
        pass

    documento.estado = (
        DocumentoInstitucional.Estado.FINALIZADO
    )

    documento.finalizado_en = momento
    documento.finalizado_por = usuario
    documento.modificado_por = usuario

    documento.save()

    return (
        True,
        f"Documento {documento.numero} finalizado correctamente."
    )


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
def documentos_institucionales(request):
    empresa = obtener_empresa(request)

    documentos = (
        DocumentoInstitucional.objects
        .filter(
            empresa=empresa,
            eliminado_en__isnull=True,
        )
        .order_by("-fecha_documento", "-id")
    )

    return render(
        request,
        "documentos_institucionales.html",
        {
            "empresa": empresa,
            "documentos": documentos,
        },
    )


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
def nuevo_documento_institucional(request):
    empresa = obtener_empresa(request)

    fecha_desde_inicial = (
        request.GET.get("fecha_inicio", "").strip()
        or request.POST.get("fecha_desde", "").strip()
    )

    fecha_hasta_inicial = (
        request.GET.get("fecha_fin", "").strip()
        or request.POST.get("fecha_hasta", "").strip()
    )

    if request.method == "POST":
        from datetime import date

        fecha_desde = date.fromisoformat(
            request.POST.get("fecha_desde")
        )

        fecha_hasta = date.fromisoformat(
            request.POST.get("fecha_hasta")
        )

        if fecha_desde > fecha_hasta:
            messages.error(
                request,
                "La fecha inicial no puede ser mayor que la fecha final.",
            )
            return redirect("nuevo_documento_institucional")

        dias = _dias_no_laborables_documento(
            empresa,
            fecha_desde,
            fecha_hasta,
        )

        conduces_anulados = _conduces_anulados_documento(
            empresa,
            fecha_desde,
            fecha_hasta,
            dias,
        )

        contenido = _sanitizar_html_documento(
            request.POST.get(
                "contenido_html",
                "",
            )
        )

        if not contenido:
            contenido = _texto_sugerido_nota_aclaratoria(
                fecha_desde,
                fecha_hasta,
                dias,
                conduces_anulados,
            )

        with documento_transaction.atomic():
            numero = _numero_documento_siguiente(
                empresa,
                timezone.localdate().year,
            )

            documento = DocumentoInstitucional.objects.create(
                empresa=empresa,
                numero=numero,
                tipo=DocumentoInstitucional.Tipo.NOTA_ACLARATORIA,
                estado=DocumentoInstitucional.Estado.BORRADOR,
                origen=DocumentoInstitucional.Origen.ASISTIDO,
                fecha_documento=timezone.localdate(),
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                destinatario=(
                    request.POST.get("destinatario", "").strip()
                    or "Instituto Nacional de Bienestar Estudiantil (INABIE)"
                ),
                asunto=(
                    request.POST.get("asunto", "").strip()
                    or "Nota aclaratoria"
                ),
                contenido_html=contenido,
                firmante=(
                    request.POST.get("firmante", "").strip()
                    or empresa.firmante_predeterminado
                    or ""
                ),
                cargo_firmante=(
                    request.POST.get(
                        "cargo_firmante",
                        "",
                    ).strip()
                    or empresa.cargo_firmante_predeterminado
                    or ""
                ),
                incluir_firma=(
                    "incluir_firma" in request.POST
                ),
                incluir_sello=(
                    "incluir_sello" in request.POST
                ),
                dias_no_laborables_snapshot=dias,
                datos_snapshot={
                    "periodo": {
                        "desde": fecha_desde.isoformat(),
                        "hasta": fecha_hasta.isoformat(),
                    },
                    "conduces_anulados": conduces_anulados,
                    "totales": {
                        "cantidad_conduces_anulados": len(
                            conduces_anulados
                        ),
                        "unidades_conduces_anulados": sum(
                            int(item.get("cantidad", 0) or 0)
                            for item in conduces_anulados
                        ),
                    },
                },
                creado_por=request.user,
                modificado_por=request.user,
            )

        messages.success(
            request,
            f"Documento {documento.numero} creado como borrador.",
        )

        return redirect(
            "editar_documento_institucional",
            documento_id=documento.id,
        )

    return render(
        request,
        "documento_institucional_form.html",
        {
            "empresa": empresa,
            "fecha_desde": fecha_desde_inicial,
            "fecha_hasta": fecha_hasta_inicial,
        },
    )


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
def editar_documento_institucional(request, documento_id):
    empresa = obtener_empresa(request)

    documento = documento_get_object_or_404(
        DocumentoInstitucional,
        id=documento_id,
        empresa=empresa,
        eliminado_en__isnull=True,
    )

    if documento.estado != DocumentoInstitucional.Estado.BORRADOR:
        messages.error(
            request,
            "Solo los documentos en borrador pueden editarse.",
        )
        return redirect("documentos_institucionales")

    # ========================================================
    # AUTOCOMPLETAR IDENTIDAD DEL FIRMANTE
    # ========================================================
    # Solo aplica a BORRADORES que todavía no tienen estos datos.
    # Una vez copiados al documento, quedan independientes de
    # cambios futuros realizados en la configuración de la empresa.
    campos_identidad_actualizados = []

    if (
        not documento.firmante
        and empresa.firmante_predeterminado
    ):
        documento.firmante = empresa.firmante_predeterminado
        campos_identidad_actualizados.append("firmante")

    if (
        not documento.cargo_firmante
        and empresa.cargo_firmante_predeterminado
    ):
        documento.cargo_firmante = (
            empresa.cargo_firmante_predeterminado
        )
        campos_identidad_actualizados.append("cargo_firmante")

    if campos_identidad_actualizados:
        campos_identidad_actualizados.append("modificado_en")
        documento.save(
            update_fields=campos_identidad_actualizados
        )

    if request.method == "POST":
        accion = request.POST.get("accion", "guardar")

        if accion == "restaurar_sastre":
            documento.contenido_html = _texto_sugerido_nota_aclaratoria(
                documento.fecha_desde,
                documento.fecha_hasta,
                documento.dias_no_laborables_snapshot or [],
                (
                    (documento.datos_snapshot or {}).get(
                        "conduces_anulados",
                        [],
                    )
                ),
            )
            documento.modificado_por = request.user
            documento.origen = DocumentoInstitucional.Origen.ASISTIDO
            documento.save(
                update_fields=(
                    "contenido_html",
                    "modificado_por",
                    "origen",
                    "modificado_en",
                )
            )

            messages.success(
                request,
                "Se restauró la redacción sugerida por SASTRE.",
            )

            return redirect(
                "editar_documento_institucional",
                documento_id=documento.id,
            )

        documento.destinatario = request.POST.get(
            "destinatario",
            "",
        ).strip()

        documento.asunto = request.POST.get(
            "asunto",
            "",
        ).strip()

        documento.contenido_html = _sanitizar_html_documento(
            request.POST.get(
                "contenido_html",
                "",
            )
        )

        documento.firmante = request.POST.get(
            "firmante",
            "",
        ).strip()

        documento.cargo_firmante = request.POST.get(
            "cargo_firmante",
            "",
        ).strip()

        documento.incluir_firma = (
            "incluir_firma" in request.POST
        )

        documento.incluir_sello = (
            "incluir_sello" in request.POST
        )

        documento.modificado_por = request.user
        documento.save()

        if accion == "finalizar":
            ok, mensaje = _finalizar_documento_institucional(
                documento,
                empresa,
                request.user,
            )

            if ok:
                messages.success(
                    request,
                    mensaje,
                )
                return redirect(
                    "documentos_institucionales"
                )

            messages.error(
                request,
                mensaje,
            )

            return redirect(
                "editar_documento_institucional",
                documento_id=documento.id,
            )

        messages.success(
            request,
            "Borrador guardado correctamente.",
        )

        return redirect(
            "editar_documento_institucional",
            documento_id=documento.id,
        )

    return render(
        request,
        "documento_institucional_form.html",
        {
            "empresa": empresa,
            "documento": documento,
            "dias_snapshot": documento.dias_no_laborables_snapshot,
            "conduces_snapshot": (
                (documento.datos_snapshot or {}).get(
                    "conduces_anulados",
                    [],
                )
            ),
        },
    )


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
@documento_require_POST
def eliminar_documento_institucional(request, documento_id):
    empresa = obtener_empresa(request)

    documento = documento_get_object_or_404(
        DocumentoInstitucional,
        id=documento_id,
        empresa=empresa,
        eliminado_en__isnull=True,
    )

    if documento.estado != DocumentoInstitucional.Estado.BORRADOR:
        messages.error(
            request,
            "Solo los borradores pueden eliminarse.",
        )
        return redirect("documentos_institucionales")

    documento.eliminar_logicamente(request.user)

    messages.success(
        request,
        f"Documento {documento.numero} eliminado.",
    )

    return redirect("documentos_institucionales")




@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
@documento_require_POST
def finalizar_documento_institucional(
    request,
    documento_id,
):
    empresa = obtener_empresa(request)

    documento = documento_get_object_or_404(
        DocumentoInstitucional,
        id=documento_id,
        empresa=empresa,
        eliminado_en__isnull=True,
    )

    ok, mensaje = _finalizar_documento_institucional(
        documento,
        empresa,
        request.user,
    )

    if ok:
        messages.success(
            request,
            mensaje,
        )
    else:
        messages.error(
            request,
            mensaje,
        )

    return redirect(
        "documentos_institucionales"
    )


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
@documento_require_POST
def duplicar_documento_institucional(
    request,
    documento_id,
):
    """
    Crea una nueva versión editable de un documento emitido.

    El documento original nunca se modifica.
    """

    from copy import deepcopy

    empresa = obtener_empresa(request)

    documento = documento_get_object_or_404(
        DocumentoInstitucional,
        id=documento_id,
        empresa=empresa,
        eliminado_en__isnull=True,
    )

    if documento.estado not in (
        DocumentoInstitucional.Estado.FINALIZADO,
        DocumentoInstitucional.Estado.ANULADO,
    ):
        messages.error(
            request,
            "Solo los documentos finalizados o anulados "
            "pueden generar una nueva versión.",
        )
        return redirect(
            "documentos_institucionales"
        )

    # El documento_base siempre debe apuntar al primer
    # documento de la serie.
    base = (
        documento.documento_base
        or documento
    )

    with documento_transaction.atomic():

        base = (
            DocumentoInstitucional.objects
            .select_for_update()
            .get(
                pk=base.pk,
                empresa=empresa,
            )
        )

        ultima_version = (
            DocumentoInstitucional.objects
            .filter(
                empresa=empresa,
                documento_base=base,
            )
            .order_by("-version")
            .values_list(
                "version",
                flat=True,
            )
            .first()
        )

        siguiente_version = (
            max(
                int(base.version or 1),
                int(ultima_version or 1),
            )
            + 1
        )

        numero = _numero_documento_siguiente(
            empresa,
            timezone.localdate().year,
        )

        snapshot = deepcopy(
            documento.datos_snapshot
            or {}
        )

        # Una nueva versión todavía no es una emisión.
        snapshot.pop(
            "emision",
            None,
        )

        snapshot["versionado"] = {
            "documento_base_id": base.id,
            "documento_base_numero": base.numero,
            "version": siguiente_version,
            "creado_desde_id": documento.id,
            "creado_desde_numero": documento.numero,
            "creado_en": timezone.now().isoformat(),
        }

        nuevo = DocumentoInstitucional.objects.create(
            empresa=empresa,
            numero=numero,
            tipo=documento.tipo,
            estado=DocumentoInstitucional.Estado.BORRADOR,
            origen=documento.origen,
            fecha_documento=timezone.localdate(),
            fecha_desde=documento.fecha_desde,
            fecha_hasta=documento.fecha_hasta,
            destinatario=documento.destinatario,
            asunto=documento.asunto,
            contenido_html=documento.contenido_html,
            firmante=documento.firmante,
            cargo_firmante=documento.cargo_firmante,
            incluir_firma=documento.incluir_firma,
            incluir_sello=documento.incluir_sello,
            dias_no_laborables_snapshot=deepcopy(
                documento.dias_no_laborables_snapshot
                or []
            ),
            datos_snapshot=snapshot,
            documento_base=base,
            version=siguiente_version,
            creado_por=request.user,
            modificado_por=request.user,
        )

    messages.success(
        request,
        (
            f"Nueva versión V{nuevo.version} creada como "
            f"borrador: {nuevo.numero}."
        ),
    )

    return redirect(
        "editar_documento_institucional",
        documento_id=nuevo.id,
    )


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
@documento_require_POST
def anular_documento_institucional(
    request,
    documento_id,
):
    empresa = obtener_empresa(request)

    documento = documento_get_object_or_404(
        DocumentoInstitucional,
        id=documento_id,
        empresa=empresa,
        eliminado_en__isnull=True,
    )

    if (
        documento.estado
        != DocumentoInstitucional.Estado.FINALIZADO
    ):
        messages.error(
            request,
            "Solo los documentos finalizados pueden anularse.",
        )
        return redirect(
            "documentos_institucionales"
        )

    motivo = request.POST.get(
        "motivo_anulacion",
        "",
    ).strip()

    if not motivo:
        messages.error(
            request,
            "Debe indicar el motivo de la anulación.",
        )
        return redirect(
            "documentos_institucionales"
        )

    momento = timezone.now()

    snapshot = dict(
        documento.datos_snapshot
        or {}
    )

    emision = dict(
        snapshot.get(
            "emision",
            {},
        )
    )

    emision.update({
        "estado": "ANULADO",
        "anulado_en": momento.isoformat(),
        "anulado_por_id": request.user.id,
        "motivo_anulacion": motivo,
    })

    snapshot["emision"] = emision

    documento.datos_snapshot = snapshot
    documento.estado = (
        DocumentoInstitucional.Estado.ANULADO
    )
    documento.anulado_en = momento
    documento.anulado_por = request.user
    documento.motivo_anulacion = motivo
    documento.modificado_por = request.user

    documento.save(
        update_fields=[
            "datos_snapshot",
            "estado",
            "anulado_en",
            "anulado_por",
            "motivo_anulacion",
            "modificado_por",
            "modificado_en",
        ]
    )

    messages.success(
        request,
        f"Documento {documento.numero} anulado correctamente.",
    )

    return redirect(
        "documentos_institucionales"
    )


# ============================================================
# DOCUMENTOS INSTITUCIONALES - SALIDA PDF
# ============================================================

def _pdf_documento_institucional(documento, empresa):
    import os
    from io import BytesIO
    from html import escape as html_escape
    from html.parser import HTMLParser

    from reportlab.lib import colors
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import (
        TA_CENTER,
        TA_JUSTIFY,
        TA_LEFT,
        TA_RIGHT,
    )
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import (
        ParagraphStyle,
        getSampleStyleSheet,
    )
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image,
        HRFlowable,
        KeepTogether,
        CondPageBreak,
        Flowable,
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=12 * mm,
        bottomMargin=16 * mm,
        title=documento.asunto or "Nota aclaratoria",
        author=empresa.nombre or "",
    )

    estilos = getSampleStyleSheet()

    estilo_empresa = ParagraphStyle(
        "EmpresaDocumento",
        parent=estilos["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=13,
        alignment=TA_CENTER,
        spaceAfter=2,
    )

    estilo_datos = ParagraphStyle(
        "DatosEmpresaDocumento",
        parent=estilos["Normal"],
        fontName="Times-Roman",
        fontSize=9.2,
        leading=10.8,
        alignment=TA_CENTER,
        spaceAfter=1,
    )

    estilo_numero = ParagraphStyle(
        "NumeroDocumento",
        parent=estilos["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        alignment=TA_LEFT,
    )

    estilo_fecha = ParagraphStyle(
        "FechaDocumento",
        parent=estilos["Normal"],
        fontName="Times-Roman",
        fontSize=9.8,
        leading=11.5,
        alignment=TA_RIGHT,
    )

    estilo_titulo = ParagraphStyle(
        "TituloDocumento",
        parent=estilos["Normal"],
        fontName="Times-Bold",
        fontSize=15.5,
        leading=18,
        alignment=TA_CENTER,
        textColor=HexColor("#123B72"),
        spaceBefore=5,
        spaceAfter=12,
    )

    estilo_destinatario = ParagraphStyle(
        "DestinatarioDocumento",
        parent=estilos["Normal"],
        fontName="Times-Roman",
        fontSize=10.3,
        leading=12.7,
        alignment=TA_LEFT,
        spaceAfter=11,
    )

    estilo_cuerpo = ParagraphStyle(
        "CuerpoDocumento",
        parent=estilos["Normal"],
        fontName="Times-Roman",
        fontSize=10.3,
        leading=14.7,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
    )

    estilo_seccion = ParagraphStyle(
        "SeccionDocumento",
        parent=estilos["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.1,
        leading=12.5,
        alignment=TA_LEFT,
        textColor=HexColor("#123B72"),
        spaceBefore=6,
        spaceAfter=5,
    )

    estilo_lista = ParagraphStyle(
        "ListaDocumento",
        parent=estilo_cuerpo,
        leftIndent=16,
        firstLineIndent=-7,
    )

    estilo_tabla = ParagraphStyle(
        "CeldaDocumento",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=7.1,
        leading=8.5,
        alignment=TA_LEFT,
    )

    estilo_tabla_centro = ParagraphStyle(
        "CeldaCentroDocumento",
        parent=estilo_tabla,
        alignment=TA_CENTER,
    )

    story = []

    # ========================================================
    # MEMBRETE
    # ========================================================

    if getattr(empresa, "logo", None):
        try:
            with empresa.logo.storage.open(
                empresa.logo.name,
                "rb",
            ) as archivo_logo:
                logo_buffer = BytesIO(
                    archivo_logo.read()
                )

            logo = Image(
                logo_buffer
            )

            # Membrete institucional:
            # aumenta ligeramente el logo pero conserva
            # siempre su proporción original.
            logo._restrictSize(
                45 * mm,
                24 * mm,
            )

            logo.hAlign = "CENTER"

            story.append(logo)
            story.append(Spacer(1, 1.5 * mm))

        except Exception:
            pass

    story.append(
        Paragraph(
            html_escape((empresa.nombre or "").upper()),
            estilo_empresa,
        )
    )

    if empresa.direccion:
        story.append(
            Paragraph(
                html_escape(empresa.direccion),
                estilo_datos,
            )
        )

    contacto = []

    if empresa.telefono:
        contacto.append(
            "Teléfono.: " + html_escape(empresa.telefono)
        )

    if empresa.rnc:
        contacto.append(
            "RNC.: " + html_escape(empresa.rnc)
        )

    if contacto:
        story.append(
            Paragraph(
                " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(contacto),
                estilo_datos,
            )
        )

    if empresa.correo:
        story.append(
            Paragraph(
                html_escape(empresa.correo),
                estilo_datos,
            )
        )

    story.append(Spacer(1, 2.5 * mm))

    story.append(
        HRFlowable(
            width="100%",
            thickness=1.1,
            color=HexColor("#123B72"),
        )
    )

    story.append(Spacer(1, 2.5 * mm))

    # ========================================================
    # NUMERO / LUGAR / FECHA
    # ========================================================

    fecha_documento = (
        documento.fecha_documento
        or timezone.localdate()
    )

    fecha_texto = _fecha_documental_espanol(
        fecha_documento
    )

    ciudad = html_escape(
        empresa.ciudad or ""
    )

    meta = Table(
        [[
            Paragraph(
                html_escape(documento.numero or ""),
                estilo_numero,
            ),
            Paragraph(
                (
                    f"{ciudad}<br/>{fecha_texto}"
                    if ciudad
                    else fecha_texto
                ),
                estilo_fecha,
            ),
        ]],
        colWidths=[80 * mm, 96 * mm],
    )

    meta.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    story.append(meta)

    story.append(
        Paragraph(
            "<u>NOTA ACLARATORIA</u>",
            estilo_titulo,
        )
    )

    # ========================================================
    # DESTINATARIO
    # ========================================================

    destinatario = html_escape(
        documento.destinatario
        or "Instituto Nacional de Bienestar Estudiantil (INABIE)"
    )

    story.append(
        Paragraph(
            "Señores<br/>"
            f"<b>{destinatario}</b><br/>"
            "Su despacho.-<br/>"
            "Distinguidos señores:",
            estilo_destinatario,
        )
    )

    # ========================================================
    # PARSER DEL HTML EDITABLE
    # ========================================================

    class ParserDocumento(HTMLParser):

        def __init__(self):
            super().__init__()

            self.story = []

            self.tipo = None
            self.texto = []

            self.en_tabla = False
            self.tabla = []

            self.fila = None
            self.celda = None

        def _texto_actual(self):
            return "".join(self.texto).strip()

        def _cerrar_bloque(self):

            texto = self._texto_actual()

            if texto:

                if self.tipo in ("h1", "h2", "h3"):
                    estilo = estilo_seccion

                elif self.tipo == "li":
                    estilo = estilo_lista
                    texto = "• " + texto

                else:
                    estilo = estilo_cuerpo

                self.story.append(
                    Paragraph(
                        texto,
                        estilo,
                    )
                )

            self.tipo = None
            self.texto = []

        def handle_starttag(self, tag, attrs):

            tag = tag.lower()

            if tag in ("p", "h1", "h2", "h3", "li"):
                self._cerrar_bloque()
                self.tipo = tag
                return

            if tag == "br":
                self.texto.append("<br/>")
                return

            if tag in ("strong", "b"):
                self.texto.append("<b>")
                return

            if tag in ("em", "i"):
                self.texto.append("<i>")
                return

            if tag == "u":
                self.texto.append("<u>")
                return

            if tag == "table":
                self._cerrar_bloque()
                self.en_tabla = True
                self.tabla = []
                return

            if tag == "tr" and self.en_tabla:
                self.fila = []
                return

            if tag in ("th", "td") and self.en_tabla:

                self.celda = {
                    "tag": tag,
                    "texto": [],
                }

                return

        def handle_endtag(self, tag):

            tag = tag.lower()

            if tag in ("strong", "b"):
                self.texto.append("</b>")
                return

            if tag in ("em", "i"):
                self.texto.append("</i>")
                return

            if tag == "u":
                self.texto.append("</u>")
                return

            if tag in ("p", "h1", "h2", "h3", "li"):
                self._cerrar_bloque()
                return

            if (
                tag in ("th", "td")
                and self.en_tabla
                and self.celda is not None
            ):

                texto = "".join(
                    self.celda["texto"]
                ).strip()

                self.fila.append({
                    "tag": self.celda["tag"],
                    "texto": texto,
                })

                self.celda = None
                return

            if tag == "tr" and self.en_tabla:

                if self.fila:
                    self.tabla.append(
                        self.fila
                    )

                self.fila = None
                return

            if tag == "table" and self.en_tabla:
                self._cerrar_tabla()
                return

        def handle_data(self, data):

            seguro = html_escape(
                data,
                quote=False,
            )

            if (
                self.en_tabla
                and self.celda is not None
            ):
                self.celda["texto"].append(
                    seguro
                )

            else:
                self.texto.append(
                    seguro
                )

        def _cerrar_tabla(self):

            if not self.tabla:
                self.en_tabla = False
                return

            data = []

            for fila in self.tabla:

                fila_pdf = []

                for celda in fila:

                    estilo = (
                        estilo_tabla_centro
                        if celda.get("tag") == "th"
                        else estilo_tabla
                    )

                    fila_pdf.append(
                        Paragraph(
                            celda.get(
                                "texto",
                                "",
                            ),
                            estilo,
                        )
                    )

                data.append(
                    fila_pdf
                )

            # Ancho total aproximado: 520 pt
            col_widths = [
                47,   # Fecha
                47,   # No. conduce
                42,   # Codigo
                102,  # Centro
                52,   # Producto
                44,   # Cantidad
                186,  # Motivo
            ]

            tabla = Table(
                data,
                colWidths=col_widths,
                repeatRows=1,
                hAlign="CENTER",
            )

            tabla.setStyle(
                TableStyle([

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        HexColor("#123B72"),
                    ),

                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),

                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),

                    (
                        "ALIGN",
                        (0, 0),
                        (-1, 0),
                        "CENTER",
                    ),

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),

                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        HexColor("#7E8A9A"),
                    ),

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ])
            )

            self.story.append(
                Spacer(
                    1,
                    2 * mm,
                )
            )

            self.story.append(
                tabla
            )

            self.story.append(
                Spacer(
                    1,
                    3 * mm,
                )
            )

            self.tabla = []
            self.en_tabla = False

        def finalizar(self):

            self._cerrar_bloque()

            if self.en_tabla:
                self._cerrar_tabla()

            return self.story

    parser = ParserDocumento()

    contenido_pdf = documento.contenido_html or ""

    # --------------------------------------------------------
    # SEGURIDAD DOCUMENTAL EXTERNA
    # --------------------------------------------------------
    # Ninguna comunicación emitida debe revelar que fue
    # preparada mediante software o automatización.

    contenido_pdf = contenido_pdf.replace(
        "Los conduces relacionados anteriormente corresponden "
        "exclusivamente a anulaciones registradas en SASTRE por "
        "incidencias particulares de los centros educativos en las "
        "fechas indicadas.",
        "Los conduces relacionados anteriormente corresponden "
        "a anulaciones realizadas conforme a las incidencias "
        "particulares reportadas por los centros educativos en las "
        "fechas indicadas."
    )

    contenido_pdf = contenido_pdf.replace(
        "realizadas conforme a las incidencias particulares",
        "realizadas conforme a las incidencias particulares"
    )

    contenido_pdf = contenido_pdf.replace(
        "registrados en SASTRE por incidencias particulares",
        "realizados conforme a las incidencias particulares"
    )

    contenido_pdf = contenido_pdf.replace(
        "SASTRE ERP",
        ""
    )

    parser.feed(
        contenido_pdf
    )

    story.extend(
        parser.finalizar()
    )

    # ========================================================
    # CIERRE DOCUMENTAL
    # ========================================================
    #
    # Atentamente + firma + firmante + cargo + sello forman
    # una sola unidad visual.
    #
    # No utiliza:
    # - CondPageBreak
    # - KeepTogether
    # - tablas auxiliares
    #
    # Platypus decide naturalmente si el bloque cabe.
    #
    # Dimensiones institucionales:
    # - Firma: 60 x 21 mm
    # - Sello: 45 x 45 mm
    #
    # El sello aprovecha parcialmente el margen inferior
    # sin modificar los márgenes generales del documento.
    # ========================================================

    class CierreDocumentoFlowable(Flowable):

        def __init__(
            self,
            firma_path=None,
            sello_path=None,
            firmante="",
            cargo="",
        ):
            Flowable.__init__(self)

            self.firma_path = firma_path
            self.sello_path = sello_path
            self.firmante = firmante or ""
            self.cargo = cargo or ""

            # Altura lógica del cierre.
            #
            # Es suficiente para el texto y la firma.
            # El sello utiliza también una pequeña porción
            # del margen inferior sin afectar el flujo.
            self.height = 36 * mm
            self._avail_width = 0

        def wrap(self, availWidth, availHeight):

            self._avail_width = availWidth

            return (
                availWidth,
                self.height,
            )

        def draw(self):

            c = self.canv
            w = self._avail_width

            # ------------------------------------------------
            # POSICIONES GENERALES
            # ------------------------------------------------

            firma_centro_x = 72 * mm
            sello_centro_x = 143 * mm

            # ------------------------------------------------
            # ATENTAMENTE
            # ------------------------------------------------

            c.saveState()

            c.setFillColor(
                colors.black
            )

            c.setFont(
                "Helvetica",
                9.5,
            )

            c.drawString(
                0,
                32.5 * mm,
                "Atentamente,"
            )

            c.restoreState()

            # ------------------------------------------------
            # FIRMA GRAFICA
            # ------------------------------------------------

            if self.firma_path:

                firma_w = 60 * mm
                firma_h = 21 * mm

                firma_x = (
                    firma_centro_x
                    - firma_w / 2
                )

                firma_y = 9 * mm

                try:

                    c.drawImage(
                        self.firma_path,
                        firma_x,
                        firma_y,
                        width=firma_w,
                        height=firma_h,
                        preserveAspectRatio=True,
                        mask="auto",
                    )

                except Exception:
                    pass

            # ------------------------------------------------
            # LINEA DE FIRMA
            # ------------------------------------------------

            linea_w = 72 * mm

            linea_x1 = (
                firma_centro_x
                - linea_w / 2
            )

            linea_x2 = (
                firma_centro_x
                + linea_w / 2
            )

            linea_y = 7.5 * mm

            c.saveState()

            c.setStrokeColor(
                colors.black
            )

            c.setLineWidth(
                0.55
            )

            c.line(
                linea_x1,
                linea_y,
                linea_x2,
                linea_y,
            )

            c.restoreState()

            # ------------------------------------------------
            # NOMBRE DEL FIRMANTE
            # ------------------------------------------------

            if self.firmante:

                c.saveState()

                c.setFillColor(
                    colors.black
                )

                c.setFont(
                    "Helvetica-Bold",
                    9,
                )

                c.drawCentredString(
                    firma_centro_x,
                    4.2 * mm,
                    self.firmante,
                )

                c.restoreState()

            # ------------------------------------------------
            # CARGO
            # ------------------------------------------------

            if self.cargo:

                c.saveState()

                c.setFillColor(
                    colors.black
                )

                c.setFont(
                    "Helvetica",
                    8.5,
                )

                c.drawCentredString(
                    firma_centro_x,
                    1 * mm,
                    self.cargo,
                )

                c.restoreState()

            # ------------------------------------------------
            # SELLO INSTITUCIONAL
            # ------------------------------------------------

            if self.sello_path:

                sello_d = 45 * mm

                sello_x = (
                    sello_centro_x
                    - sello_d / 2
                )

                # El bloque mide 36 mm.
                # El sello utiliza 8 mm adicionales del margen
                # inferior, sin interferir con el texto.
                sello_y = -8 * mm

                try:

                    c.drawImage(
                        self.sello_path,
                        sello_x,
                        sello_y,
                        width=sello_d,
                        height=sello_d,
                        preserveAspectRatio=True,
                        mask="auto",
                    )

                except Exception:
                    pass


    # ========================================================
    # ARCHIVOS INSTITUCIONALES
    # ========================================================

    firma_path_cierre = None
    sello_path_cierre = None


    if documento.incluir_firma:

        firma_empresa = getattr(
            empresa,
            "firma_autorizada",
            None,
        )

        if firma_empresa:

            try:

                with firma_empresa.storage.open(
                    firma_empresa.name,
                    "rb",
                ) as archivo_firma:
                    firma_path_cierre = ImageReader(
                        BytesIO(
                            archivo_firma.read()
                        )
                    )

            except Exception:
                firma_path_cierre = None


    if documento.incluir_sello:

        sello_empresa = getattr(
            empresa,
            "sello_institucional",
            None,
        )

        if sello_empresa:

            try:

                with sello_empresa.storage.open(
                    sello_empresa.name,
                    "rb",
                ) as archivo_sello:
                    sello_path_cierre = ImageReader(
                        BytesIO(
                            archivo_sello.read()
                        )
                    )

            except Exception:
                sello_path_cierre = None


    # ========================================================
    # INCORPORAR CIERRE AL DOCUMENTO
    # ========================================================
    #
    # Sin CondPageBreak.
    #
    # Si quedan 36 mm o más, se coloca en la página actual.
    # Si realmente no caben, Platypus lo llevará a la siguiente.
    # ========================================================

    story.append(
        CierreDocumentoFlowable(
            firma_path=firma_path_cierre,
            sello_path=sello_path_cierre,
            firmante=documento.firmante,
            cargo=documento.cargo_firmante,
        )
    )

    # ========================================================
    # PAGINACION NEUTRA
    # ========================================================

    def pagina(canvas, document):

        canvas.saveState()

        canvas.setFont(
            "Helvetica",
            7,
        )

        canvas.setFillColor(
            HexColor("#6B7280")
        )

        canvas.drawCentredString(
            letter[0] / 2,
            8 * mm,
            f"Página {document.page}",
        )

        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=pagina,
        onLaterPages=pagina,
    )

    buffer.seek(0)

    return buffer



# ============================================================
# DOCUMENTOS INSTITUCIONALES - WORD EDITABLE
# ============================================================

def _html_externo_documento(valor):
    """
    Limpia referencias internas que no deben aparecer
    en un documento dirigido a terceros.
    """

    valor = _sanitizar_html_documento(valor or "")

    valor = valor.replace(
        "Los conduces relacionados anteriormente corresponden "
        "exclusivamente a anulaciones registradas en SASTRE por "
        "incidencias particulares de los centros educativos en las "
        "fechas indicadas.",
        "Los conduces relacionados anteriormente corresponden "
        "exclusivamente a anulaciones derivadas de incidencias "
        "particulares de los centros educativos en las fechas indicadas.",
    )

    valor = valor.replace(
        "registrados en SASTRE por incidencias particulares",
        "realizados conforme a las incidencias particulares",
    )

    valor = valor.replace(
        "SASTRE ERP",
        "",
    )

    return valor


def _word_datos_empresa(
    documento,
    empresa,
):
    snapshot = documento.datos_snapshot or {}

    historico = (
        snapshot.get("empresa_emision", {})
        or {}
    )

    if historico:
        return {
            "nombre": historico.get("nombre", "") or "",
            "rnc": historico.get("rnc", "") or "",
            "direccion": historico.get("direccion", "") or "",
            "telefono": historico.get("telefono", "") or "",
            "ciudad": historico.get("ciudad", "") or "",
            "correo": historico.get("correo", "") or "",
        }

    return {
        "nombre": getattr(empresa, "nombre", "") or "",
        "rnc": getattr(empresa, "rnc", "") or "",
        "direccion": getattr(empresa, "direccion", "") or "",
        "telefono": getattr(empresa, "telefono", "") or "",
        "ciudad": getattr(empresa, "ciudad", "") or "",
        "correo": getattr(empresa, "correo", "") or "",
    }


def _word_imagen_empresa(
    documento,
    empresa,
    tipo,
):
    """
    Prioriza el archivo utilizado al momento de emisión.
    Si no existe snapshot, utiliza la configuración actual.
    """

    from io import BytesIO
    from django.core.files.storage import default_storage

    snapshot = documento.datos_snapshot or {}

    firma_snapshot = (
        snapshot.get("firma_emision", {})
        or {}
    )

    mapa = {
        "logo": (
            "logo_archivo",
            "logo",
        ),
        "firma": (
            "firma_archivo",
            "firma_autorizada",
        ),
        "sello": (
            "sello_archivo",
            "sello_institucional",
        ),
    }

    clave_snapshot, campo_empresa = mapa[tipo]

    historico = (
        firma_snapshot.get(clave_snapshot)
        or ""
    )

    if historico:
        try:
            with default_storage.open(
                historico,
                "rb",
            ) as archivo:
                return BytesIO(
                    archivo.read()
                )
        except Exception:
            pass

    campo = getattr(
        empresa,
        campo_empresa,
        None,
    )

    if campo:
        try:
            with campo.storage.open(
                campo.name,
                "rb",
            ) as archivo:
                return BytesIO(
                    archivo.read()
                )
        except Exception:
            pass

    return None


class _DocumentoWordHTMLParser(HTMLParser):

    BLOQUES = {
        "p",
        "div",
        "h1",
        "h2",
        "h3",
        "blockquote",
        "li",
    }

    INLINE = {
        "strong",
        "b",
        "em",
        "i",
        "u",
        "span",
    }

    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.bloques = []

        self.parrafo = None

        self.tabla = None
        self.fila = None
        self.celda = None

        self.inline = []

        self.listas = []


    def _estilos(self, attrs):

        salida = {}

        attrs = dict(
            attrs or []
        )

        valor = (
            attrs.get("style", "")
            or ""
        )

        for regla in valor.split(";"):

            if ":" not in regla:
                continue

            clave, dato = regla.split(
                ":",
                1,
            )

            clave = clave.strip().lower()
            dato = dato.strip().lower()

            if clave == "text-align":
                salida["align"] = dato

            elif clave == "margin-left":
                match = re.fullmatch(
                    r"(\d+)px",
                    dato,
                )

                if match:
                    salida["margin_left"] = int(
                        match.group(1)
                    )

            elif clave == "font-size":
                match = re.fullmatch(
                    r"(\d+)px",
                    dato,
                )

                if match:
                    salida["font_size"] = int(
                        match.group(1)
                    )

        return salida


    def _formato_inline(self):

        formato = {
            "bold": False,
            "italic": False,
            "underline": False,
            "font_size": None,
        }

        for tag, attrs in self.inline:

            if tag in (
                "strong",
                "b",
            ):
                formato["bold"] = True

            elif tag in (
                "em",
                "i",
            ):
                formato["italic"] = True

            elif tag == "u":
                formato["underline"] = True

            estilos = self._estilos(
                attrs
            )

            if estilos.get("font_size"):
                formato["font_size"] = estilos[
                    "font_size"
                ]

        return formato


    def _nuevo_parrafo(
        self,
        tag="p",
        attrs=None,
    ):

        self._cerrar_parrafo()

        estilos = self._estilos(
            attrs or []
        )

        self.parrafo = {
            "tipo": "parrafo",
            "tag": tag,
            "align": estilos.get(
                "align"
            ),
            "margin_left": estilos.get(
                "margin_left",
                0,
            ),
            "font_size": estilos.get(
                "font_size"
            ),
            "runs": [],
        }

        if (
            tag == "li"
            and self.listas
        ):

            lista = self.listas[-1]

            if lista["tipo"] == "ol":
                lista["contador"] += 1

                prefijo = (
                    f'{lista["contador"]}. '
                )

            else:
                prefijo = "• "

            self.parrafo["runs"].append({
                "texto": prefijo,
                "bold": False,
                "italic": False,
                "underline": False,
                "font_size": None,
            })


    def _cerrar_parrafo(self):

        if not self.parrafo:
            return

        texto = "".join(
            run.get("texto", "")
            for run
            in self.parrafo["runs"]
        )

        if texto.strip():

            if self.celda is not None:

                self.celda.setdefault(
                    "parrafos",
                    [],
                ).append(
                    self.parrafo
                )

            else:

                self.bloques.append(
                    self.parrafo
                )

        self.parrafo = None


    def _texto(self, valor):

        if not valor:
            return

        if (
            not valor.strip()
            and self.parrafo is None
        ):
            return

        if self.parrafo is None:
            self._nuevo_parrafo(
                "p",
                [],
            )

        formato = (
            self._formato_inline()
        )

        self.parrafo["runs"].append({
            "texto": valor,
            **formato,
        })


    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        tag = tag.lower()

        if tag == "table":

            self._cerrar_parrafo()

            self.tabla = {
                "tipo": "tabla",
                "filas": [],
            }

            return

        if tag == "tr":

            self._cerrar_parrafo()

            self.fila = []

            return

        if tag in (
            "th",
            "td",
        ):

            self._cerrar_parrafo()

            self.celda = {
                "header": (
                    tag == "th"
                ),
                "parrafos": [],
            }

            self._nuevo_parrafo(
                "p",
                attrs,
            )

            return

        if tag in (
            "ul",
            "ol",
        ):

            self._cerrar_parrafo()

            self.listas.append({
                "tipo": tag,
                "contador": 0,
            })

            return

        if tag in self.BLOQUES:

            self._nuevo_parrafo(
                tag,
                attrs,
            )

            return

        if tag == "br":

            self._texto("\n")

            return

        if tag in self.INLINE:

            self.inline.append(
                (
                    tag,
                    attrs,
                )
            )


    def handle_endtag(
        self,
        tag,
    ):

        tag = tag.lower()

        if tag in self.INLINE:

            for indice in range(
                len(self.inline) - 1,
                -1,
                -1,
            ):

                if (
                    self.inline[indice][0]
                    == tag
                ):

                    self.inline.pop(
                        indice
                    )

                    break

            return

        if tag in self.BLOQUES:

            self._cerrar_parrafo()

            return

        if tag in (
            "ul",
            "ol",
        ):

            self._cerrar_parrafo()

            if self.listas:
                self.listas.pop()

            return

        if tag in (
            "th",
            "td",
        ):

            self._cerrar_parrafo()

            if (
                self.fila is not None
                and self.celda is not None
            ):

                self.fila.append(
                    self.celda
                )

            self.celda = None

            return

        if tag == "tr":

            self._cerrar_parrafo()

            if (
                self.tabla is not None
                and self.fila is not None
            ):

                self.tabla["filas"].append(
                    self.fila
                )

            self.fila = None

            return

        if tag == "table":

            self._cerrar_parrafo()

            if self.tabla is not None:

                self.bloques.append(
                    self.tabla
                )

            self.tabla = None


    def handle_data(
        self,
        data,
    ):

        self._texto(
            data
        )


    def finalizar(self):

        self._cerrar_parrafo()

        return self.bloques


def _word_quitar_bordes_tabla(
    table,
):

    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    tbl_pr = table._tbl.tblPr

    bordes = OxmlElement(
        "w:tblBorders"
    )

    for lado in (
        "top",
        "left",
        "bottom",
        "right",
        "insideH",
        "insideV",
    ):

        elemento = OxmlElement(
            f"w:{lado}"
        )

        elemento.set(
            qn("w:val"),
            "nil",
        )

        bordes.append(
            elemento
        )

    tbl_pr.append(
        bordes
    )


def _word_sombrear_celda(
    cell,
    fill,
):

    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    tc_pr = (
        cell._tc.get_or_add_tcPr()
    )

    shd = OxmlElement(
        "w:shd"
    )

    shd.set(
        qn("w:fill"),
        fill,
    )

    tc_pr.append(
        shd
    )


def _word_borde_inferior(
    paragraph,
):

    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    p_pr = (
        paragraph._p.get_or_add_pPr()
    )

    p_bdr = OxmlElement(
        "w:pBdr"
    )

    bottom = OxmlElement(
        "w:bottom"
    )

    bottom.set(
        qn("w:val"),
        "single",
    )

    bottom.set(
        qn("w:sz"),
        "6",
    )

    bottom.set(
        qn("w:space"),
        "1",
    )

    bottom.set(
        qn("w:color"),
        "000000",
    )

    p_bdr.append(
        bottom
    )

    p_pr.append(
        p_bdr
    )


def _word_agregar_runs(
    paragraph,
    node,
    default_size=10.5,
    color=None,
):

    from docx.shared import Pt, RGBColor

    for item in node.get(
        "runs",
        [],
    ):

        texto = item.get(
            "texto",
            "",
        )

        if not texto:
            continue

        run = paragraph.add_run(
            texto
        )

        run.bold = bool(
            item.get("bold")
        )

        run.italic = bool(
            item.get("italic")
        )

        run.underline = bool(
            item.get("underline")
        )

        px = (
            item.get("font_size")
            or node.get("font_size")
        )

        if px:

            size = max(
                8,
                min(
                    24,
                    float(px) * 0.75,
                ),
            )

        else:

            size = default_size

        run.font.size = Pt(
            size
        )

        run.font.name = (
            "Times New Roman"
        )

        if color:

            run.font.color.rgb = RGBColor(
                *color
            )


def _docx_documento_institucional(
    documento,
    empresa,
):

    from io import BytesIO

    from docx import Document
    from docx.shared import (
        Mm,
        Pt,
        RGBColor,
    )

    from docx.enum.text import (
        WD_ALIGN_PARAGRAPH,
    )

    from docx.enum.table import (
        WD_TABLE_ALIGNMENT,
        WD_CELL_VERTICAL_ALIGNMENT,
    )

    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    salida = BytesIO()

    doc = Document()

    section = doc.sections[0]

    # Carta 8.5 x 11
    section.page_width = Mm(
        215.9
    )

    section.page_height = Mm(
        279.4
    )

    section.left_margin = Mm(
        16
    )

    section.right_margin = Mm(
        16
    )

    section.top_margin = Mm(
        12
    )

    section.bottom_margin = Mm(
        16
    )

    section.footer_distance = Mm(
        7
    )


    # --------------------------------------------------------
    # ESTILO GENERAL
    # --------------------------------------------------------

    normal = doc.styles[
        "Normal"
    ]

    normal.font.name = (
        "Times New Roman"
    )

    normal.font.size = Pt(
        10.5
    )

    normal._element.rPr.rFonts.set(
        qn("w:eastAsia"),
        "Times New Roman",
    )


    datos_empresa = (
        _word_datos_empresa(
            documento,
            empresa,
        )
    )


    # --------------------------------------------------------
    # LOGO
    # --------------------------------------------------------

    logo = _word_imagen_empresa(
        documento,
        empresa,
        "logo",
    )

    if logo:

        p = doc.add_paragraph()

        p.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        p.paragraph_format.space_after = Pt(
            1
        )

        run = p.add_run()

        run.add_picture(
            logo,
            width=Mm(45),
        )


    # --------------------------------------------------------
    # NOMBRE EMPRESA
    # --------------------------------------------------------

    p = doc.add_paragraph()

    p.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    p.paragraph_format.space_after = Pt(
        1
    )

    run = p.add_run(
        (
            datos_empresa[
                "nombre"
            ]
            or ""
        ).upper()
    )

    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(
        11.5
    )


    if datos_empresa[
        "direccion"
    ]:

        p = doc.add_paragraph()

        p.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        p.paragraph_format.space_after = Pt(
            0
        )

        run = p.add_run(
            datos_empresa[
                "direccion"
            ]
        )

        run.font.size = Pt(
            9
        )


    datos_contacto = []

    if datos_empresa[
        "telefono"
    ]:

        datos_contacto.append(
            "Teléfono: "
            + datos_empresa[
                "telefono"
            ]
        )

    if datos_empresa[
        "rnc"
    ]:

        datos_contacto.append(
            "RNC: "
            + datos_empresa[
                "rnc"
            ]
        )

    if datos_contacto:

        p = doc.add_paragraph()

        p.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        p.paragraph_format.space_after = Pt(
            5
        )

        run = p.add_run(
            "    ·    ".join(
                datos_contacto
            )
        )

        run.font.size = Pt(
            9
        )


    # --------------------------------------------------------
    # NUMERO + FECHA
    # --------------------------------------------------------

    meta = doc.add_table(
        rows=1,
        cols=2,
    )

    meta.autofit = False

    meta.alignment = (
        WD_TABLE_ALIGNMENT.CENTER
    )

    _word_quitar_bordes_tabla(
        meta
    )

    meta.cell(
        0,
        0,
    ).width = Mm(
        91
    )

    meta.cell(
        0,
        1,
    ).width = Mm(
        91
    )


    p = meta.cell(
        0,
        0,
    ).paragraphs[0]

    p.alignment = (
        WD_ALIGN_PARAGRAPH.LEFT
    )

    run = p.add_run(
        documento.numero
        or ""
    )

    run.bold = True
    run.font.size = Pt(
        9
    )


    p = meta.cell(
        0,
        1,
    ).paragraphs[0]

    p.alignment = (
        WD_ALIGN_PARAGRAPH.RIGHT
    )

    fecha_texto = (
        _fecha_documental_espanol(
            documento.fecha_documento
        )
    )

    if datos_empresa[
        "ciudad"
    ]:

        fecha_texto = (
            datos_empresa[
                "ciudad"
            ]
            + ", "
            + fecha_texto
        )

    run = p.add_run(
        fecha_texto
    )

    run.font.size = Pt(
        9.5
    )


    # --------------------------------------------------------
    # TITULO
    # --------------------------------------------------------

    p = doc.add_paragraph()

    p.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    p.paragraph_format.space_before = Pt(
        8
    )

    p.paragraph_format.space_after = Pt(
        8
    )

    run = p.add_run(
        (
            documento.get_tipo_display()
            or "Documento institucional"
        ).upper()
    )

    run.bold = True
    run.underline = True
    run.font.name = "Arial"
    run.font.size = Pt(
        11
    )


    # --------------------------------------------------------
    # DESTINATARIO
    # --------------------------------------------------------

    if documento.destinatario:

        p = doc.add_paragraph()

        p.paragraph_format.space_after = Pt(
            7
        )

        run = p.add_run(
            "Señores:\n"
        )

        run.bold = True

        run = p.add_run(
            documento.destinatario
        )

        run.bold = True


    # --------------------------------------------------------
    # CONTENIDO HTML
    # --------------------------------------------------------

    parser = (
        _DocumentoWordHTMLParser()
    )

    parser.feed(
        _html_externo_documento(
            documento.contenido_html
        )
    )

    parser.close()

    bloques = parser.finalizar()


    mapa_alineacion = {
        "left": (
            WD_ALIGN_PARAGRAPH.LEFT
        ),
        "center": (
            WD_ALIGN_PARAGRAPH.CENTER
        ),
        "right": (
            WD_ALIGN_PARAGRAPH.RIGHT
        ),
        "justify": (
            WD_ALIGN_PARAGRAPH.JUSTIFY
        ),
    }


    for node in bloques:

        if (
            node.get("tipo")
            == "parrafo"
        ):

            p = doc.add_paragraph()

            tag = node.get(
                "tag",
                "p",
            )

            if node.get(
                "align"
            ):

                p.alignment = (
                    mapa_alineacion.get(
                        node["align"],
                        WD_ALIGN_PARAGRAPH.JUSTIFY,
                    )
                )

            elif tag in (
                "h1",
                "h2",
                "h3",
            ):

                p.alignment = (
                    WD_ALIGN_PARAGRAPH.LEFT
                )

            else:

                p.alignment = (
                    WD_ALIGN_PARAGRAPH.JUSTIFY
                )


            if node.get(
                "margin_left"
            ):

                p.paragraph_format.left_indent = Pt(
                    node[
                        "margin_left"
                    ]
                    * 0.75
                )


            if tag in (
                "h1",
                "h2",
                "h3",
            ):

                p.paragraph_format.space_before = Pt(
                    5
                )

                p.paragraph_format.space_after = Pt(
                    3
                )

                p.paragraph_format.keep_with_next = True

            else:

                p.paragraph_format.space_after = Pt(
                    5
                )


            if tag == "h1":
                size = 14

            elif tag == "h2":
                size = 12

            elif tag == "h3":
                size = 10.5

            else:
                size = 10.5


            _word_agregar_runs(
                p,
                node,
                default_size=size,
            )


            if tag in (
                "h1",
                "h2",
                "h3",
            ):

                for run in p.runs:

                    run.bold = True
                    run.font.name = "Arial"


        elif (
            node.get("tipo")
            == "tabla"
        ):

            filas = node.get(
                "filas",
                [],
            )

            if not filas:
                continue

            columnas = max(
                len(fila)
                for fila in filas
            )

            tabla = doc.add_table(
                rows=len(filas),
                cols=columnas,
            )

            tabla.style = (
                "Table Grid"
            )

            tabla.alignment = (
                WD_TABLE_ALIGNMENT.CENTER
            )

            tabla.autofit = True


            for i, fila in enumerate(
                filas
            ):

                for j, cell_node in enumerate(
                    fila
                ):

                    cell = tabla.cell(
                        i,
                        j,
                    )

                    cell.vertical_alignment = (
                        WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    )

                    es_header = bool(
                        cell_node.get(
                            "header"
                        )
                    )

                    if es_header:

                        _word_sombrear_celda(
                            cell,
                            "174A7E",
                        )


                    parrafos = (
                        cell_node.get(
                            "parrafos",
                            [],
                        )
                    )

                    if not parrafos:
                        continue


                    for indice, node_p in enumerate(
                        parrafos
                    ):

                        if indice == 0:

                            p = (
                                cell.paragraphs[0]
                            )

                        else:

                            p = (
                                cell.add_paragraph()
                            )


                        p.alignment = (
                            WD_ALIGN_PARAGRAPH.CENTER
                            if es_header
                            else WD_ALIGN_PARAGRAPH.LEFT
                        )

                        p.paragraph_format.space_after = Pt(
                            0
                        )


                        _word_agregar_runs(
                            p,
                            node_p,
                            default_size=7.5,
                            color=(
                                (255, 255, 255)
                                if es_header
                                else None
                            ),
                        )


                        for run in p.runs:

                            run.font.size = Pt(
                                7.5
                            )

                            if es_header:

                                run.bold = True
                                run.font.name = "Arial"


            p = doc.add_paragraph()

            p.paragraph_format.space_after = Pt(
                0
            )


    # --------------------------------------------------------
    # CIERRE
    # --------------------------------------------------------

    p = doc.add_paragraph()

    p.paragraph_format.space_before = Pt(
        5
    )

    p.paragraph_format.space_after = Pt(
        4
    )

    run = p.add_run(
        "Atentamente,"
    )

    run.font.size = Pt(
        10.5
    )


    cierre = doc.add_table(
        rows=1,
        cols=2,
    )

    cierre.autofit = False

    cierre.alignment = (
        WD_TABLE_ALIGNMENT.CENTER
    )

    _word_quitar_bordes_tabla(
        cierre
    )


    cell_firma = cierre.cell(
        0,
        0,
    )

    cell_sello = cierre.cell(
        0,
        1,
    )


    cell_firma.width = Mm(
        115
    )

    cell_sello.width = Mm(
        55
    )


    cell_firma.vertical_alignment = (
        WD_CELL_VERTICAL_ALIGNMENT.BOTTOM
    )

    cell_sello.vertical_alignment = (
        WD_CELL_VERTICAL_ALIGNMENT.CENTER
    )


    # --------------------------------------------------------
    # FIRMA
    # --------------------------------------------------------

    p = cell_firma.paragraphs[
        0
    ]

    p.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    p.paragraph_format.space_after = Pt(
        0
    )


    if documento.incluir_firma:

        firma = _word_imagen_empresa(
            documento,
            empresa,
            "firma",
        )

        if firma:

            run = p.add_run()

            run.add_picture(
                firma,
                width=Mm(60),
            )


    # Línea física aproximadamente 72 mm.
    linea = cell_firma.add_paragraph()

    linea.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    linea.paragraph_format.left_indent = Mm(
        20
    )

    linea.paragraph_format.right_indent = Mm(
        20
    )

    linea.paragraph_format.space_before = Pt(
        0
    )

    linea.paragraph_format.space_after = Pt(
        2
    )

    _word_borde_inferior(
        linea
    )


    if documento.firmante:

        p = cell_firma.add_paragraph()

        p.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        p.paragraph_format.space_after = Pt(
            0
        )

        run = p.add_run(
            documento.firmante
        )

        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(
            9
        )


    if documento.cargo_firmante:

        p = cell_firma.add_paragraph()

        p.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        p.paragraph_format.space_after = Pt(
            0
        )

        run = p.add_run(
            documento.cargo_firmante
        )

        run.font.size = Pt(
            9
        )


    # --------------------------------------------------------
    # SELLO
    # --------------------------------------------------------

    p = cell_sello.paragraphs[
        0
    ]

    p.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )


    if documento.incluir_sello:

        sello = _word_imagen_empresa(
            documento,
            empresa,
            "sello",
        )

        if sello:

            run = p.add_run()

            run.add_picture(
                sello,
                width=Mm(45),
            )


    # --------------------------------------------------------
    # PIE DE PAGINA
    # --------------------------------------------------------

    footer = section.footer

    p = footer.paragraphs[
        0
    ]

    p.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )


    run = p.add_run(
        "Página "
    )

    run.font.name = "Arial"
    run.font.size = Pt(
        7
    )


    field = OxmlElement(
        "w:fldSimple"
    )

    field.set(
        qn("w:instr"),
        "PAGE",
    )

    p._p.append(
        field
    )


    # --------------------------------------------------------
    # METADATOS NEUTROS
    # --------------------------------------------------------

    doc.core_properties.title = (
        documento.asunto
        or documento.get_tipo_display()
    )

    doc.core_properties.subject = (
        documento.numero
        or ""
    )

    doc.core_properties.author = (
        datos_empresa[
            "nombre"
        ]
    )

    doc.core_properties.keywords = (
        "documento institucional"
    )


    doc.save(
        salida
    )

    salida.seek(
        0
    )

    return salida


def _contenido_docx_documento_institucional(
    documento,
    empresa,
):

    # Documento emitido:
    # usar siempre el Word histórico si ya existe.
    if (
        documento.estado
        in (
            DocumentoInstitucional.Estado.FINALIZADO,
            DocumentoInstitucional.Estado.ANULADO,
        )
        and documento.docx_final
    ):

        try:

            documento.docx_final.open(
                "rb"
            )

            return (
                documento.docx_final.read()
            )

        finally:

            try:
                documento.docx_final.close()
            except Exception:
                pass


    buffer = (
        _docx_documento_institucional(
            documento,
            empresa,
        )
    )

    contenido = (
        buffer.getvalue()
    )


    # Compatibilidad:
    # documentos emitidos antes de incorporar Word
    # se congelan al descargarse por primera vez.
    if (
        documento.estado
        in (
            DocumentoInstitucional.Estado.FINALIZADO,
            DocumentoInstitucional.Estado.ANULADO,
        )
        and not documento.docx_final
    ):

        try:

            from django.core.files.base import ContentFile

            documento.docx_final.save(
                f"{documento.numero}.docx",
                ContentFile(
                    contenido
                ),
                save=False,
            )

            documento.save(
                update_fields=[
                    "docx_final",
                ]
            )

        except Exception:
            pass


    return contenido


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
def descargar_word_documento_institucional(
    request,
    documento_id,
):

    empresa = obtener_empresa(
        request
    )

    documento = (
        documento_get_object_or_404(
            DocumentoInstitucional,
            id=documento_id,
            empresa=empresa,
            eliminado_en__isnull=True,
        )
    )

    contenido = (
        _contenido_docx_documento_institucional(
            documento,
            empresa,
        )
    )

    response = HttpResponse(
        contenido,
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; filename="{documento.numero}.docx"'
    )

    return response


def _contenido_pdf_documento_institucional(
    documento,
    empresa,
):
    """
    FINALIZADO / ANULADO:
        devuelve el PDF histórico almacenado.

    BORRADOR:
        genera una vista dinámica.
    """

    if (
        documento.estado
        in (
            DocumentoInstitucional.Estado.FINALIZADO,
            DocumentoInstitucional.Estado.ANULADO,
        )
        and documento.pdf_final
    ):
        try:
            documento.pdf_final.open("rb")
            return documento.pdf_final.read()
        finally:
            try:
                documento.pdf_final.close()
            except Exception:
                pass

    pdf_buffer = _pdf_documento_institucional(
        documento,
        empresa,
    )

    contenido = pdf_buffer.getvalue()

    # Compatibilidad con documentos finalizados antes
    # de incorporar almacenamiento histórico del PDF.
    if (
        documento.estado
        in (
            DocumentoInstitucional.Estado.FINALIZADO,
            DocumentoInstitucional.Estado.ANULADO,
        )
        and not documento.pdf_final
    ):
        try:
            from django.core.files.base import ContentFile

            documento.pdf_final.save(
                f"{documento.numero}.pdf",
                ContentFile(contenido),
                save=False,
            )

            documento.save(
                update_fields=[
                    "pdf_final",
                ]
            )
        except Exception:
            pass

    return contenido


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
def ver_pdf_documento_institucional(
    request,
    documento_id,
):
    empresa = obtener_empresa(request)

    documento = documento_get_object_or_404(
        DocumentoInstitucional,
        id=documento_id,
        empresa=empresa,
        eliminado_en__isnull=True,
    )

    pdf_bytes = _contenido_pdf_documento_institucional(
        documento,
        empresa,
    )

    response = HttpResponse(
        pdf_bytes,
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        f'inline; filename="{documento.numero}.pdf"'
    )

    return response


@login_required(login_url="login_usuario")
@modulo_requerido("modulo_reportes")
@suscripcion_requerida
def descargar_pdf_documento_institucional(
    request,
    documento_id,
):
    empresa = obtener_empresa(request)

    documento = documento_get_object_or_404(
        DocumentoInstitucional,
        id=documento_id,
        empresa=empresa,
        eliminado_en__isnull=True,
    )

    pdf_bytes = _contenido_pdf_documento_institucional(
        documento,
        empresa,
    )

    response = HttpResponse(
        pdf_bytes,
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{documento.numero}.pdf"'
    )

    return response



# ===== FIN MOTOR DOCUMENTAL SASTRE 02 =====


# =====================================================
# ESTADO DE CUENTA / SUSCRIPCIÓN
# =====================================================
@login_required(login_url="login_usuario")
def cuenta_estado(request):
    from .subscription_service import (
        suscripcion_permite_acceso_request,
    )
    from .tenant_context import (
        contexto_soporte_activo,
        obtener_empresa_saas_request,
    )

    empresa_saas = obtener_empresa_saas_request(
        request,
        permitir_soporte=True,
    )

    suscripcion = (
        getattr(
            empresa_saas,
            "suscripcion",
            None,
        )
        if empresa_saas
        else None
    )

    contexto = {
        "empresa_saas": empresa_saas,
        "suscripcion": suscripcion,
        "tiene_acceso": (
            suscripcion_permite_acceso_request(
                request
            )
        ),
        "en_prueba": bool(
            suscripcion
            and suscripcion.esta_en_prueba()
        ),
        "dias_restantes": (
            suscripcion.dias_restantes_prueba()
            if suscripcion
            else 0
        ),
        "modo_soporte": contexto_soporte_activo(request),
    }

    return render(
        request,
        "cuenta_estado.html",
        contexto,
    )
