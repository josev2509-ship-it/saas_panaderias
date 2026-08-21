from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from rrhh.models import SaldoVacacion, SalidaEmpleado

from .models import DetalleNominaEmpleado, LiquidacionLaboral, PrestacionLaboral
from .payroll_engine import ZERO, money


PROTECTED_TERMINATIONS = {"MATERNIDAD", "FUERO_SINDICAL", "PROTECCION_ESPECIAL", "VIH"}
SEVERANCE_TERMINATIONS = {"DESAHUCIO", "DESPIDO_INJUSTIFICADO"}


def _service_parts(start, end):
    if end < start:
        raise ValidationError("La fecha de salida no puede ser anterior al ingreso.")
    years = end.year - start.year - ((end.month, end.day) < (start.month, start.day))
    anniversary_year = start.year + years
    anniversary = date(anniversary_year, start.month, min(start.day, monthrange(anniversary_year, start.month)[1]))
    remaining_days = max((end - anniversary).days, 0)
    return years, remaining_days, (end - start).days


def _preaviso_days(total_days):
    if total_days < 90:
        return 0
    if total_days < 180:
        return 7
    if total_days < 365:
        return 14
    return 28


def _cesantia_days(years, remaining_days, total_days):
    if total_days < 90:
        return 0
    if years == 0:
        return 6 if total_days < 180 else 13
    days = min(years, 5) * 21 + max(years - 5, 0) * 23
    if remaining_days >= 180:
        days += 13
    elif remaining_days >= 90:
        days += 6
    return days


def _salary_average(employee, exit_date):
    details = DetalleNominaEmpleado.objects.filter(
        empleado=employee,
        nomina__periodo__hasta__lte=exit_date,
        nomina__periodo__hasta__gte=date(exit_date.year - 1, exit_date.month, 1),
        nomina__estado__in=("CALCULADA", "APROBADA", "CERRADA", "PAGADA"),
    )
    snapshots = [Decimal(item.snapshot.get("employee", {}).get("salario_mensual", employee.salario)) for item in details]
    return money(sum(snapshots, ZERO) / len(snapshots)) if snapshots else money(employee.salario), bool(snapshots)


def _christmas_wages(employee, exit_date):
    details = DetalleNominaEmpleado.objects.filter(
        empleado=employee,
        nomina__periodo__desde__year=exit_date.year,
        nomina__periodo__hasta__lte=exit_date,
        nomina__estado__in=("CALCULADA", "APROBADA", "CERRADA", "PAGADA"),
    )
    actual = sum((d.salario_periodo for d in details), ZERO)
    if actual:
        return money(actual), True
    start = max(employee.fecha_ingreso, date(exit_date.year, 1, 1))
    earned_days = (exit_date - start).days + 1
    return money(employee.salario / Decimal("30") * earned_days), False


@transaction.atomic
def calculate_settlement(*, settlement):
    settlement = LiquidacionLaboral.objects.select_for_update().select_related("empleado").get(pk=settlement.pk)
    if settlement.estado in {"APROBADA", "PAGADA"}:
        raise ValidationError("Una liquidación aprobada no puede recalcularse.")
    employee = settlement.empleado
    salida = SalidaEmpleado.objects.filter(empresa=settlement.empresa, empleado=employee).first()
    exit_date = settlement.fecha_salida or (salida.fecha_salida if salida else settlement.fecha)
    termination = (settlement.tipo_terminacion or (salida.tipo if salida else "DESAHUCIO")).upper()
    years, remainder, total_days = _service_parts(employee.fecha_ingreso, exit_date)
    average_salary, has_history = _salary_average(employee, exit_date)
    daily_salary = money(average_salary / Decimal("23.83"))
    review_reasons = []
    if termination in PROTECTED_TERMINATIONS:
        review_reasons.append("Caso legalmente protegido; requiere revisión laboral especializada.")
    if not has_history:
        review_reasons.append("Sin historial salarial completo; se utilizó el salario vigente como base provisional.")

    eligible = termination in SEVERANCE_TERMINATIONS and not (termination in PROTECTED_TERMINATIONS)
    preaviso_days = Decimal(_preaviso_days(total_days) if eligible else 0)
    cesantia_days = Decimal(_cesantia_days(years, remainder, total_days) if eligible else 0)
    vacation_balance = SaldoVacacion.objects.filter(empleado=employee).first()
    vacation_days = max(Decimal(vacation_balance.disponibles if vacation_balance else 0), ZERO)
    christmas_wages, actual_christmas = _christmas_wages(employee, exit_date)
    if not actual_christmas:
        review_reasons.append("Salario de Navidad estimado por falta de nóminas históricas completas del año.")

    items = [
        ("PREAVISO", preaviso_days, daily_salary, "salario diario × días", "Código de Trabajo, art. 76", money(daily_salary * preaviso_days)),
        ("CESANTIA", cesantia_days, daily_salary, "salario diario × días", "Código de Trabajo, art. 80", money(daily_salary * cesantia_days)),
        ("VACACIONES", vacation_days, daily_salary, "salario diario × días pendientes", "Código de Trabajo, arts. 177 y 180", money(daily_salary * vacation_days)),
        ("SALARIO_NAVIDAD", ZERO, christmas_wages, "salarios ordinarios devengados en el año ÷ 12", "Código de Trabajo, art. 219", money(christmas_wages / Decimal("12"))),
    ]
    settlement.prestaciones.all().delete()
    total = ZERO
    for kind, days, base, formula, reference, amount in items:
        PrestacionLaboral.objects.create(liquidacion=settlement, tipo=kind, dias=days, base=base, formula=formula, referencia_legal=reference, monto=amount)
        total += amount
    settlement.fecha_salida = exit_date
    settlement.tipo_terminacion = termination
    settlement.salario_promedio = average_salary
    settlement.salario_diario = daily_salary
    settlement.total = money(total)
    settlement.requiere_revision = bool(review_reasons)
    settlement.motivo_revision = " ".join(review_reasons)
    settlement.estado = "REVISION" if review_reasons else "CALCULADA"
    settlement.snapshot = {
        "employee": {"codigo": employee.codigo, "nombre": f"{employee.nombres} {employee.apellidos}", "identificacion": employee.identificacion, "fecha_ingreso": employee.fecha_ingreso.isoformat()},
        "exit_date": exit_date.isoformat(), "termination": termination,
        "service": {"years": years, "remaining_days": remainder, "total_days": total_days},
        "salary": {"average_monthly": str(average_salary), "daily": str(daily_salary), "divisor": "23.83", "historical": has_history},
        "items": [{"type": i[0], "days": str(i[1]), "base": str(i[2]), "formula": i[3], "reference": i[4], "amount": str(i[5])} for i in items],
        "review_reasons": review_reasons,
        "sources": ["https://mt.gob.do/transparencia/images/docs/publicaciones/codigo-de-trabajo.pdf", "https://calculo.mt.gob.do/files/ayuda.pdf"],
    }
    settlement.save()
    return settlement
