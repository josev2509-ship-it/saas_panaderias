from django.urls import path
from . import views

app_name = "contabilidad"

urlpatterns = [
    path("enterprise/",views.dashboard_enterprise,name="dashboard_enterprise"),

    path(
        "",
        views.dashboard_contabilidad,
        name="dashboard"
    ),

    path(
        "socios/",
        views.socios,
        name="socios"
    ),

    path(
        "socios/crear/",
        views.crear_socio,
        name="crear_socio"
    ),

    path(
        "aportes/",
        views.aportes_socios,
        name="aportes_socios"
    ),

    path(
        "aportes/crear/",
        views.crear_aporte_socio,
        name="crear_aporte_socio"
    ),

    path(
        "deudas-socios/",
        views.deudas_socios,
        name="deudas_socios"
    ),

    path(
        "deudas-socios/crear/",
        views.crear_deuda_socio,
        name="crear_deuda_socio"
    ),

    path(
        "gastos/",
        views.gastos,
        name="gastos"
    ),

    path(
        "gastos/crear/",
        views.crear_gasto,
        name="crear_gasto"
    ),

    path(
        "gastos/exportar-606/",
        views.exportar_606_excel,
        name="exportar_606_excel"
    ),

    path(
        "factoring/",
        views.factoring,
        name="factoring"
    ),

    path(
        "factoring/crear/",
        views.crear_factoring,
        name="crear_factoring"
    ),

    path(
        "factoring/<int:factoring_id>/",
        views.detalle_factoring,
        name="detalle_factoring"
    ),

    path(
        "factoring/<int:factoring_id>/pago/",
        views.registrar_pago_factoring,
        name="registrar_pago_factoring"
    ),

    path(
        "cuentas-por-pagar/",
        views.cuentas_por_pagar,
        name="cuentas_por_pagar"
    ),

    path(
        "cuentas-por-pagar/crear/",
        views.crear_cuenta_por_pagar,
        name="crear_cuenta_por_pagar"
    ),

    path(
        "cuentas-por-pagar/<int:cuenta_id>/pago/",
        views.registrar_pago_cxp,
        name="registrar_pago_cxp"
    ),

    path(
        "cuentas-por-cobrar/",
        views.cuentas_por_cobrar,
        name="cuentas_por_cobrar"
    ),

    path(
        "cuentas-por-cobrar/crear/",
        views.crear_cuenta_por_cobrar,
        name="crear_cuenta_por_cobrar"
    ),

    path(
        "cuentas-por-cobrar/<int:cuenta_id>/cobro/",
        views.registrar_cobro_cxc,
        name="registrar_cobro_cxc"
    ),

    path(
        "presupuesto/",
        views.presupuesto,
        name="presupuesto"
    ),

    path(
        "presupuesto/crear/",
        views.crear_presupuesto,
        name="crear_presupuesto"
    ),
    # =====================================================
# REPORTES FINANCIEROS
# =====================================================

path(
    "reportes/",
    views.reportes_financieros,
    name="reportes_financieros"
),

path(
    "reportes/estado-resultados/",
    views.estado_resultados,
    name="estado_resultados"
),

path(
    "reportes/balance-general/",
    views.balance_general,
    name="balance_general"
),

path(
    "reportes/flujo-efectivo/",
    views.flujo_efectivo,
    name="flujo_efectivo"
),

path(
    "reportes/cuentas-por-cobrar/",
    views.reporte_cuentas_por_cobrar,
    name="reporte_cuentas_por_cobrar"
),

path(
    "reportes/cuentas-por-pagar/",
    views.reporte_cuentas_por_pagar,
    name="reporte_cuentas_por_pagar"
),
# =====================================================
# FACTURAS 606
# =====================================================

path(
    "facturas-606/",
    views.lista_facturas_606,
    name="facturas_606"
),

path(
    "facturas-606/crear/",
    views.crear_factura_606,
    name="crear_factura_606"
),

# =====================================================
# PROVEEDORES
# =====================================================

path(
    "proveedores/",
    views.lista_proveedores,
    name="proveedores"
),

path(
    "proveedores/crear/",
    views.crear_proveedor,
    name="crear_proveedor"
),
]
