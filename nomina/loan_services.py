from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.application.numbering import obtener_siguiente_numero

from .models import CuotaPrestamoEmpleado, PrestamoEmpleado


CENT = Decimal("0.01")


def money(value):
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


@transaction.atomic
def prepare_loan(loan, *, usuario=None):
    if not loan.codigo:
        loan.codigo = obtener_siguiente_numero(
            empresa=loan.empresa, tipo_documento="PRE", prefijo="PRE", longitud=6, usuario=usuario
        )
    loan.fecha = loan.fecha or timezone.localdate()
    loan.saldo = money(loan.principal)
    if not loan.monto_cuota:
        loan.monto_cuota = money(loan.principal / loan.cuotas)
    if loan.principal <= 0 or loan.cuotas <= 0 or loan.monto_cuota <= 0:
        raise ValidationError("El monto, las cuotas y el valor de cuota deben ser mayores que cero.")
    loan.full_clean()
    loan.save()
    return loan


@transaction.atomic
def provision_payroll_loans(*, payroll, employee):
    total = Decimal("0")
    provisions = []
    from django.db.models import Q
    loans = PrestamoEmpleado.objects.select_for_update().filter(
        empresa=payroll.empresa, empleado=employee, estado="ACTIVO", saldo__gt=0
    ).filter(Q(primera_nomina__isnull=True) | Q(primera_nomina__desde__lte=payroll.periodo.hasta))
    for loan in loans.distinct().order_by("fecha", "pk"):
        paid = loan.cuotas_detalle.filter(estado="APLICADA").count()
        if paid >= loan.cuotas:
            continue
        amount = money(min(loan.monto_cuota, loan.saldo))
        quota, _ = CuotaPrestamoEmpleado.objects.update_or_create(
            prestamo=loan, nomina=payroll,
            defaults={"numero": paid + 1, "monto": amount, "pagada": False, "fecha": payroll.periodo.hasta,
                      "saldo_anterior": loan.saldo, "saldo_posterior": money(loan.saldo - amount), "estado": "PROVISIONAL"},
        )
        total += amount
        provisions.append(quota)
    return money(total), provisions


@transaction.atomic
def finalize_payroll_loans(payroll):
    for quota in CuotaPrestamoEmpleado.objects.select_for_update().select_related("prestamo").filter(nomina=payroll, estado="PROVISIONAL"):
        loan = PrestamoEmpleado.objects.select_for_update().get(pk=quota.prestamo_id)
        quota.saldo_anterior = loan.saldo
        quota.saldo_posterior = money(max(loan.saldo - quota.monto, Decimal("0")))
        quota.estado, quota.pagada = "APLICADA", True
        quota.save(update_fields=["saldo_anterior", "saldo_posterior", "estado", "pagada"])
        loan.saldo = quota.saldo_posterior
        if loan.saldo == 0 or loan.cuotas_detalle.filter(estado="APLICADA").count() >= loan.cuotas:
            loan.estado = "PAGADO"
        loan.save(update_fields=["saldo", "estado"])


@transaction.atomic
def reverse_payroll_loans(payroll):
    for quota in CuotaPrestamoEmpleado.objects.select_for_update().select_related("prestamo").filter(nomina=payroll, estado="APLICADA"):
        loan = PrestamoEmpleado.objects.select_for_update().get(pk=quota.prestamo_id)
        loan.saldo = money(loan.saldo + quota.monto)
        if loan.estado == "PAGADO":
            loan.estado = "ACTIVO"
        loan.save(update_fields=["saldo", "estado"])
        quota.estado, quota.pagada = "REVERSADA", False
        quota.save(update_fields=["estado", "pagada"])


def loan_totals(loan):
    paid = loan.cuotas_detalle.filter(estado="APLICADA").aggregate(total=Sum("monto"))["total"] or Decimal("0")
    paid_count = loan.cuotas_detalle.filter(estado="APLICADA").count()
    return {"pagado": money(paid), "cuotas_pagadas": paid_count, "cuotas_pendientes": max(loan.cuotas-paid_count, 0)}
