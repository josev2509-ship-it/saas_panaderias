from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from conduces.models import Empresa
from rrhh.models import CentroTrabajo, Departamento, Empleado, HoraExtra, Puesto, SaldoVacacion

from .documents import loan_statement_pdf, payroll_pdf, payroll_xlsx, payslip_pdf, payslips_zip, settlement_pdf
from .forms import PrestamoForm
from .loan_services import finalize_payroll_loans, prepare_loan, reverse_payroll_loans
from .labor_settlement import calculate_settlement
from .models import ConceptoNomina, CuotaPrestamoEmpleado, LiquidacionLaboral, NovedadNomina, PeriodoNomina, PrestamoEmpleado, TipoNomina
from .payroll_engine import calculate_isr_annual, ensure_legal_parameters, money, process_payroll, salario_ordinario_periodo


class PayrollRDEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("payroll-rd", "payroll@example.test", "test")
        cls.company = Empresa.objects.create(usuario=cls.user, nombre="Payroll RD", rnc="101000001")
        cls.department = Departamento.objects.create(empresa=cls.company, codigo="FIN", nombre="Finanzas")
        cls.position = Puesto.objects.create(empresa=cls.company, codigo="ANA", nombre="Analista")
        cls.center = CentroTrabajo.objects.create(empresa=cls.company, codigo="SDQ", nombre="Principal")

    def setUp(self):
        self.client.force_login(self.user)

    def employee(self, code, salary, start=date(2022, 1, 1)):
        return Empleado.objects.create(empresa=self.company, codigo=code, nombres="Persona", apellidos=code, identificacion=f"ID-{code}", puesto=self.position, departamento=self.department, centro=self.center, fecha_ingreso=start, salario=Decimal(salary), estado="ACTIVO")

    def period(self, periodicity="MENSUAL", start=date(2026, 8, 1), end=date(2026, 8, 31)):
        kind = TipoNomina.objects.create(empresa=self.company, nombre=f"{periodicity}-{TipoNomina.objects.count()}", periodicidad=periodicity)
        return PeriodoNomina.objects.create(empresa=self.company, tipo=kind, desde=start, hasta=end)

    def test_official_isr_brackets_2026(self):
        brackets = ensure_legal_parameters(self.company, date(2026, 8, 31)).escala_isr
        self.assertEqual(calculate_isr_annual(Decimal("400000"), brackets), Decimal("0.00"))
        self.assertEqual(calculate_isr_annual(Decimal("500000"), brackets), Decimal("12567.00"))
        self.assertEqual(calculate_isr_annual(Decimal("700000"), brackets), Decimal("46350.20"))
        self.assertEqual(calculate_isr_annual(Decimal("900000"), brackets), Decimal("87995.25"))

    def test_payroll_below_and_across_all_isr_bands(self):
        for code, salary in (("EXENTO", "30000"), ("B15", "45000"), ("B20", "60000"), ("B25", "80000")):
            self.employee(code, salary)
        payroll = process_payroll(empresa=self.company, periodo=self.period())
        details = {d.empleado.codigo: d for d in payroll.detalles.select_related("empleado")}
        self.assertEqual(details["EXENTO"].isr, Decimal("0.00"))
        self.assertEqual(details["B15"].isr, Decimal("1148.33"))
        self.assertEqual(details["B20"].isr, Decimal("3486.65"))
        self.assertEqual(details["B25"].isr, Decimal("7400.94"))

    def test_tss_caps_and_employer_contributions_are_separate(self):
        employee = self.employee("TOPES", "500000")
        payroll = process_payroll(empresa=self.company, periodo=self.period())
        detail = payroll.detalles.get(empleado=employee)
        legal = ensure_legal_parameters(self.company, date(2026, 8, 31))
        self.assertEqual(detail.sfs_empleado, money(legal.tope_sfs * legal.sfs_empleado))
        self.assertEqual(detail.afp_empleado, money(legal.tope_svds * legal.afp_empleado))
        self.assertEqual(detail.srl_empleador, money(legal.tope_srl * legal.srl_fijo))
        self.assertEqual(detail.deducciones, detail.afp_empleado + detail.sfs_empleado + detail.isr)
        self.assertNotEqual(detail.aportes, Decimal("0.00"))
        self.assertEqual(detail.neto, detail.ingresos - detail.deducciones)

    def test_overtime_incentive_and_other_discount_are_integrated_once(self):
        employee = self.employee("MIX", "45000")
        period = self.period()
        incentive = ConceptoNomina.objects.create(empresa=self.company, codigo="INC", nombre="Incentivo", tipo="INGRESO", gravable=True)
        discount = ConceptoNomina.objects.create(empresa=self.company, codigo="DESC", nombre="Otro descuento", tipo="DEDUCCION")
        NovedadNomina.objects.create(empresa=self.company, empleado=employee, periodo=period, concepto=incentive, monto=Decimal("3000"))
        NovedadNomina.objects.create(empresa=self.company, empleado=employee, periodo=period, concepto=discount, monto=Decimal("500"))
        extra = HoraExtra.objects.create(empresa=self.company, empleado=employee, fecha=date(2026, 8, 10), horas=2, monto=Decimal("1200"), estado="APROBADA")
        payroll = process_payroll(empresa=self.company, periodo=period)
        detail = payroll.detalles.get()
        self.assertEqual(detail.ingresos, Decimal("49200.00"))
        self.assertEqual(detail.horas_extra, Decimal("1200.00"))
        self.assertEqual(detail.otros_ingresos, Decimal("3000.00"))
        self.assertEqual(detail.otros_descuentos, Decimal("500.00"))
        process_payroll(empresa=self.company, periodo=period)
        self.assertEqual(payroll.detalles.get().horas_extra, Decimal("1200.00"))
        extra.refresh_from_db()
        self.assertEqual(extra.estado, "APLICADA")

    def test_monthly_and_biweekly_are_consistent(self):
        employee = self.employee("FREQ", "60000")
        monthly = process_payroll(empresa=self.company, periodo=self.period())
        monthly_detail = monthly.detalles.get(empleado=employee)
        biweekly = process_payroll(empresa=self.company, periodo=self.period("QUINCENAL", date(2026, 9, 1), date(2026, 9, 15)))
        biweekly_detail = biweekly.detalles.get(empleado=employee)
        self.assertEqual(biweekly_detail.salario_periodo, Decimal("30000.00"))
        self.assertEqual(biweekly_detail.afp_empleado, money(monthly_detail.afp_empleado / 2))
        self.assertEqual(biweekly_detail.sfs_empleado, money(monthly_detail.sfs_empleado / 2))
        self.assertEqual(biweekly_detail.isr, money(monthly_detail.isr / 2))

    def test_salary_frequency_has_one_canonical_conversion_service(self):
        employee = self.employee("BASE-FREQ", "50000")
        biweekly = self.period("QUINCENAL", date(2026, 10, 1), date(2026, 10, 15))
        self.assertEqual(salario_ordinario_periodo(employee, biweekly), Decimal("25000.00"))
        employee.frecuencia_salario, employee.salario = "QUINCENAL", Decimal("25000")
        employee.save(update_fields=["frecuencia_salario", "salario"])
        self.assertEqual(salario_ordinario_periodo(employee, biweekly), Decimal("25000.00"))

    def test_payroll_context_panels_keep_selected_payroll(self):
        employee = self.employee("CTX", "50000")
        payroll = process_payroll(empresa=self.company, periodo=self.period("QUINCENAL", date(2026, 11, 1), date(2026, 11, 15)))
        for section in ("ingresos", "descuentos", "prestamos", "aportes", "volantes", "documentos"):
            response = self.client.get(reverse("nomina:panel", args=[payroll.pk, section]))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, payroll.numero)
        response = self.client.get(reverse("nomina:novedad_crear") + f"?tipo=DESCUENTO&nomina={payroll.pk}")
        self.assertContains(response, "← Volver")

    def test_snapshot_is_historical_and_closed_payroll_cannot_recalculate(self):
        self.employee("SNAP", "45000")
        period = self.period()
        payroll = process_payroll(empresa=self.company, periodo=period)
        detail = payroll.detalles.get()
        old_net, old_rate = detail.neto, detail.snapshot["legal"]["sfs_empleado"]
        legal = ensure_legal_parameters(self.company, period.hasta)
        legal.sfs_empleado = Decimal("0.999")
        legal.save()
        detail.refresh_from_db()
        self.assertEqual(detail.neto, old_net)
        self.assertEqual(detail.snapshot["legal"]["sfs_empleado"], old_rate)
        payroll.estado = "CERRADA"
        payroll.save()
        with self.assertRaises(ValidationError):
            process_payroll(empresa=self.company, periodo=period)

    def test_pdf_excel_zip_and_payslip_use_snapshot(self):
        self.employee("DOC", "45000")
        payroll = process_payroll(empresa=self.company, periodo=self.period())
        detail = payroll.detalles.get()
        self.assertTrue(payroll_pdf(payroll).startswith(b"%PDF"))
        self.assertTrue(payslip_pdf(detail).startswith(b"%PDF"))
        workbook = load_workbook(BytesIO(payroll_xlsx(payroll)))
        self.assertEqual(workbook.active["A1"].value, "Código")
        with ZipFile(BytesIO(payslips_zip(payroll))) as archive:
            self.assertEqual(len(archive.namelist()), 1)
            self.assertTrue(archive.read(archive.namelist()[0]).startswith(b"%PDF"))

    def test_views_expose_enterprise_outputs(self):
        self.employee("WEB", "45000")
        payroll = process_payroll(empresa=self.company, periodo=self.period())
        detail = payroll.detalles.get()
        for name, args, content_type in (("nomina:detalle", [payroll.pk], "text/html"), ("nomina:empleado_detalle", [payroll.pk, detail.pk], "text/html"), ("nomina:nomina_pdf", [payroll.pk], "application/pdf"), ("nomina:volante_pdf", [payroll.pk, detail.pk], "application/pdf"), ("nomina:exportar_excel", [payroll.pk], "spreadsheetml"), ("nomina:volantes_zip", [payroll.pk], "application/zip")):
            response = self.client.get(reverse(name, args=args))
            self.assertEqual(response.status_code, 200)
            self.assertIn(content_type, response["Content-Type"])


