from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase

from catalogos.models import Moneda, MonedaEmpresa
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from core.models import EventoDominio
from tesoreria.models import ConciliacionBancaria, CuentaBancariaEmpresa, ImportacionExtractoBancario, LineaExtractoBancario, MovimientoTesoreria
from tesoreria.services import conciliar_linea, desconciliar_linea, importar_csv, importar_extracto, sugerir_coincidencias

from .api import contabilizar
from .models import CuentaContable, DiarioContable, PeriodoContable, PlanCuenta
from .services import cerrar_periodo, reabrir_periodo, revertir_asiento


class FinancialServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("controller", "controller@example.invalid", "x")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Empresa financiera")
        moneda = Moneda.objects.create(codigo="DOP", nombre="Peso", simbolo="$")
        self.moneda = MonedaEmpresa.objects.create(empresa=self.empresa, moneda=moneda, es_base=True)
        self.context = OperationContext(empresa=self.empresa, usuario=self.user)
        plan = PlanCuenta.objects.create(empresa=self.empresa, codigo="BASE", nombre="Base", creado_por=self.user)
        self.debito = CuentaContable.objects.create(empresa=self.empresa, plan=plan, codigo="1101", nombre="Banco", tipo="ACTIVO", naturaleza="DEBITO", creado_por=self.user)
        self.credito = CuentaContable.objects.create(empresa=self.empresa, plan=plan, codigo="4101", nombre="Ingreso", tipo="INGRESO", naturaleza="CREDITO", creado_por=self.user)
        self.periodo = PeriodoContable.objects.create(empresa=self.empresa, anio=2026, mes=8, fecha_inicio=date(2026, 8, 1), fecha_fin=date(2026, 8, 31), creado_por=self.user)
        self.diario = DiarioContable.objects.create(empresa=self.empresa, codigo="GENERAL", nombre="General", creado_por=self.user)

    def asiento(self):
        return contabilizar(context=self.context, origen_tipo="PRUEBA", origen_id=1, concepto="Prueba", fecha=date(2026, 8, 2), lineas=[{"cuenta": self.debito, "debito": 100}, {"cuenta": self.credito, "credito": 100}])

    def test_cierre_reapertura_idempotentes_y_auditados(self):
        self.asiento()
        cierre = cerrar_periodo(context=self.context, periodo=self.periodo, motivo="Cierre mensual")
        self.assertEqual(cierre.pk, cerrar_periodo(context=self.context, periodo=self.periodo).pk)
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, "CERRADO")
        reabrir_periodo(context=self.context, periodo=self.periodo, motivo="Ajuste autorizado")
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, "ABIERTO")
        self.assertTrue(EventoDominio.objects.filter(empresa=self.empresa, tipo_evento="PeriodoCerrado").exists())

    def test_reversion_balanceada_e_idempotente(self):
        asiento = self.asiento()
        reversa = revertir_asiento(context=self.context, asiento=asiento, motivo="Corrección")
        segunda = revertir_asiento(context=self.context, asiento=asiento, motivo="Corrección")
        self.assertEqual(reversa.pk, segunda.pk)
        self.assertEqual(reversa.total_debito, reversa.total_credito)

    def test_importacion_bancaria_preview_confirmacion_y_duplicados(self):
        cuenta = CuentaBancariaEmpresa.objects.create(empresa=self.empresa, banco="Banco", numero_enmascarado="****1234", moneda=self.moneda)
        csv = "fecha,descripcion,referencia,debito,credito,saldo\n2026-08-02,Venta,REF-1,0,150.25,150.25\n"
        self.assertEqual(len(importar_csv(empresa=self.empresa, cuenta=cuenta, contenido=csv)), 1)
        primera = importar_csv(empresa=self.empresa, cuenta=cuenta, contenido=csv, usuario=self.user, confirmar=True)
        segunda = importar_csv(empresa=self.empresa, cuenta=cuenta, contenido=csv, usuario=self.user, confirmar=True)
        self.assertEqual(primera.pk, segunda.pk)
        self.assertEqual(ImportacionExtractoBancario.objects.filter(empresa=self.empresa).count(), 1)
        self.assertEqual(LineaExtractoBancario.objects.filter(importacion=primera).count(), 1)

    def test_roles_no_cruzan_dominios_administrativos(self):
        call_command("configurar_roles_administrativos")
        rrhh = Group.objects.get(name="Administrador RRHH")
        self.assertFalse(rrhh.permissions.filter(content_type__app_label="contabilidad").exists())
        self.assertTrue(rrhh.permissions.filter(content_type__app_label="rrhh").exists())

    def test_adaptadores_workflow_productivos_registrados(self):
        from workflow.domain.adapters import adapter_registry
        claves = ("contabilidad.asiento_manual", "contabilidad.cierre", "contabilidad.reapertura", "contabilidad.solicitud_pago", "contabilidad.orden_pago", "contabilidad.anticipo", "rrhh.vacaciones", "rrhh.horas_extra", "nomina.nomina", "nomina.liquidacion", "activos.alta", "activos.baja", "activos.revaluacion", "mantenimiento.alto_costo", "contabilidad.gasto_extraordinario", "contabilidad.aporte_socio", "contabilidad.prestamo_socio")
        for clave in claves:
            self.assertIsNotNone(adapter_registry.get(clave))

    def test_xlsx_matching_y_desconciliacion_controlada(self):
        from openpyxl import Workbook
        cuenta = CuentaBancariaEmpresa.objects.create(empresa=self.empresa, banco="Banco", numero_enmascarado="****9876", moneda=self.moneda)
        movimiento = MovimientoTesoreria.objects.create(empresa=self.empresa, cuenta=cuenta, tipo="INGRESO", fecha=date(2026, 8, 5), monto=Decimal("250.00"), referencia="DEP-25")
        libro = Workbook()
        hoja = libro.active
        hoja.append(["fecha", "descripcion", "referencia", "debito", "credito", "saldo"])
        hoja.append([date(2026, 8, 5), "Depósito", "DEP-25", 0, 250, 250])
        contenido = BytesIO()
        libro.save(contenido)
        importacion = importar_extracto(context=self.context, cuenta=cuenta, contenido=contenido.getvalue(), nombre_archivo="banco.xlsx", confirmar=True)
        sugerencia = sugerir_coincidencias(context=self.context, importacion=importacion)[0]
        self.assertEqual(sugerencia["tipo"], "REFERENCIA")
        conciliacion = ConciliacionBancaria.objects.create(empresa=self.empresa, cuenta=cuenta, desde=date(2026, 8, 1), hasta=date(2026, 8, 31), saldo_banco=250, saldo_libros=250)
        linea = conciliar_linea(context=self.context, conciliacion=conciliacion, linea_id=sugerencia["linea_id"], movimiento_id=movimiento.pk, tipo=sugerencia["tipo"])
        movimiento.refresh_from_db()
        self.assertTrue(movimiento.conciliado)
        desconciliar_linea(context=self.context, linea_id=linea.pk, motivo="Corrección")
        movimiento.refresh_from_db()
        self.assertFalse(movimiento.conciliado)
