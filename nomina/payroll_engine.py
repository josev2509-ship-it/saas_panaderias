from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from rrhh.models import Empleado, HoraExtra

from .models import ConceptoNomina, DetalleNominaEmpleado, LineaDetalleNomina, Nomina, NovedadNomina, ParametroLegalNomina

ZERO = Decimal("0.00")
CENT = Decimal("0.01")
DEFAULT_ISR_2026 = [
    {"desde": "0", "hasta": "416220.00", "fijo": "0", "tasa": "0", "excedente": "0"},
    {"desde": "416220.00", "hasta": "624329.00", "fijo": "0", "tasa": "0.15", "excedente": "416220.00"},
    {"desde": "624329.00", "hasta": "867123.00", "fijo": "31216.00", "tasa": "0.20", "excedente": "624329.00"},
    {"desde": "867123.00", "hasta": None, "fijo": "79776.00", "tasa": "0.25", "excedente": "867123.00"},
]
OFFICIAL_SOURCES = [
    "https://tss.gob.do/tss-informa-nuevos-topes-de-cotizacion-del-regimen-contributivo-del-sdss/",
    "https://www.tss.gob.do/assets/guiausuario24b.pdf",
    "https://ayuda.dgii.gov.do/conversations/impuesto-sobre-la-renta-isr/ca687-cul-es-la-escala-salarial-correspondiente-al-ao-2026-del-impuesto-sobre-la-renta-isr/696a664277932619036537b8",
]


def money(value):
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def ensure_legal_parameters(empresa, fecha=None):
    fecha = fecha or timezone.localdate()
    current = ParametroLegalNomina.objects.filter(empresa=empresa, activo=True, vigente_desde__lte=fecha).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=fecha)).first()
    if current:
        return current
    if fecha.year != 2026 or fecha < timezone.datetime(2026, 2, 1).date():
        raise ValidationError("No existe una parametrización legal versionada para la fecha del período.")
    return ParametroLegalNomina.objects.create(
        empresa=empresa, nombre="RD Nómina 2026 · vigencia febrero", version=1,
        vigente_desde=timezone.datetime(2026, 2, 1).date(), sfs_empleado=Decimal("0.0304"),
        afp_empleado=Decimal("0.0287"), sfs_empleador=Decimal("0.0709"),
        svds_empleador=Decimal("0.0710"), srl_fijo=Decimal("0.0100"), srl_variable=ZERO,
        infotep_empleador=Decimal("0.0100"), tope_sfs=Decimal("232230.00"),
        tope_svds=Decimal("464460.00"), tope_srl=Decimal("92892.00"),
        escala_isr=DEFAULT_ISR_2026, fuentes=OFFICIAL_SOURCES,
    )


def parameter_snapshot(p):
    keys = ("sfs_empleado", "afp_empleado", "sfs_empleador", "svds_empleador", "srl_fijo", "srl_variable", "infotep_empleador", "tope_sfs", "tope_svds", "tope_srl")
    data = {key: str(getattr(p, key)) for key in keys}
    data.update({"id": p.pk, "version": p.version, "vigente_desde": p.vigente_desde.isoformat(), "escala_isr": p.escala_isr, "fuentes": p.fuentes})
    return data


def calculate_isr_annual(taxable_annual, brackets):
    taxable_annual = Decimal(taxable_annual)
    for bracket in brackets:
        start = Decimal(bracket["desde"])
        end = Decimal(bracket["hasta"]) if bracket.get("hasta") else None
        if taxable_annual >= start and (end is None or taxable_annual <= end):
            return money(Decimal(bracket["fijo"]) + max(taxable_annual - Decimal(bracket["excedente"]), ZERO) * Decimal(bracket["tasa"]))
    return ZERO


def _factor(periodo):
    return {"QUINCENAL": Decimal("0.5"), "SEMANAL": Decimal("0.25")}.get(periodo.tipo.periodicidad.upper(), Decimal("1"))


def _concept(empresa, codigo, nombre, tipo, **flags):
    obj, _ = ConceptoNomina.objects.get_or_create(empresa=empresa, codigo=codigo, defaults={"nombre": nombre, "tipo": tipo, "activo": True, **flags})
    return obj