class LaborSettlementEngineTests(PayrollRDEngineTests):
    def test_automatic_settlement_breakdown_and_documents(self):
        employee = self.employee("LIQ", "30000", date(2022, 10, 1))
        SaldoVacacion.objects.create(empleado=employee, disponibles=Decimal("14"), tomados=0)
        process_payroll(empresa=self.company, periodo=self.period())
        settlement = LiquidacionLaboral.objects.create(empresa=self.company, empleado=employee, fecha=date(2026, 8, 31), fecha_salida=date(2026, 8, 31), tipo_terminacion="DESAHUCIO")
        settlement = calculate_settlement(settlement=settlement)
        self.assertGreater(settlement.total, 0)
        self.assertEqual(settlement.prestaciones.count(), 4)
        self.assertFalse(any(item.monto < 0 for item in settlement.prestaciones.all()))
        self.assertEqual(settlement.prestaciones.get(tipo="PREAVISO").dias, Decimal("28.00"))
        self.assertTrue(settlement_pdf(settlement).startswith(b"%PDF"))
        self.assertTrue(settlement_pdf(settlement, letter=True).startswith(b"%PDF"))

    def test_resignation_excludes_preaviso_and_severance(self):
        employee = self.employee("REN", "30000", date(2024, 1, 1))
        settlement = LiquidacionLaboral.objects.create(empresa=self.company, empleado=employee, fecha=date(2026, 8, 31), fecha_salida=date(2026, 8, 31), tipo_terminacion="RENUNCIA")
        settlement = calculate_settlement(settlement=settlement)
        self.assertEqual(settlement.prestaciones.get(tipo="PREAVISO").monto, Decimal("0.00"))
        self.assertEqual(settlement.prestaciones.get(tipo="CESANTIA").monto, Decimal("0.00"))

    def test_protected_case_requires_human_review(self):
        employee = self.employee("PROT", "30000", date(2024, 1, 1))
        settlement = LiquidacionLaboral.objects.create(empresa=self.company, empleado=employee, fecha=date(2026, 8, 31), fecha_salida=date(2026, 8, 31), tipo_terminacion="MATERNIDAD")
        settlement = calculate_settlement(settlement=settlement)
        self.assertTrue(settlement.requiere_revision)
        self.assertEqual(settlement.estado, "REVISION")
        self.assertIn("protegido", settlement.motivo_revision.lower())


