from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

from catalogos.models import MonedaEmpresa
from comercial.models_o2c4 import CesionFactoring, CuentaPorCobrar
from compras.application.financial import aprobar_solicitud_y_orden, crear_solicitud_pago, pagar_orden
from compras.models import Proveedor
from contabilidad.models import CuentaPorPagarEnterprise, FacturaProveedor, SolicitudPago
from core.application.operation_context import OperationContext
from core.models import EventoDominio
from tesoreria.models import ConciliacionBancaria, CuentaBancariaEmpresa, FlujoCajaProyectado, MovimientoTesoreria
from conduces.services import obtener_empresa_usuario


MODULES = {
    "ventas": ("Venta General", "Clientes, cotizaciones, pedidos, facturación, cobros y entregas.", [
        ("Clientes", "Gestión y expediente 360", "comercial:clientes_lista"), ("Cotizaciones", "Propuestas comerciales", "comercial:cotizaciones_lista"),
        ("Pedidos y ventas", "Ciclo comercial", "comercial:pedidos_lista"), ("Facturación", "Emisión y documentos", "facturacion"),
        ("Cuentas por cobrar", "Saldos, aging y cobros", "core:enterprise_cxc"), ("Rutas y entregas", "Conduces y despachos", "buscar_conduces"),
        ("Reportes", "Indicadores comerciales", "comercial:o2c_reportes")]),
    "inabie": ("Gestión INABIE", "Centros, menús, recetas, entregas, relaciones y facturación.", [
        ("Centros educativos", "Matrícula, raciones y ubicación", "lista_centros"), ("Menús", "Programación alimentaria", "carga_menu"),
        ("Recetas", "Composición y costos", "inventario:recetas_lista"), ("Conduces y entregas", "Evidencia operativa", "buscar_conduces"),
        ("Relaciones", "Relaciones diarias y generales", "buscar_conduces"), ("Facturación INABIE", "Facturas y comprobantes", "facturacion"),
        ("Mapa y rutas", "Cobertura geográfica", "mapa_centros"), ("Reportes", "Resumen INABIE", "core:actividad")]),
    "inventario": ("Inventario y Producción", "Existencias, movimientos, producción y necesidades.", [
        ("Productos y materias primas", "Catálogo operativo", "inventario:productos"), ("Inventario", "Disponibilidad y alertas", "inventario:dashboard"),
        ("Entradas y salidas", "Movimientos trazables", "inventario:movimientos"), ("Producción", "Órdenes y avance", "inventario:produccion_dashboard"),
        ("Necesidades de materiales", "Requerimientos", "inventario:necesidades_materia_prima"), ("Recetas de producción", "Fórmulas versionadas", "inventario:recetas_lista"),
        ("Reportes", "Inventario y producción", "inventario:dashboard")]),
    "administracion": ("Administración", "Configuración, seguridad, secuencias y auditoría.", [
        ("Empresa", "Datos y preferencias", "mi_empresa"), ("Usuarios", "Accesos de la empresa", "mi_empresa"),
        ("Roles y permisos", "Seguridad por función", "core:motor_dashboard"), ("Sucursales y lugares", "Estructura operativa", "catalogos:centro"),
        ("Numeraciones", "Secuencias documentales", "core:secuencias"), ("Plantillas", "Documentos corporativos", "rrhh:documentos_centro"),
        ("Parámetros", "Catálogos empresariales", "catalogos:centro"), ("Auditoría", "Eventos y trazabilidad", "core:motor_dashboard")]),
}


def _empresa(request):
    return obtener_empresa_usuario(request)


def _ctx(request):
    return OperationContext(empresa=_empresa(request), usuario=request.user, request=request, clave_idempotente=request.headers.get("Idempotency-Key") or f"enterprise:{request.path}:{timezone.now().timestamp()}")


def _audit(request, action, obj, before=None, after=None):
    EventoDominio.objects.create(empresa=_empresa(request), tipo_evento=f"Enterprise{action}", agregado_tipo=obj._meta.label, agregado_id=str(obj.pk), referencia=str(obj), clave_idempotente=f"web:{action}:{obj._meta.label_lower}:{obj.pk}:{timezone.now().timestamp()}", payload={"schema_version": 1, "antes": before or {}, "despues": after or {}}, estado="PROCESADO", creado_por=request.user)


