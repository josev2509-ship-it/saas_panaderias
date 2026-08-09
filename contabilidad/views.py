from decimal import Decimal

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum
from django.utils import timezone

from .models import (
    Socio,
    AporteSocio,
    DeudaSocio,
    Gasto,
    Factoring,
    PagoFactoring,
    CuentaPorPagar,
    CuentaPorCobrar,
    Presupuesto,
)


def decimal_cero(valor):
    return valor or Decimal("0.00")

@login_required
def dashboard_enterprise(request):
    from conduces.services import obtener_empresa_usuario
    from contabilidad.models import AsientoContable,CuentaPorPagarEnterprise
    from tesoreria.models import CuentaBancariaEmpresa
    from presupuesto.models import Presupuesto as PresupuestoEnterprise
    from rrhh.models import Empleado
    from nomina.models import Nomina
    from activos.models import ActivoFijo
    from mantenimiento.models import OrdenMantenimiento
    e=obtener_empresa_usuario(request)
    kpis={"asientos":AsientoContable.objects.filter(empresa=e).count(),"cxp":CuentaPorPagarEnterprise.objects.filter(empresa=e).aggregate(v=Sum("saldo"))["v"] or 0,"bancos":CuentaBancariaEmpresa.objects.filter(empresa=e).aggregate(v=Sum("saldo"))["v"] or 0,"presupuestos":PresupuestoEnterprise.objects.filter(empresa=e,estado="ACTIVO").count(),"empleados":Empleado.objects.filter(empresa=e,estado="ACTIVO").count(),"nominas":Nomina.objects.filter(empresa=e).count(),"activos":ActivoFijo.objects.filter(empresa=e,estado="ACTIVO").count(),"mantenimientos":OrdenMantenimiento.objects.filter(empresa=e).exclude(estado__in=["COMPLETADA","CANCELADA"]).count()}
    return render(request,"contabilidad/dashboard_enterprise.html",{"empresa":e,"kpis":kpis})


@login_required
def dashboard_contabilidad(request):
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)

    gastos_mes = Gasto.objects.filter(
        fecha_factura__gte=inicio_mes,
        fecha_factura__lte=hoy,
    )

    cxp_pendientes = CuentaPorPagar.objects.filter(pagada=False)
    cxc_pendientes = CuentaPorCobrar.objects.filter(cobrada=False)
    factoring_pendiente = Factoring.objects.exclude(estado="cerrado")

    total_gastos_mes = decimal_cero(gastos_mes.aggregate(total=Sum("total"))["total"])
    total_cxp = decimal_cero(cxp_pendientes.aggregate(total=Sum("monto"))["total"])
    total_cxc = decimal_cero(cxc_pendientes.aggregate(total=Sum("monto"))["total"])
    total_factoring = decimal_cero(factoring_pendiente.aggregate(total=Sum("monto_factura"))["total"])

    pagos_factoring = decimal_cero(PagoFactoring.objects.aggregate(total=Sum("monto"))["total"])

    cuentas_vencidas = cxp_pendientes.filter(fecha_vencimiento__lt=hoy)
    cuentas_por_vencer = cxp_pendientes.filter(
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timezone.timedelta(days=7)
    )

    cuentas_cobrar_vencidas = cxc_pendientes.filter(fecha_vencimiento__lt=hoy)

    flujo_estimado = total_cxc - total_cxp

    contexto = {
        "titulo": "Dashboard contable",
        "hoy": hoy,
        "total_gastos_mes": total_gastos_mes,
        "total_cxp": total_cxp,
        "total_cxc": total_cxc,
        "total_factoring": total_factoring,
        "pagos_factoring": pagos_factoring,
        "flujo_estimado": flujo_estimado,
        "cuentas_vencidas": cuentas_vencidas[:10],
        "cuentas_por_vencer": cuentas_por_vencer[:10],
        "cuentas_cobrar_vencidas": cuentas_cobrar_vencidas[:10],
        "factoring_pendiente": factoring_pendiente[:10],
        "total_socios": Socio.objects.filter(activo=True).count(),
    }

    return render(request, "contabilidad/dashboard.html", contexto)


@login_required
def socios(request):
    socios_qs = Socio.objects.all().order_by("nombre")
    return render(request, "contabilidad/socios.html", {"socios": socios_qs})


@login_required
def crear_socio(request):
    return HttpResponse("Crear socio pendiente")


@login_required
def aportes_socios(request):
    return HttpResponse("Aportes socios pendiente")


@login_required
def crear_aporte_socio(request):
    return HttpResponse("Crear aporte socio pendiente")


@login_required
def deudas_socios(request):
    return HttpResponse("Deudas socios pendiente")


@login_required
def crear_deuda_socio(request):
    return HttpResponse("Crear deuda socio pendiente")


