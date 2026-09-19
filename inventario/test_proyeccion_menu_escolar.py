from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from conduces.models import (AsignacionProgramaCentro, CalendarioEscolar,
    CentroEducativo, DiaCalendarioEscolar, Empresa, ProgramaMenu,
    ProgramacionMenuEscolar, VersionProgramaMenu)
from .models import DetalleRecetaProduccion, ProductoInventario, RecetaProduccion
from .proyeccion_menu_escolar import proyectar_necesidades_menu_escolar


class ProyeccionMenuEscolarTests(TestCase):
    def setUp(self):
        usuario = get_user_model().objects.create_user("proyeccion", password="x")
        self.empresa = Empresa.objects.create(usuario=usuario, nombre="Empresa A")
        self.centro = CentroEducativo.objects.create(
            empresa=self.empresa, codigo="A", nombre="Centro A", matricula=500,
            matricula_lunes_viernes=700, matricula_fin_semana=250,
        )
        self.inicio = date(2026, 8, 24)
        self.calendario = CalendarioEscolar.objects.create(
            empresa=self.empresa, nombre="2026-27", anio_inicio=2026, anio_fin=2027,
            inicio_docencia=self.inicio, fin_docencia=self.inicio + timedelta(days=30),
            estado=CalendarioEscolar.Estado.ACTIVO,
        )
        self.programa = ProgramaMenu.objects.create(
            empresa=self.empresa, codigo="P", nombre="Regular", modalidad="REGULAR")
        self.version = VersionProgramaMenu.objects.create(
            programa=self.programa, nombre="V1", vigente_desde=self.inicio,
            fecha_ancla_ciclo=self.inicio, estado=VersionProgramaMenu.Estado.ACTIVA,
        )
        self.asignacion = AsignacionProgramaCentro.objects.create(
            centro=self.centro, programa=self.programa, modalidad="REGULAR",
            dias_entrega=list(range(7)), vigente_desde=self.inicio,
        )
        self.pan = ProductoInventario.objects.create(
            empresa=self.empresa, nombre="Pan", tipo="producto_terminado", unidad_medida="unidad")
        self.harina = ProductoInventario.objects.create(
            empresa=self.empresa, nombre="Harina", tipo="materia_prima",
            unidad_medida="lb", unidad_compra="saco",
            cantidad_por_empaque=Decimal("25"), stock_actual=Decimal("10"))
        self.receta = RecetaProduccion.objects.create(
            empresa=self.empresa, codigo="R", nombre="Pan", producto_terminado=self.pan,
            rendimiento_base=Decimal("100"), unidad_rendimiento="unidad",
            fecha_vigencia_desde=self.inicio, activa=True)
        DetalleRecetaProduccion.objects.create(
            receta=self.receta, materia_prima=self.harina,
            cantidad=Decimal("20"), unidad_medida="lb")

    def fila(self, fecha, *, centro=None, estado=ProgramacionMenuEscolar.Estado.PROGRAMADO,
             confirmada=True, docente=True):
        DiaCalendarioEscolar.objects.update_or_create(
            calendario=self.calendario, fecha=fecha,
            defaults={"clasificacion": (DiaCalendarioEscolar.Clasificacion.DOCENCIA if docente
                      else DiaCalendarioEscolar.Clasificacion.NO_LECTIVO)},
        )
        centro = centro or self.centro
        asignacion = self.asignacion if centro == self.centro else AsignacionProgramaCentro.objects.create(
            centro=centro, programa=self.programa, modalidad="REGULAR",
            dias_entrega=list(range(7)), vigente_desde=self.inicio)
        return ProgramacionMenuEscolar.objects.create(
            empresa=self.empresa, calendario=self.calendario, asignacion=asignacion,
            centro=centro, fecha=fecha, dia_semana=fecha.weekday(),
            programa=self.programa, version=self.version, producto="Pan",
            programa_snapshot="Regular", version_snapshot="V1", modalidad_snapshot="REGULAR",
            estado=estado, confirmada=confirmada,
        )

    def proyectar(self, hasta=None):
        return proyectar_necesidades_menu_escolar(
            empresa=self.empresa, desde=self.inicio, hasta=hasta or self.inicio + timedelta(days=6))

    def test_a_fecha_regular_y_fin_semana_usan_matriculas_distintas(self):
        self.fila(self.inicio)
        self.fila(self.inicio + timedelta(days=5))
        resultado = self.proyectar()
        self.assertEqual(resultado.raciones, Decimal("950"))
        trazas = resultado.necesidades[self.harina.pk].trazas
        self.assertEqual([(t.matricula, t.tipo_matricula) for t in trazas], [(700, "regular"), (250, "fin_semana")])

    def test_producto_provisional_muestra_necesidad_sin_inventar_empaques(self):
        self.harina.unidad_compra = ""
        self.harina.requiere_revision = True
        self.harina.save(update_fields=["unidad_compra", "requiere_revision"])
        self.fila(self.inicio)
        resultado = self.proyectar()
        necesidad = resultado.necesidades[self.harina.pk]
        self.assertGreater(necesidad.neta, 0)
        self.assertEqual(necesidad.empaques, 0)
        self.assertTrue(necesidad.compra_pendiente)
        self.assertTrue(any("pendiente de configuración de compra" in aviso for aviso in resultado.advertencias))

    def test_b_fallback_compatible(self):
        self.centro.matricula_lunes_viernes = None
        self.centro.matricula_fin_semana = None
        self.centro.save()
        self.fila(self.inicio)
        self.fila(self.inicio + timedelta(days=5))
        resultado = self.proyectar()
        self.assertEqual(resultado.raciones, Decimal("1000"))
        self.assertEqual({t.tipo_matricula for t in resultado.necesidades[self.harina.pk].trazas}, {"fallback"})

    def test_c_siete_fechas_suman_4000_no_4900(self):
        for n in range(7):
            self.fila(self.inicio + timedelta(days=n))
        self.assertEqual(self.proyectar().raciones, Decimal("4000"))

    def test_d_no_docente_o_no_materializado_no_cuenta(self):
        self.fila(self.inicio, docente=False)
        self.assertEqual(self.proyectar().raciones, 0)
        self.assertEqual(self.proyectar().necesidades, {})

    def test_e_consolida_dos_centros(self):
        self.fila(self.inicio)
        otro = CentroEducativo.objects.create(empresa=self.empresa, codigo="B", nombre="B", matricula=300)
        self.fila(self.inicio, centro=otro)
        self.assertEqual(self.proyectar().necesidades[self.harina.pk].bruta, Decimal("200"))

    def test_f_factor_y_cantidad_decimal(self):
        self.fila(self.inicio)
        traza = self.proyectar().necesidades[self.harina.pk].trazas[0]
        self.assertEqual(traza.factor, Decimal("7"))
        self.assertEqual(traza.cantidad, Decimal("140"))

    def test_g_stock_superior_deja_neta_cero(self):
        self.harina.stock_actual = 200
        self.harina.save(update_fields=["stock_actual"])
        self.fila(self.inicio)
        self.assertEqual(self.proyectar().necesidades[self.harina.pk].neta, 0)

    def test_h_compra_redondea_empaque_hacia_arriba_sin_mover_stock(self):
        self.fila(self.inicio)
        necesidad = self.proyectar().necesidades[self.harina.pk]
        self.assertEqual(necesidad.neta, Decimal("130"))
        self.assertEqual(necesidad.empaques, 6)
        self.harina.refresh_from_db()
        self.assertEqual(self.harina.stock_actual, Decimal("10"))

    def test_i_prepara_fin_semana_previsualizacion_si_proyecta(self):
        fecha = self.inicio + timedelta(days=5)
        programa = ProgramaMenu.objects.create(
            empresa=self.empresa, codigo='PREP', nombre='PREPARA', modalidad='PREPARA')
        version = VersionProgramaMenu.objects.create(
            programa=programa, nombre='V1', vigente_desde=self.inicio,
            fecha_ancla_ciclo=self.inicio, estado=VersionProgramaMenu.Estado.ACTIVA,
        )
        asignacion = AsignacionProgramaCentro.objects.create(
            centro=self.centro, programa=programa, modalidad='PREPARA',
            dias_entrega=[5, 6], vigente_desde=self.inicio,
        )
        DiaCalendarioEscolar.objects.create(
            calendario=self.calendario, fecha=fecha,
            clasificacion=DiaCalendarioEscolar.Clasificacion.NO_LECTIVO,
            origen='PREVISUALIZACION_CALENDARIO',
        )
        ProgramacionMenuEscolar.objects.create(
            empresa=self.empresa, calendario=self.calendario, asignacion=asignacion,
            centro=self.centro, fecha=fecha, dia_semana=fecha.weekday(),
            programa=programa, version=version, producto='Pan',
            programa_snapshot='PREPARA', version_snapshot='V1',
            modalidad_snapshot='PREPARA',
            estado=ProgramacionMenuEscolar.Estado.PROGRAMADO, confirmada=True,
        )
        resultado = proyectar_necesidades_menu_escolar(
            empresa=self.empresa, desde=fecha, hasta=fecha)
        self.assertEqual(resultado.raciones, Decimal('250'))
        self.assertIn(self.harina.pk, resultado.necesidades)
        self.assertEqual(resultado.necesidades[self.harina.pk].bruta, Decimal('50'))

    def test_j_prepara_suspension_real_no_proyecta(self):
        fecha = self.inicio + timedelta(days=5)
        programa = ProgramaMenu.objects.create(
            empresa=self.empresa, codigo='PREP', nombre='PREPARA', modalidad='PREPARA')
        version = VersionProgramaMenu.objects.create(
            programa=programa, nombre='V1', vigente_desde=self.inicio,
            fecha_ancla_ciclo=self.inicio, estado=VersionProgramaMenu.Estado.ACTIVA,
        )
        asignacion = AsignacionProgramaCentro.objects.create(
            centro=self.centro, programa=programa, modalidad='PREPARA',
            dias_entrega=[5, 6], vigente_desde=self.inicio,
        )
        DiaCalendarioEscolar.objects.create(
            calendario=self.calendario, fecha=fecha,
            clasificacion=DiaCalendarioEscolar.Clasificacion.SUSPENSION,
            origen='MANUAL',
        )
        ProgramacionMenuEscolar.objects.create(
            empresa=self.empresa, calendario=self.calendario, asignacion=asignacion,
            centro=self.centro, fecha=fecha, dia_semana=fecha.weekday(),
            programa=programa, version=version, producto='Pan',
            programa_snapshot='PREPARA', version_snapshot='V1',
            modalidad_snapshot='PREPARA',
            estado=ProgramacionMenuEscolar.Estado.PROGRAMADO, confirmada=True,
        )
        resultado = proyectar_necesidades_menu_escolar(
            empresa=self.empresa, desde=fecha, hasta=fecha)
        self.assertEqual(resultado.raciones, Decimal('0'))
        self.assertEqual(resultado.necesidades, {})

    def test_solo_confirmada_y_misma_empresa(self):
        self.fila(self.inicio, confirmada=False)
        self.assertEqual(self.proyectar().raciones, 0)
        otro = Empresa.objects.create(usuario=get_user_model().objects.create_user("otro"), nombre="Otra")
        self.assertEqual(proyectar_necesidades_menu_escolar(
            empresa=otro, desde=self.inicio, hasta=self.inicio).raciones, 0)