def _canonical_concepts(empresa):
    return {
        "SALARIO": _concept(empresa, "SALARIO", "Salario ordinario", "INGRESO", gravable=True, cotiza_tss=True, cotiza_infotep=True, origen="SALARIO"),
        "HORA_EXTRA": _concept(empresa, "HORA_EXTRA", "Horas extra aprobadas", "INGRESO", gravable=True, origen="ASISTENCIA"),
        "AFP": _concept(empresa, "AFP", "AFP/SVDS trabajador", "DEDUCCION", origen="LEGAL"),
        "SFS": _concept(empresa, "SFS", "SFS trabajador", "DEDUCCION", origen="LEGAL"),
        "ISR": _concept(empresa, "ISR", "ISR asalariado", "DEDUCCION", origen="LEGAL"),
        "SFS_PATRONAL": _concept(empresa, "SFS_PATRONAL", "SFS empleador", "APORTE", origen="LEGAL"),
        "SVDS_PATRONAL": _concept(empresa, "SVDS_PATRONAL", "SVDS empleador", "APORTE", origen="LEGAL"),
        "SRL": _concept(empresa, "SRL", "Riesgos laborales", "APORTE", origen="LEGAL"),
        "INFOTEP": _concept(empresa, "INFOTEP", "INFOTEP empleador", "APORTE", origen="LEGAL"),
    }


def _add_line(detail, concept, amount, **snapshot):
    if money(amount) != ZERO:
        LineaDetalleNomina.objects.create(detalle=detail, concepto=concept, monto=money(amount), snapshot=snapshot)