@login_required
def module_hub(request, module):
    if module not in MODULES:
        return HttpResponse(status=404)
    title, description, cards = MODULES[module]
    return render(request, "core/enterprise/module_hub.html", {"empresa": _empresa(request), "module": module, "title": title, "description": description, "cards": cards})


@login_required
def finance_dashboard(request):
    e = _empresa(request); today = timezone.localdate(); month = today.replace(day=1)
    cxp = CuentaPorPagarEnterprise.objects.filter(empresa=e, saldo__gt=0)
    cxc = CuentaPorCobrar.objects.filter(empresa=e, saldo__gt=0)
    banks = CuentaBancariaEmpresa.objects.filter(empresa=e, activa=True)
    projected = FlujoCajaProyectado.objects.filter(empresa=e, fecha__gte=today).aggregate(v=Sum("monto"))["v"] or 0
    kpis = [("Cuentas por cobrar", cxc.aggregate(v=Sum("saldo"))["v"] or 0), ("Cuentas por pagar", cxp.aggregate(v=Sum("saldo"))["v"] or 0), ("Saldo bancos", banks.aggregate(v=Sum("saldo"))["v"] or 0), ("Pagos próximos", SolicitudPago.objects.filter(empresa=e, fecha_prevista__range=(today, today + timedelta(days=30))).aggregate(v=Sum("monto"))["v"] or 0), ("Facturas vencidas", cxp.filter(vence_el__lt=today).count()), ("Flujo proyectado", projected)]
    return render(request, "core/enterprise/finance_dashboard.html", {"empresa": e, "kpis": kpis})


def _aging(qs):
    groups = ((["CORRIENTE", "1_30"], "0-30 días"), (["31_60"], "31-60"), (["61_90"], "61-90"), (["91_120"], "91-120"), (["MAS_120"], "Más de 120"))
    return [(label, qs.filter(bucket_aging__in=keys).aggregate(v=Sum("saldo"))["v"] or 0) for keys, label in groups]


@login_required
@permission_required("contabilidad.view_cuentaporpagarenterprise", raise_exception=True)
def cxp_list(request):
    e = _empresa(request); qs = CuentaPorPagarEnterprise.objects.filter(empresa=e).select_related("proveedor", "factura", "moneda__moneda")
    for field in ("estado", "proveedor"):
        value = request.GET.get(field)
        if value: qs = qs.filter(**{f"{field}_id" if field == "proveedor" else field: value})
    today = timezone.localdate(); open_qs = qs.filter(saldo__gt=0)
    for item in qs:
        item.pagado_calculado = item.monto_original - item.saldo
        item.dias_vencidos = max(0, (today - item.vence_el).days)
    kpis = [("Total por pagar", open_qs.aggregate(v=Sum("saldo"))["v"] or 0), ("Vencido", open_qs.filter(vence_el__lt=today).aggregate(v=Sum("saldo"))["v"] or 0), ("Por vencer", open_qs.filter(vence_el__gte=today).aggregate(v=Sum("saldo"))["v"] or 0), ("Facturas pendientes", open_qs.count()), ("Pagos del mes", MovimientoTesoreria.objects.filter(empresa=e, tipo="EGRESO", fecha__gte=today.replace(day=1)).aggregate(v=Sum("monto"))["v"] or 0)]
    return render(request, "core/enterprise/cxp_list.html", {"empresa": e, "cuentas": sorted(qs, key=lambda item: (item.vence_el, item.pk)), "proveedores": Proveedor.objects.filter(empresa=e), "kpis": kpis, "aging": _aging(open_qs), "today": today})


@login_required
@permission_required("contabilidad.view_cuentaporpagarenterprise", raise_exception=True)
def cxp_detail(request, pk):
    obj = get_object_or_404(CuentaPorPagarEnterprise.objects.select_related("factura", "proveedor", "moneda__moneda").prefetch_related("movimientos", "factura__detalles"), pk=pk, empresa=_empresa(request))
    return render(request, "core/enterprise/cxp_detail.html", {"empresa": _empresa(request), "obj": obj})