class PayrollProfessionalExperienceTests(PayrollRDEngineTests):
    def test_multiple_loans_recalculation_and_final_balance_are_idempotent(self):
        employee = self.employee("LOAN", "60000")
        period = self.period()
        loans = []
        for amount, installments in (("30000", 10), ("12000", 4)):
            loan = PrestamoEmpleado(empresa=self.company, empleado=employee, principal=Decimal(amount), saldo=0, cuotas=installments, estado="ACTIVO", primera_nomina=period)
            loans.append(prepare_loan(loan, usuario=self.user))
        payroll = process_payroll(empresa=self.company, periodo=period)
        detail = payroll.detalles.get(empleado=employee)
        self.assertEqual(detail.otros_descuentos, Decimal("6000.00"))
        self.assertEqual(CuotaPrestamoEmpleado.objects.filter(nomina=payroll).count(), 2)
        process_payroll(empresa=self.company, periodo=period)
        self.assertEqual(CuotaPrestamoEmpleado.objects.filter(nomina=payroll).count(), 2)
        for loan in loans:
            loan.refresh_from_db(); self.assertEqual(loan.saldo, loan.principal)
        finalize_payroll_loans(payroll)
        for loan in loans:
            loan.refresh_from_db(); self.assertEqual(loan.saldo, loan.principal - loan.monto_cuota)
        reverse_payroll_loans(payroll)
        for loan in loans:
            loan.refresh_from_db(); self.assertEqual(loan.saldo, loan.principal)

    def test_private_payslip_excludes_other_employee_and_loan_pdf_is_tenant_safe(self):
        employee = self.employee("PRIVATE", "50000")
        other = self.employee("OTHER", "200000")
        period = self.period()
        loan = prepare_loan(PrestamoEmpleado(empresa=self.company, empleado=employee, principal=Decimal("10000"), saldo=0, cuotas=5, estado="ACTIVO", primera_nomina=period), usuario=self.user)
        payroll = process_payroll(empresa=self.company, periodo=period)
        captured = {}
        def capture_pdf(title, company, story, **kwargs):
            captured["text"] = " ".join(getattr(item, "text", "") for item in story)
            return b"%PDF"
        with patch("nomina.documents._build_pdf", side_effect=capture_pdf):
            pdf = payslip_pdf(payroll.detalles.get(empleado=employee))
        text = captured["text"]
        self.assertIn("PRIVATE", text)
        self.assertNotIn("OTHER", text)
        self.assertTrue(loan_statement_pdf(loan).startswith(b"%PDF"))
        response = self.client.get(reverse("nomina:prestamo_pdf", args=[loan.pk]))
        self.assertEqual(response.status_code, 200)

    def test_loan_form_filters_cross_tenant_records(self):
        employee = self.employee("FORM", "40000")
        period = self.period()
        form = PrestamoForm(empresa=self.company)
        self.assertQuerySetEqual(form.fields["empleado"].queryset, [employee])
        self.assertQuerySetEqual(form.fields["primera_nomina"].queryset, [period])