@transaction.atomic
def process_payroll(*, empresa, periodo, usuario=None):
    payroll, _ = Nomina.objects.select_for_update().get_or_create(empresa=empresa, periodo=periodo, defaults={"numero": f"NOM-{periodo.pk:06d}"})
    if payroll.estado in {"APROBADA", "CERRADA", "PAGADA"}:
        raise ValidationError("Una nómina aprobada o cerrada no puede recalcularse.")
    legal = ensure_legal_parameters(empresa, periodo.hasta)
    legal_snapshot, concepts, factor = parameter_snapshot(legal), _canonical_concepts(empresa), _factor(periodo)
    totals = {key: ZERO for key in ("gross", "deductions", "net", "afp", "sfs", "isr", "other_deductions", "employer")}
    employees = Empleado.objects.filter(empresa=empresa, estado="ACTIVO", fecha_ingreso__lte=periodo.hasta)
    for employee in employees.select_related("puesto", "departamento"):
        salary_period = money(employee.salario * factor)
        additions = list(NovedadNomina.objects.filter(empresa=empresa, empleado=employee, periodo=periodo, estado="APROBADA").select_related("concepto"))
        extras = HoraExtra.objects.filter(empresa=empresa, empleado=employee, fecha__range=(periodo.desde, periodo.hasta)).filter(Q(estado="APROBADA") | Q(estado="APLICADA", nomina_id=payroll.pk))
        overtime = money(extras.aggregate(value=Sum("monto"))["value"] or ZERO)
        other_income = money(sum((n.monto for n in additions if n.concepto.tipo == "INGRESO"), ZERO))
        other_deductions = money(sum((n.monto for n in additions if n.concepto.tipo == "DEDUCCION"), ZERO))
        manual_employer = money(sum((n.monto for n in additions if n.concepto.tipo == "APORTE"), ZERO))
        gross = money(salary_period + overtime + other_income)
        tss_base_period = salary_period + sum((n.monto for n in additions if n.concepto.tipo == "INGRESO" and n.concepto.cotiza_tss), ZERO)
        infotep_base_period = salary_period + sum((n.monto for n in additions if n.concepto.tipo == "INGRESO" and n.concepto.cotiza_infotep), ZERO)
        monthly_tss_base, monthly_infotep_base = money(tss_base_period / factor), money(infotep_base_period / factor)
        afp = money(min(monthly_tss_base, legal.tope_svds) * legal.afp_empleado * factor)
        sfs = money(min(monthly_tss_base, legal.tope_sfs) * legal.sfs_empleado * factor)
        taxable_period = salary_period + overtime + sum((n.monto for n in additions if n.concepto.tipo == "INGRESO" and n.concepto.gravable), ZERO)
        taxable_month = max(money(taxable_period / factor) - money((afp + sfs) / factor), ZERO)
        annual_isr = calculate_isr_annual(taxable_month * 12, legal.escala_isr)
        isr = money(annual_isr / 12 * factor)
        sfs_employer = money(min(monthly_tss_base, legal.tope_sfs) * legal.sfs_empleador * factor)
        svds_employer = money(min(monthly_tss_base, legal.tope_svds) * legal.svds_empleador * factor)
        srl_employer = money(min(monthly_tss_base, legal.tope_srl) * (legal.srl_fijo + legal.srl_variable) * factor)
        infotep_employer = money(monthly_infotep_base * legal.infotep_empleador * factor)
        deductions = money(afp + sfs + isr + other_deductions)
        employer_total = money(sfs_employer + svds_employer + srl_employer + infotep_employer + manual_employer)
        net = money(gross - deductions)
        if net < ZERO:
            raise ValidationError(f"Las deducciones de {employee.codigo} producirían un neto negativo.")
        snapshot = {"employee": {"codigo": employee.codigo, "identificacion": employee.identificacion, "nombre": f"{employee.nombres} {employee.apellidos}", "puesto": employee.puesto.nombre, "fecha_ingreso": employee.fecha_ingreso.isoformat(), "salario_mensual": str(employee.salario)}, "period": {"desde": periodo.desde.isoformat(), "hasta": periodo.hasta.isoformat(), "periodicidad": periodo.tipo.periodicidad, "factor": str(factor)}, "legal": legal_snapshot, "bases": {"tss_mensual": str(monthly_tss_base), "isr_mensual": str(taxable_month), "isr_anual": str(taxable_month * 12), "isr_anual_calculado": str(annual_isr)}}
        detail, _ = DetalleNominaEmpleado.objects.update_or_create(nomina=payroll, empleado=employee, defaults={"ingresos": gross, "deducciones": deductions, "aportes": employer_total, "neto": net, "salario_periodo": salary_period, "horas_extra": overtime, "otros_ingresos": other_income, "afp_empleado": afp, "sfs_empleado": sfs, "isr": isr, "otros_descuentos": other_deductions, "sfs_empleador": sfs_employer, "svds_empleador": svds_employer, "srl_empleador": srl_employer, "infotep_empleador": infotep_employer, "snapshot": snapshot, "alerta": ""})
        detail.lineas.all().delete()
        _add_line(detail, concepts["SALARIO"], salary_period, fuente="salario_empleado", gravable=True, cotiza_tss=True)
        _add_line(detail, concepts["HORA_EXTRA"], overtime, fuente="horas_extra_aprobadas", ids=list(extras.values_list("pk", flat=True)), gravable=True, cotiza_tss=False)
        for addition in additions:
            _add_line(detail, addition.concepto, addition.monto, fuente="novedad_nomina", novedad_id=addition.pk, gravable=addition.concepto.gravable, cotiza_tss=addition.concepto.cotiza_tss)
        for code, amount in (("AFP", afp), ("SFS", sfs), ("ISR", isr), ("SFS_PATRONAL", sfs_employer), ("SVDS_PATRONAL", svds_employer), ("SRL", srl_employer), ("INFOTEP", infotep_employer)):
            _add_line(detail, concepts[code], amount, fuente="motor_legal", parametro_version=legal.version)
        extras.filter(estado="APROBADA").update(estado="APLICADA", nomina_id=payroll.pk)
        for key, value in (("gross", gross), ("deductions", deductions), ("net", net), ("afp", afp), ("sfs", sfs), ("isr", isr), ("other_deductions", other_deductions), ("employer", employer_total)):
            totals[key] += value
    payroll.detalles.exclude(empleado__in=employees).delete()
    payroll.total_ingresos, payroll.total_deducciones, payroll.total_neto = money(totals["gross"]), money(totals["deductions"]), money(totals["net"])
    payroll.total_afp, payroll.total_sfs, payroll.total_isr = money(totals["afp"]), money(totals["sfs"]), money(totals["isr"])
    payroll.total_otros_descuentos, payroll.total_aportes_patronales = money(totals["other_deductions"]), money(totals["employer"])
    payroll.snapshot_reglas, payroll.estado = legal_snapshot, "CALCULADA"
    payroll.save()
    return payroll
