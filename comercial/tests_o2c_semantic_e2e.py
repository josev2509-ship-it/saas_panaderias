from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from auditoria.models import EventoAuditoria
from core.models import EventoDominio
from contabilidad.api import contabilizar
from contabilidad.models import CuentaContable, DimensionContable, ValorDimensionContable, ReglaContabilizacion, AsientoContable
from comercial.models import FacturaVenta, CuentaPorCobrar
from comercial.application.o2c_full import registrar_cobro, aplicar_cobro, solicitar_factoring, avanzar_factoring
from comercial.application.financial_integration import contabilizar_factura_emitida, integrar_cobro, emitir_nota_credito_integrada, emitir_nota_debito_integrada, desembolsar_factoring
from comercial.api.finanzas import dashboard
from contabilidad.reportes import mayor, estado_resultados, balance_general
from tesoreria.api import flujo
from tesoreria.models import ConciliacionBancaria
from tesoreria.services import importar_extracto, sugerir_coincidencias, conciliar_linea, completar_conciliacion

from comercial.tests_o2c_multicurrency_flows import O2CMulticurrencyFlowsTest


class O2CSemanticE2ETest(O2CMulticurrencyFlowsTest):
    def test_e2e_semantico_unico_20_pasos(self):
        # 1-3 Empresa DOP base, USD y tasa vigente fueron creadas en setUp.
        # 4 Cuentas y reglas configurables.
        plan=CuentaContable.objects.filter(empresa=self.empresa).first().plan
        for code,name,t,n in (("1301","Retención","ACTIVO","DEBITO"),("6101","Gasto financiero","GASTO","DEBITO")):
            CuentaContable.objects.create(empresa=self.empresa,plan=plan,codigo=code,nombre=name,tipo=t,naturaleza=n,creado_por=self.user)
        for event,cfg in (("FACTURA_VENTA",{"debito":"1201","credito":"4101"}),("NOTA_CREDITO_VENTA",{"debito":"4101","credito":"1201"}),("FACTORING",{"banco":"1102","gasto":"6101","retencion":"1301","cxc":"1201"})):
            ReglaContabilizacion.objects.create(empresa=self.empresa,evento=event,configuracion=cfg,creado_por=self.user)
        # 5-7 Centro, proyecto y sucursal reales.
        dims={}
        for code in ("CENTRO_COSTO","PROYECTO","SUCURSAL"):
            dimension=DimensionContable.objects.create(empresa=self.empresa,codigo=code,nombre=code,creado_por=self.user);value=ValorDimensionContable.objects.create(empresa=self.empresa,dimension=dimension,codigo=code[:3],nombre=code,creado_por=self.user);dims[code]=value.pk
        # 8 Cliente creado en setUp.
        # 9 Factura USD emitida por POST con CSRF válido.
        factura=FacturaVenta.objects.create(empresa=self.empresa,numero="E2E-USD",cliente=self.client,moneda=self.usd,tasa_cambio=60,dimensiones=dims,fecha=date(2026,8,2),vence_el=date(2026,9,2),estado="BORRADOR",total=100,creado_por=self.user)
        http=Client(enforce_csrf_checks=True);http.force_login(self.user);http.cookies["csrftoken"]="a"*32
        self.assertEqual(http.post(reverse("comercial:fin_factura_emitir",kwargs={"pk":factura.pk}),HTTP_X_CSRFTOKEN="a"*32).status_code,200);factura.refresh_from_db()
        # 10 Contabilización e idempotencia inicial.
        asiento_factura=contabilizar_factura_emitida(context=self.ctx,factura_id=factura.pk);self.assertEqual(asiento_factura.asiento_id,contabilizar_factura_emitida(context=self.ctx,factura_id=factura.pk).asiento_id)
        # 11 Cobro parcial USD.
        usd=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.usd,monto=20,metodo="TRANSFERENCIA",tasa_cambio=61,dimensiones=dims);aplicar_cobro(context=self.ctx,recibo_id=usd.pk,cuenta_id=factura.cuenta_cobrar.pk,monto=20,monto_cuenta=20);integrar_cobro(context=self.ctx,recibo_id=usd.pk,cuenta_bancaria_id=self.bank_usd.pk)
        # 12 Cobro parcial DOP con diferencia cambiaria.
        dop=registrar_cobro(context=self.ctx,cliente=self.client,moneda=self.dop,monto=1220,metodo="TRANSFERENCIA",fecha=date(2026,8,2),dimensiones=dims);aplicar_cobro(context=self.ctx,recibo_id=dop.pk,cuenta_id=factura.cuenta_cobrar.pk,monto=1220,monto_cuenta=20);integrar_cobro(context=self.ctx,recibo_id=dop.pk,cuenta_bancaria_id=self.bank_dop.pk)
        # 13-14 Notas heredan snapshot y dimensiones.
        nc=emitir_nota_credito_integrada(context=self.ctx,factura_id=factura.pk,monto=10,motivo="NC E2E");nd=emitir_nota_debito_integrada(context=self.ctx,factura_id=factura.pk,monto=5,motivo="ND E2E");self.assertTrue(nc["nota_id"] and nd["nota_id"])
        # 15 Factoring parcial sobre otra factura.
        segunda=self.invoice("E2E-FAC",total=200,dims=dims);cesion=solicitar_factoring(context=self.ctx,cuenta_id=segunda.cuenta_cobrar.pk,factor="Factor E2E",porcentaje=80,monto=100);cesion=avanzar_factoring(context=self.ctx,pk=cesion.pk,estado="APROBADA")
        # 16 Desembolso.
        desembolso=desembolsar_factoring(context=self.ctx,cesion_id=cesion.pk,cuenta_bancaria_id=self.bank_usd.pk,comision=2,costo_financiero=2,retencion=1,referencia="FAC-E2E");self.assertEqual(desembolso["neto"],"95.00")
        # 17 Importación y conciliación del cobro DOP.
        csv=f"fecha,descripcion,referencia,debito,credito,saldo\n2026-08-02,Cobro,COBRO_O2C:{dop.pk},0,1220,1220\n";imp=importar_extracto(context=self.ctx,cuenta=self.bank_dop,contenido=csv,nombre_archivo="e2e.csv",confirmar=True);match=sugerir_coincidencias(context=self.ctx,importacion=imp)[0];conc=ConciliacionBancaria.objects.create(empresa=self.empresa,cuenta=self.bank_dop,desde=date(2026,8,2),hasta=date(2026,8,2),saldo_banco=1220,saldo_libros=1220);conciliar_linea(context=self.ctx,conciliacion=conc,linea_id=match["linea_id"],movimiento_id=match["movimiento_id"]);completar_conciliacion(context=self.ctx,conciliacion=conc)
        # 18 Mayor por centro y resultados por proyecto.
        self.assertTrue(mayor(empresa=self.empresa,centro=dims["CENTRO_COSTO"]));self.assertIn("resultado",estado_resultados(empresa=self.empresa,proyecto=dims["PROYECTO"]))
        # 19 Balance, flujo y dashboard por moneda.
        self.assertIn("activo",balance_general(empresa=self.empresa));self.assertIsInstance(flujo(empresa=self.empresa,desde=date(2026,8,1),hasta=date(2026,8,31)),list);self.assertIn("facturado",dashboard(empresa=self.empresa))
        # 20 Reintento idempotente y rollback por tasa inválida.
        before=AsientoContable.objects.count()
        with self.assertRaises(ValidationError):contabilizar(context=self.ctx,origen_tipo="INVALID_RATE",origen_id="1",concepto="Inválida",lineas=[{"cuenta":"1201","debito":1},{"cuenta":"4101","credito":1}],fecha=date(2026,8,2),moneda=self.usd,tasa_cambio=999)
        self.assertEqual(AsientoContable.objects.count(),before);self.assertTrue(EventoDominio.objects.filter(empresa=self.empresa).exists());self.assertTrue(EventoAuditoria.objects.filter(empresa=self.empresa).exists())