@login_required
def gastos(request):
    from conduces.services import obtener_empresa_usuario
    from .models import FacturaProveedor

    empresa = obtener_empresa_usuario(request)
    facturas_606 = FacturaProveedor.objects.filter(empresa=empresa).select_related(
        "proveedor", "moneda__moneda"
    ).order_by("-fecha", "-id")

    return render(
        request,
        "contabilidad/gastos.html",
        {
            "facturas_606": facturas_606
        }
    )


@login_required
def crear_gasto(request):
    return HttpResponse("Crear gasto pendiente")


@login_required
def exportar_606_excel(request):
    from openpyxl import Workbook
    from conduces.services import obtener_empresa_usuario
    from .models import FacturaProveedor

    empresa = obtener_empresa_usuario(request)
    facturas = FacturaProveedor.objects.filter(empresa=empresa).select_related(
        "proveedor", "moneda__moneda"
    ).prefetch_related("retenciones_aplicadas").order_by("fecha", "id")
    periodo = request.GET.get("periodo", "").strip()
    if periodo:
        try:
            anio, mes = (int(value) for value in periodo.split("-", 1))
            facturas = facturas.filter(fecha__year=anio, fecha__month=mes)
        except (TypeError, ValueError):
            return HttpResponse("El período debe usar el formato AAAA-MM.", status=400)

    headers = (
        "RNC/Cédula", "Tipo ID", "Tipo Bienes y Servicios", "NCF", "NCF Modificado",
        "Fecha Comprobante", "Fecha Pago", "Monto Servicios", "Monto Bienes", "Total Facturado",
        "ITBIS Facturado", "ITBIS Retenido", "ITBIS Sujeto Proporcionalidad", "ITBIS Llevado al Costo",
        "ITBIS por Adelantar", "ITBIS Percibido", "Retención Renta", "ISR Percibido", "ISC",
        "Otros Impuestos/Tasas", "Propina Legal", "Forma de Pago",
    )

    def safe(value):
        text = "" if value is None else str(value)
        return "'" + text if text[:1] in "=+-@" else value

    book = Workbook(); sheet = book.active; sheet.title = "DGII 606"; sheet.append(headers)
    for factura in facturas:
        dgii = factura.dimensiones or {}
        identificacion = factura.proveedor.rnc_normalizado or factura.proveedor.rnc_identificacion
        tipo_id = {"JURIDICA": "1", "GUBERNAMENTAL": "1", "FISICA": "2", "EXTRANJERA": "3"}.get(factura.proveedor.tipo_persona, "")
        retenciones = list(factura.retenciones_aplicadas.exclude(estado__in=["ANULADA", "REVERTIDA", "RECHAZADA"]))
        itbis_retenido = sum((item.monto for item in retenciones if item.tipo == "ITBIS"), Decimal("0"))
        renta_retenida = sum((item.monto for item in retenciones if item.tipo == "ISR"), Decimal("0"))
        sheet.append(tuple(safe(value) for value in (
            identificacion, tipo_id, dgii.get("dgii_tipo_bienes_servicios", ""), factura.ncf,
            dgii.get("dgii_ncf_modificado", ""), factura.fecha.strftime("%Y%m%d"), dgii.get("dgii_fecha_pago", ""),
            dgii.get("dgii_servicios", 0), dgii.get("dgii_bienes", 0), factura.total, factura.impuesto,
            itbis_retenido, dgii.get("dgii_itbis_proporcionalidad", 0), dgii.get("dgii_itbis_costo", 0),
            dgii.get("dgii_itbis_adelantar", 0), dgii.get("dgii_itbis_percibido", 0), renta_retenida,
            dgii.get("dgii_isr_percibido", 0), dgii.get("dgii_isc", 0), dgii.get("dgii_otros_impuestos", factura.cargos),
            dgii.get("dgii_propina", 0), dgii.get("dgii_forma_pago", ""),
        )))
    sheet.freeze_panes = "A2"; sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        sheet.column_dimensions[column[0].column_letter].width = min(28, max(12, max(len(str(cell.value or "")) for cell in column) + 2))
    from io import BytesIO
    stream = BytesIO(); book.save(stream)
    response = HttpResponse(stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="DGII_606_{periodo or "todos"}.xlsx"'
    return response


@login_required
def factoring(request):
    factoring_qs = Factoring.objects.all().order_by("-fecha_factura")
    return render(request, "contabilidad/factoring.html", {"factoring": factoring_qs})


@login_required
def crear_factoring(request):
    return HttpResponse("Crear factoring pendiente")


@login_required
def detalle_factoring(request, factoring_id):
    return HttpResponse(f"Detalle factoring {factoring_id}")


@login_required
def registrar_pago_factoring(request, factoring_id):
    return HttpResponse(f"Pago factoring {factoring_id}")


@login_required
def cuentas_por_pagar(request):
    cuentas = CuentaPorPagar.objects.all().order_by("fecha_vencimiento")
    return render(request, "contabilidad/cuentas_por_pagar.html", {"cuentas": cuentas})


@login_required
def crear_cuenta_por_pagar(request):
    return HttpResponse("Crear cuenta por pagar pendiente")


@login_required
def registrar_pago_cxp(request, cuenta_id):
    return HttpResponse(f"Pago CXP {cuenta_id}")


@login_required
def cuentas_por_cobrar(request):
    cuentas = CuentaPorCobrar.objects.all().order_by("fecha_vencimiento")
    return render(request, "contabilidad/cuentas_por_cobrar.html", {"cuentas": cuentas})


@login_required
def crear_cuenta_por_cobrar(request):
    return HttpResponse("Crear cuenta por cobrar pendiente")


@login_required
def registrar_cobro_cxc(request, cuenta_id):
    return HttpResponse(f"Cobro CXC {cuenta_id}")


@login_required
def presupuesto(request):
    presupuestos = Presupuesto.objects.all().order_by("-año")
    return render(request, "contabilidad/presupuesto.html", {"presupuestos": presupuestos})


@login_required
def crear_presupuesto(request):
    return HttpResponse("Crear presupuesto pendiente")


@login_required
def reportes_financieros(request):
    return render(request, "contabilidad/reportes_financieros.html")


@login_required
def estado_resultados(request):
    ingresos = CuentaPorCobrar.objects.filter(cobrada=True)
    gastos_pagados = Gasto.objects.filter(estado="pagado")

    total_ingresos = decimal_cero(ingresos.aggregate(total=Sum("monto"))["total"])
    total_gastos = decimal_cero(gastos_pagados.aggregate(total=Sum("total"))["total"])
    utilidad = total_ingresos - total_gastos

    return render(request, "contabilidad/estado_resultados.html", {
        "total_ingresos": total_ingresos,
        "total_gastos": total_gastos,
        "utilidad": utilidad,
    })


@login_required
def balance_general(request):
    total_cxc = decimal_cero(CuentaPorCobrar.objects.filter(cobrada=False).aggregate(total=Sum("monto"))["total"])
    total_cxp = decimal_cero(CuentaPorPagar.objects.filter(pagada=False).aggregate(total=Sum("monto"))["total"])

    return render(request, "contabilidad/balance_general.html", {
        "total_cxc": total_cxc,
        "total_cxp": total_cxp,
        "patrimonio_estimado": total_cxc - total_cxp,
    })


@login_required
def flujo_efectivo(request):
    ingresos = decimal_cero(CuentaPorCobrar.objects.filter(cobrada=True).aggregate(total=Sum("monto"))["total"])
    salidas = decimal_cero(Gasto.objects.filter(estado="pagado").aggregate(total=Sum("total"))["total"])

    return render(request, "contabilidad/flujo_efectivo.html", {
        "total_ingresos": ingresos,
        "total_salidas": salidas,
        "flujo_neto": ingresos - salidas,
    })


@login_required
def reporte_cuentas_por_cobrar(request):
    cuentas = CuentaPorCobrar.objects.all().order_by("fecha_vencimiento")
    return render(request, "contabilidad/reporte_cxc.html", {"cuentas": cuentas})


@login_required
def reporte_cuentas_por_pagar(request):
    cuentas = CuentaPorPagar.objects.all().order_by("fecha_vencimiento")
    return render(request, "contabilidad/reporte_cxp.html", {"cuentas": cuentas})
from django.shortcuts import render, redirect

from .models import (
    Factura606,
    Proveedor,
)

from .forms import (
    Factura606Form,
    ProveedorForm,
)


# =====================================================
# FACTURAS 606
# =====================================================

def lista_facturas_606(request):

    facturas = Factura606.objects.all().order_by(
        "-fecha_comprobante"
    )

    return render(
        request,
        "contabilidad/facturas_606.html",
        {
            "facturas": facturas
        }
    )


@login_required
def crear_factura_606(request):
    if request.method == "POST":
        form = Factura606Form(request.POST)

        if form.is_valid():
            form.save()
            return redirect("contabilidad:facturas_606")
    else:
        form = Factura606Form()

    return render(
        request,
        "contabilidad/crear_factura_606.html",
        {
            "form": form
        }
    )


# =====================================================
# PROVEEDORES
# =====================================================

def lista_proveedores(request):

    proveedores = Proveedor.objects.all()

    return render(
        request,
        "contabilidad/proveedores.html",
        {
            "proveedores": proveedores
        }
    )


def crear_proveedor(request):

    form = ProveedorForm(
        request.POST or None
    )

    if form.is_valid():

        form.save()

        return redirect(
            "contabilidad:proveedores"
        )

    return render(
        request,
        "contabilidad/crear_proveedor.html",
        {
            "form": form
        }
    )
