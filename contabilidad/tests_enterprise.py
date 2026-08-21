from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from catalogos.models import Moneda,MonedaEmpresa
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from contabilidad.models import *
from contabilidad.api import contabilizar,balanza
from rrhh.models import Departamento,Puesto,CentroTrabajo,Empleado
from nomina.models import TipoNomina,PeriodoNomina,ConceptoNomina
from nomina.services import procesar_nomina
from activos.models import CategoriaActivo,UbicacionActivo,ActivoFijo
from activos.services import ejecutar_depreciacion
from presupuesto.models import Presupuesto,EscenarioPresupuesto,LineaPresupuesto,EjecucionPresupuestaria

class AdministrativoE2E(TestCase):
 def setUp(self):
  self.u=User.objects.create_superuser("fin","fin@example.invalid","x");self.e=Empresa.objects.create(usuario=self.u,nombre="Finanzas");m=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$");self.me=MonedaEmpresa.objects.create(empresa=self.e,moneda=m,es_base=True);self.ctx=OperationContext(empresa=self.e,usuario=self.u)
  self.plan=PlanCuenta.objects.create(empresa=self.e,codigo="BASE",nombre="Base",creado_por=self.u);self.caja=CuentaContable.objects.create(empresa=self.e,plan=self.plan,codigo="1101",nombre="Caja",tipo="ACTIVO",naturaleza="DEBITO",creado_por=self.u);self.ing=CuentaContable.objects.create(empresa=self.e,plan=self.plan,codigo="4101",nombre="Ingresos",tipo="INGRESO",naturaleza="CREDITO",creado_por=self.u);self.per=PeriodoContable.objects.create(empresa=self.e,anio=2026,mes=8,fecha_inicio=date(2026,8,1),fecha_fin=date(2026,8,31),creado_por=self.u);self.dia=DiarioContable.objects.create(empresa=self.e,codigo="GENERAL",nombre="General",creado_por=self.u)
 def test_e2e_contable_balanceado_idempotente(self):
  lineas=[{"cuenta":self.caja,"debito":1000},{"cuenta":self.ing,"credito":1000}];a=contabilizar(context=self.ctx,origen_tipo="VENTA",origen_id=1,concepto="Venta",lineas=lineas,fecha=date(2026,8,2));b=contabilizar(context=self.ctx,origen_tipo="VENTA",origen_id=1,concepto="Venta",lineas=lineas,fecha=date(2026,8,2));self.assertEqual(a.pk,b.pk);self.assertEqual(a.total_debito,a.total_credito);self.assertEqual(len(balanza(empresa=self.e,periodo=self.per)),2)
 def test_e2e_nomina(self):
  d=Departamento.objects.create(empresa=self.e,codigo="ADM",nombre="Administración");p=Puesto.objects.create(empresa=self.e,codigo="A",nombre="Analista");c=CentroTrabajo.objects.create(empresa=self.e,codigo="HQ",nombre="Principal");Empleado.objects.create(empresa=self.e,codigo="E1",nombres="Ana",apellidos="Pérez",identificacion="001",puesto=p,departamento=d,centro=c,fecha_ingreso=date(2025,1,1),salario=30000);t=TipoNomina.objects.create(empresa=self.e,nombre="Mensual",periodicidad="MENSUAL");per=PeriodoNomina.objects.create(empresa=self.e,tipo=t,desde=date(2026,8,1),hasta=date(2026,8,31));ConceptoNomina.objects.create(empresa=self.e,codigo="SALARIO",nombre="Salario",tipo="INGRESO");n=procesar_nomina(empresa=self.e,periodo=per,usuario=self.u);detalle=n.detalles.get();self.assertEqual(detalle.afp_empleado,Decimal("861.00"));self.assertEqual(detalle.sfs_empleado,Decimal("912.00"));self.assertEqual(detalle.isr,Decimal("0.00"));self.assertEqual(n.total_neto,Decimal("28227.00"));self.assertGreater(detalle.aportes,0);self.assertEqual(detalle.neto,detalle.ingresos-detalle.deducciones)
 def test_e2e_activo_depreciacion(self):
  c=CategoriaActivo.objects.create(empresa=self.e,codigo="EQ",nombre="Equipo",tipo="EQUIPO",vida_util_meses=12);u=UbicacionActivo.objects.create(empresa=self.e,codigo="HQ",nombre="Principal");a=ActivoFijo.objects.create(empresa=self.e,codigo="A1",nombre="Equipo",categoria=c,ubicacion=u,fecha_adquisicion=date(2026,1,1),costo=12000,vida_util_meses=12);ds=ejecutar_depreciacion(empresa=self.e,periodo=date(2026,8,1));self.assertEqual(ds[0].monto,1000)
 def test_e2e_presupuesto_variacion(self):
  p=Presupuesto.objects.create(empresa=self.e,codigo="P26",nombre="2026",anio=2026,estado="ACTIVO");e=EscenarioPresupuesto.objects.create(presupuesto=p,tipo="BASE",nombre="Base");l=LineaPresupuesto.objects.create(escenario=e,cuenta=self.ing,monto=10000);a=contabilizar(context=self.ctx,origen_tipo="REAL",origen_id=2,concepto="Real",lineas=[{"cuenta":self.caja,"debito":8000},{"cuenta":self.ing,"credito":8000}],fecha=date(2026,8,2));EjecucionPresupuestaria.objects.create(linea=l,asiento=a,monto=8000,fecha=date(2026,8,2));from presupuesto.api import resumen;self.assertEqual(resumen(empresa=self.e,presupuesto_id=p.pk)["variacion"],"2000")
