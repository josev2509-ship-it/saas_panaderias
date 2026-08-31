from datetime import date, timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from conduces.menu_planning import (
    activar_calendario,
    aplicar_excepcion,
    contar_docencia_regular,
    materializar_programacion,
    previsualizar_asignacion,
    semana_ciclo,
    version_vigente,
)
from conduces.models import (
    AsignacionProgramaCentro,
    CalendarioEscolar,
    CentroEducativo,
    DiaCalendarioEscolar,
    Empresa,
    ItemCicloMenu,
    ProgramaMenu,
    ProgramacionMenuEscolar,
    VersionProgramaMenu,
)


class MenuPlanningTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("planificador", password="x")
        self.empresa = Empresa.objects.create(usuario=self.user, nombre="Panaderia A", modulo_menu=True)
        self.user.user_permissions.add(Permission.objects.get(codename="change_programamenu"))
        self.centro = CentroEducativo.objects.create(
            empresa=self.empresa, codigo="A-1", nombre="Centro A", matricula=100
        )
        self.calendario = CalendarioEscolar.objects.create(
            empresa=self.empresa,
            nombre="2026-2027",
            anio_inicio=2026,
            anio_fin=2027,
            inicio_docencia=date(2026, 8, 24),
            fin_docencia=date(2026, 9, 6),
            dias_docencia_oficiales=9,
            estado=CalendarioEscolar.Estado.ACTIVO,
        )
        fecha = self.calendario.inicio_docencia
        while fecha <= self.calendario.fin_docencia:
            DiaCalendarioEscolar.objects.create(
                calendario=self.calendario,
                fecha=fecha,
                clasificacion=(
                    DiaCalendarioEscolar.Clasificacion.DOCENCIA
                    if fecha.weekday() < 5
                    else DiaCalendarioEscolar.Clasificacion.NO_LECTIVO
                ),
            )
            fecha += timedelta(days=1)
        self.programa = ProgramaMenu.objects.create(
            empresa=self.empresa, codigo="URB-V2", nombre="PAE Urbano V2", modalidad=ProgramaMenu.Modalidad.REGULAR
        )
        self.version = VersionProgramaMenu.objects.create(
            programa=self.programa,
            nombre="V1",
            vigente_desde=date(2026, 8, 24),
            semanas_ciclo=5,
            fecha_ancla_ciclo=date(2026, 8, 24),
            semana_inicial=1,
            estado=VersionProgramaMenu.Estado.ACTIVA,
        )
        productos = ("Pan", "Galleta", "Muffin", "Pan integral", "Bizcocho")
        for semana in range(1, 6):
            for dia in range(5):
                ItemCicloMenu.objects.create(
                    version=self.version,
                    semana=semana,
                    dia_semana=dia,
                    producto=f"{productos[dia]} S{semana}",
                )
        self.asignacion = AsignacionProgramaCentro.objects.create(
            centro=self.centro,
            programa=self.programa,
            modalidad=ProgramaMenu.Modalidad.REGULAR,
            dias_entrega=[0, 1, 2, 3, 4],
            vigente_desde=date(2026, 8, 24),
            creado_por=self.user,
        )

    def test_conteo_regular_excluye_sabado_y_domingo(self):
        sabado = self.calendario.dias.get(fecha=date(2026, 8, 29))
        sabado.clasificacion = DiaCalendarioEscolar.Clasificacion.DOCENCIA
        sabado.save()
        self.assertEqual(contar_docencia_regular(self.calendario), 10)

    def test_calendario_no_activa_si_conteo_no_coincide(self):
        self.calendario.estado = CalendarioEscolar.Estado.EN_REVISION
        self.calendario.dias_docencia_oficiales = 190
        self.calendario.save()
        with self.assertRaises(ValidationError):
            activar_calendario(self.calendario, usuario=self.user)

    def test_feriado_no_desplaza_producto_del_miercoles(self):
        martes = self.calendario.dias.get(fecha=date(2026, 8, 25))
        martes.clasificacion = DiaCalendarioEscolar.Clasificacion.FERIADO
        martes.save()
        filas = previsualizar_asignacion(
            self.asignacion, self.calendario, date(2026, 8, 24), date(2026, 8, 28)
        )
        self.assertEqual(len([f for f in filas if f.estado == ProgramacionMenuEscolar.Estado.PROGRAMADO]), 4)
        self.assertEqual(filas[1].estado, ProgramacionMenuEscolar.Estado.SIN_DOCENCIA)
        self.assertEqual(filas[2].producto, "Muffin S1")

    def test_ciclo_semana_cinco_regresa_a_uno_por_semana_calendario(self):
        self.assertEqual(semana_ciclo(self.version, date(2026, 9, 21)), 5)
        self.assertEqual(semana_ciclo(self.version, date(2026, 9, 28)), 1)

    def test_version_vigente_respeta_cambio_de_fecha(self):
        self.version.vigente_hasta = date(2026, 8, 31)
        self.version.save()
        v2 = VersionProgramaMenu.objects.create(
            programa=self.programa, nombre="V2", vigente_desde=date(2026, 9, 1),
            semanas_ciclo=5, fecha_ancla_ciclo=date(2026, 9, 1), semana_inicial=1,
            estado=VersionProgramaMenu.Estado.ACTIVA,
        )
        self.assertEqual(version_vigente(self.programa, date(2026, 8, 31)), self.version)
        self.assertEqual(version_vigente(self.programa, date(2026, 9, 1)), v2)

    def test_reiniciar_y_semana_especifica_son_deterministas(self):
        self.assertEqual(semana_ciclo(self.version, self.version.fecha_ancla_ciclo), 1)
        self.version.semana_inicial = 3
        self.version.modo_inicio_ciclo = VersionProgramaMenu.InicioCiclo.ESPECIFICA
        self.assertEqual(semana_ciclo(self.version, self.version.fecha_ancla_ciclo), 3)

    def test_materializacion_preserva_snapshot_historico(self):
        filas = materializar_programacion(
            self.asignacion, self.calendario, usuario=self.user,
            fecha_inicio=date(2026, 8, 24), fecha_fin=date(2026, 8, 24),
        )
        fila = filas[0]
        nombre = fila.version_snapshot
        self.version.nombre = "V1 renombrada"
        self.version.save()
        fila.refresh_from_db()
        self.assertEqual(fila.version_snapshot, nombre)

    def test_materializacion_no_genera_producto_en_fecha_excluida(self):
        dia = self.calendario.dias.get(fecha=date(2026, 8, 25))
        dia.clasificacion = DiaCalendarioEscolar.Clasificacion.SUSPENSION
        dia.save()
        filas = materializar_programacion(
            self.asignacion, self.calendario, usuario=self.user,
            fecha_inicio=dia.fecha, fecha_fin=dia.fecha,
        )
        self.assertEqual(filas[0].estado, ProgramacionMenuEscolar.Estado.SIN_DOCENCIA)
        self.assertEqual(filas[0].producto, "")

    def test_bebida_no_suministrada_no_genera_producto_operativo(self):
        item = self.version.items.get(semana=1, dia_semana=0)
        item.producto = "Leche"
        item.es_suministrado = False
        item.save()
        fila = previsualizar_asignacion(
            self.asignacion, self.calendario, date(2026, 8, 24), date(2026, 8, 24)
        )[0]
        self.assertEqual(fila.estado, ProgramacionMenuEscolar.Estado.NO_SUMINISTRADO)
        self.assertEqual(fila.producto, "")

    def test_prepara_es_independiente_y_no_desplaza_sabado_a_domingo(self):
        prepara = ProgramaMenu.objects.create(
            empresa=self.empresa, codigo="PREPARA", nombre="PAE PREPARA", modalidad=ProgramaMenu.Modalidad.PREPARA
        )
        version = VersionProgramaMenu.objects.create(
            programa=prepara, nombre="P1", vigente_desde=date(2026, 8, 24), semanas_ciclo=2,
            fecha_ancla_ciclo=date(2026, 8, 24), estado=VersionProgramaMenu.Estado.ACTIVA,
        )
        ItemCicloMenu.objects.create(version=version, semana=1, dia_semana=5, producto="Pan sabado")
        ItemCicloMenu.objects.create(version=version, semana=1, dia_semana=6, producto="Galleta domingo")
        asignacion = AsignacionProgramaCentro.objects.create(
            centro=self.centro, programa=prepara, modalidad=ProgramaMenu.Modalidad.PREPARA,
            dias_entrega=[5, 6], vigente_desde=date(2026, 8, 24),
        )
        sabado = self.calendario.dias.get(fecha=date(2026, 8, 29))
        domingo = self.calendario.dias.get(fecha=date(2026, 8, 30))
        sabado.clasificacion = DiaCalendarioEscolar.Clasificacion.FERIADO; sabado.save()
        domingo.clasificacion = DiaCalendarioEscolar.Clasificacion.DOCENCIA; domingo.save()
        filas = previsualizar_asignacion(asignacion, self.calendario, sabado.fecha, domingo.fecha)
        self.assertEqual(filas[0].estado, ProgramacionMenuEscolar.Estado.SIN_DOCENCIA)
        self.assertEqual(filas[1].producto, "Galleta domingo")
        self.assertEqual(contar_docencia_regular(self.calendario), 10)

    def test_asignacion_rechaza_programa_de_otra_empresa(self):
        otro = Empresa.objects.create(nombre="Empresa B")
        programa = ProgramaMenu.objects.create(empresa=otro, codigo="B", nombre="B", modalidad="REGULAR")
        asignacion = AsignacionProgramaCentro(
            centro=self.centro, programa=programa, modalidad="REGULAR", dias_entrega=[0],
            vigente_desde=date(2026, 8, 24),
        )
        with self.assertRaises(ValidationError):
            asignacion.full_clean()

    def test_preview_rechaza_calendario_de_otra_empresa(self):
        otro = Empresa.objects.create(nombre="Empresa B")
        calendario = CalendarioEscolar.objects.create(
            empresa=otro, nombre="B", anio_inicio=2026, anio_fin=2027,
            inicio_docencia=date(2026, 8, 24), fin_docencia=date(2026, 8, 25),
        )
        with self.assertRaises(ValidationError):
            previsualizar_asignacion(self.asignacion, calendario)

    def test_override_auditable_y_bloqueo_historico(self):
        fila = materializar_programacion(
            self.asignacion, self.calendario, usuario=self.user,
            fecha_inicio=date(2026, 8, 24), fecha_fin=date(2026, 8, 24),
        )[0]
        excepcion = aplicar_excepcion(
            fila, usuario=self.user, estado_nuevo=ProgramacionMenuEscolar.Estado.EXTRAORDINARIO,
            producto_nuevo="Pan especial", motivo="Orden extraordinaria",
        )
        self.assertEqual(excepcion.producto_anterior, "Pan S1")
        fila.refresh_from_db(); self.assertEqual(fila.producto, "Pan especial")
        fila.bloqueada = True; fila.save()
        with self.assertRaises(ValidationError):
            aplicar_excepcion(fila, usuario=self.user, estado_nuevo="OMITIDO", motivo="Prueba")

    def test_exportaciones_excel_pdf_y_rango(self):
        materializar_programacion(
            self.asignacion, self.calendario, usuario=self.user,
            fecha_inicio=date(2026, 8, 24), fecha_fin=date(2026, 8, 25),
        )
        self.client.force_login(self.user)
        excel = self.client.get(reverse("exportar_programacion_excel"), {"fecha_inicio": "2026-08-25", "fecha_fin": "2026-08-25"})
        self.assertEqual(excel.status_code, 200)
        ws = load_workbook(BytesIO(excel.content)).active
        self.assertEqual(ws.max_row, 2)
        pdf = self.client.get(reverse("exportar_programacion_pdf"), {"fecha_inicio": "2026-08-25", "fecha_fin": "2026-08-25"})
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(b"".join(pdf.streaming_content)[:4], b"%PDF")

    def test_usuario_no_autorizado_no_modifica_y_empresa_ajena_no_se_exporta(self):
        otro_usuario = get_user_model().objects.create_user("consulta")
        otra_empresa = Empresa.objects.create(usuario=otro_usuario, nombre="Empresa B", modulo_menu=True)
        self.client.force_login(otro_usuario)
        response = self.client.post(reverse("crear_programa_menu"), {"codigo": "X", "nombre": "X", "modalidad": "REGULAR"})
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse("exportar_programacion_excel"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Panaderia A", response.content)
        self.assertNotEqual(otra_empresa.pk, self.empresa.pk)