@login_required
@permission_required("contabilidad.add_solicitudpago", raise_exception=True)
def payment_create(request, pk=None):
    e = _empresa(request); accounts = CuentaPorPagarEnterprise.objects.filter(empresa=e, saldo__gt=0, bloqueada=False).select_related("proveedor", "factura"); banks = CuentaBancariaEmpresa.objects.filter(empresa=e, activa=True)
    selected = get_object_or_404(accounts, pk=pk) if pk else None
    if request.method == "POST":
        account = get_object_or_404(accounts, pk=request.POST.get("cuenta")); amount = Decimal(request.POST.get("monto", "0")); bank = get_object_or_404(banks, pk=request.POST.get("cuenta_bancaria"))
        try:
            with transaction.atomic():
                solicitud = crear_solicitud_pago(context=_ctx(request), cuenta_id=account.pk, monto=amount)
                orden = aprobar_solicitud_y_orden(context=_ctx(request), solicitud_id=solicitud.pk)
                pagar_orden(context=_ctx(request), orden_id=orden.pk, cuenta_bancaria=bank, monto=amount, referencia=request.POST.get("referencia", ""), metodo=request.POST.get("metodo", "TRANSFERENCIA"))
                _audit(request, "PagoRegistrado", orden, after={"monto": str(amount), "cuenta": account.pk})
            return redirect("core:enterprise_cxp_detail", pk=account.pk)
        except (ValidationError, ValueError) as exc:
            return render(request, "core/enterprise/payment_form.html", {"empresa": e, "cuentas": accounts, "banks": banks, "selected": account, "error": "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)}, status=400)
    return render(request, "core/enterprise/payment_form.html", {"empresa": e, "cuentas": accounts, "banks": banks, "selected": selected})


@login_required
@permission_required("contabilidad.add_solicitudpago", raise_exception=True)
def payment_multiple(request):
    e = _empresa(request); accounts = CuentaPorPagarEnterprise.objects.filter(empresa=e, saldo__gt=0, bloqueada=False).select_related("proveedor", "factura"); banks = CuentaBancariaEmpresa.objects.filter(empresa=e, activa=True)
    if request.method == "POST":
        bank = get_object_or_404(banks, pk=request.POST.get("cuenta_bancaria")); selected = accounts.filter(pk__in=request.POST.getlist("cuentas")); expected_total = Decimal(request.POST.get("monto_total", "0")); applications = []
        try:
            for account in selected:
                amount = Decimal(request.POST.get(f"monto_{account.pk}", "0"))
                if amount > 0: applications.append((account, amount))
            applied = sum((amount for _, amount in applications), Decimal("0"))
            if not applications or applied > expected_total: raise ValidationError("La suma aplicada debe ser positiva y no exceder el monto total del pago.")
            with transaction.atomic():
                for account, amount in applications:
                    solicitud = crear_solicitud_pago(context=_ctx(request), cuenta_id=account.pk, monto=amount); orden = aprobar_solicitud_y_orden(context=_ctx(request), solicitud_id=solicitud.pk); pagar_orden(context=_ctx(request), orden_id=orden.pk, cuenta_bancaria=bank, monto=amount, referencia=request.POST.get("referencia", ""))
                _audit(request, "PagoMultipleRegistrado", applications[0][0], after={"monto_total": str(applied), "facturas": [account.pk for account, _ in applications]})
            return redirect("core:enterprise_cxp")
        except (ValidationError, ValueError) as exc:
            return render(request, "core/enterprise/payment_multiple.html", {"empresa": e, "cuentas": accounts, "banks": banks, "error": "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)}, status=400)
    return render(request, "core/enterprise/payment_multiple.html", {"empresa": e, "cuentas": accounts, "banks": banks})


@login_required
@permission_required("contabilidad.add_solicitudpago", raise_exception=True)
def payment_schedule(request):
    e = _empresa(request); accounts = CuentaPorPagarEnterprise.objects.filter(empresa=e, saldo__gt=0); banks = CuentaBancariaEmpresa.objects.filter(empresa=e, activa=True)
    if request.method == "POST":
        account = get_object_or_404(accounts, pk=request.POST.get("cuenta")); bank_id = request.POST.get("cuenta_prevista")
        obj = crear_solicitud_pago(context=_ctx(request), cuenta_id=account.pk, monto=request.POST.get("monto")); obj.fecha_prevista = request.POST.get("fecha_prevista"); obj.prioridad = request.POST.get("prioridad", "MEDIA"); obj.cuenta_prevista = get_object_or_404(banks, pk=bank_id) if bank_id else None; obj.observacion = request.POST.get("observacion", ""); obj.estado = "PROGRAMADO"; obj.save(update_fields=["fecha_prevista", "prioridad", "cuenta_prevista", "observacion", "estado"]); _audit(request, "PagoProgramado", obj, after={"fecha": str(obj.fecha_prevista), "monto": str(obj.monto)}); return redirect("core:enterprise_payment_schedule")
    scheduled = SolicitudPago.objects.filter(empresa=e, estado__in=["PROGRAMADO", "APROBADO", "PAGADO", "CANCELADO"]).select_related("cuenta__proveedor", "cuenta__factura", "cuenta_prevista")
    return render(request, "core/enterprise/payment_schedule.html", {"empresa": e, "cuentas": accounts, "banks": banks, "scheduled": scheduled.order_by("fecha_prevista")})


@login_required
@permission_required("comercial.view_cuentaporcobrar", raise_exception=True)
def cxc_list(request):
    e = _empresa(request); qs = CuentaPorCobrar.objects.filter(empresa=e).select_related("cliente", "factura", "moneda__moneda"); today = timezone.localdate(); open_qs = qs.filter(saldo__gt=0)
    kpis = [("Total por cobrar", open_qs.aggregate(v=Sum("saldo"))["v"] or 0), ("Vencido", open_qs.filter(fecha_vencimiento__lt=today).aggregate(v=Sum("saldo"))["v"] or 0), ("Por vencer", open_qs.filter(fecha_vencimiento__gte=today).aggregate(v=Sum("saldo"))["v"] or 0), ("Facturas cedidas", qs.filter(estado="CEDIDA_FACTORING").count()), ("Cobrado mes", 0)]
    return render(request, "core/enterprise/cxc_list.html", {"empresa": e, "cuentas": qs.order_by("fecha_vencimiento"), "kpis": kpis, "aging": _aging(open_qs), "today": today})


@login_required
def treasury(request):
    e = _empresa(request)
    return render(request, "core/enterprise/treasury.html", {"empresa": e, "banks": CuentaBancariaEmpresa.objects.filter(empresa=e), "movements": MovimientoTesoreria.objects.filter(empresa=e).select_related("cuenta", "caja")[:100], "reconciliations": ConciliacionBancaria.objects.filter(empresa=e)[:20], "flows": FlujoCajaProyectado.objects.filter(empresa=e).order_by("fecha")[:100], "factorings": CesionFactoring.objects.filter(empresa=e)[:50]})


@login_required
@permission_required("contabilidad.view_cuentaporpagarenterprise", raise_exception=True)
def cxp_export(request, fmt):
    rows = CuentaPorPagarEnterprise.objects.filter(empresa=_empresa(request)).select_related("proveedor", "factura")
    headers = ["Proveedor", "Factura", "Vencimiento", "Monto", "Pagado", "Pendiente", "Estado"]
    data = [[x.proveedor.nombre_comercial, x.factura.numero, x.vence_el, x.monto_original, x.monto_original-x.saldo, x.saldo, x.estado] for x in rows]
    _audit(request, "CxpExportada", rows.first() or _empresa(request), after={"formato": fmt, "cantidad": len(data)}) if rows.exists() else None
    if fmt == "xlsx":
        wb = Workbook(); ws = wb.active; ws.title = "Cuentas por pagar"; ws.append(headers)
        for row in data: ws.append(row)
        stream = BytesIO(); wb.save(stream); return HttpResponse(stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": 'attachment; filename="cuentas_por_pagar.xlsx"'})
    stream = BytesIO(); pdf = Canvas(stream, pagesize=letter); y = 750; pdf.setFont("Helvetica-Bold", 14); pdf.drawString(40, y, "SASTRE ERP - Aging de cuentas por pagar"); y -= 28; pdf.setFont("Helvetica", 8)
    for row in data:
        pdf.drawString(40, y, " | ".join(str(v) for v in row)); y -= 14
        if y < 45: pdf.showPage(); y = 750
    pdf.save(); return HttpResponse(stream.getvalue(), content_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="cuentas_por_pagar.pdf"'})
