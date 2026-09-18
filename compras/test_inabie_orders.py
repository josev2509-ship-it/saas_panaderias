from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from catalogos.models import Moneda, MonedaEmpresa
from conduces.models import (AsignacionProgramaCentro, CalendarioEscolar,
    CentroEducativo, DiaCalendarioEscolar, Empresa, EmpresaSaaS, PerfilUsuario, ProgramaMenu,
    ProgramacionMenuEscolar, VersionProgramaMenu)
from core.application.operation_context import OperationContext
from inventario.models import (DetalleRecetaProduccion, MovimientoInventario,
    ProductoInventario, RecetaProduccion)
from .application.inabie_orders import (agregar_linea_inabie,
    editar_borrador_inabie, editar_linea_inabie, eliminar_linea_inabie,
    generar_borrador_inabie)
from .application.p2p import crear_recepcion, transicionar_orden
from .models import OrdenCompraEnterprise, Proveedor


class InabieOrderDraftTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user("comprador", password="x")
        self.empresa = Empresa.objects.create(usuario=self.usuario, nombre="Panadería A",
                                              modulo_compras=True, modulo_inabie=True)
        self.usuario.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="compras", codename__in=(
                "add_ordencompraenterprise", "change_ordencompraenterprise",
                "view_ordencompraenterprise", "cancelar_orden_compra")))
        self.ctx = OperationContext(empresa=self.empresa, usuario=self.usuario,
                                    clave_idempotente="inabie-test")
        self.desde = date(2026, 8, 24)
        moneda = Moneda.objects.create(codigo="DOP", nombre="Peso", simbolo="RD$")
        self.moneda = MonedaEmpresa.objects.create(empresa=self.empresa, moneda=moneda,
                                                  activa=True, es_base=True)
        self.centro = CentroEducativo.objects.create(
            empresa=self.empresa, codigo="C", nombre="Centro", matricula=500,
            matricula_lunes_viernes=700, matricula_fin_semana=250)
        self.calendario = CalendarioEscolar.objects.create(
            empresa=self.empresa, nombre="2026-27", anio_inicio=2026, anio_fin=2027,
            inicio_docencia=self.desde, fin_docencia=date(2026, 9, 30),
            estado=CalendarioEscolar.Estado.ACTIVO)
        self.programa = ProgramaMenu.objects.create(
            empresa=self.empresa, codigo="R", nombre="Regular", modalidad="REGULAR")
        self.version = VersionProgramaMenu.objects.create(
            programa=self.programa, nombre="V1", vigente_desde=self.desde,
            fecha_ancla_ciclo=self.desde, estado=VersionProgramaMenu.Estado.ACTIVA)
        self.asignacion = AsignacionProgramaCentro.objects.create(
            centro=self.centro, programa=self.programa, modalidad="REGULAR",
            dias_entrega=list(range(7)), vigente_desde=self.desde)
        self.pan = ProductoInventario.objects.create(
            empresa=self.empresa, nombre="Pan", tipo="producto_terminado", unidad_medida="unidad")
        self.harina = ProductoInventario.objects.create(
            empresa=self.empresa, nombre="Harina", tipo="materia_prima", unidad_medida="lb",
            stock_actual=Decimal("10"), cantidad_por_empaque=Decimal("25"),
            precio_unitario_compra=Decimal("100"))
        receta = RecetaProduccion.objects.create(
            empresa=self.empresa, codigo="R1", nombre="Pan", producto_terminado=self.pan,
            rendimiento_base=Decimal("100"), unidad_rendimiento="unidad",
            fecha_vigencia_desde=self.desde, activa=True)
        DetalleRecetaProduccion.objects.create(receta=receta, materia_prima=self.harina,
                                               cantidad=Decimal("20"), unidad_medida="lb")
        self.proveedor = Proveedor.objects.create(
            empresa=self.empresa, codigo="P1", tipo_persona="JURIDICA",
            razon_social="Proveedor", estado="ACTIVO", creado_por=self.usuario)

    def fila(self, fecha):
        DiaCalendarioEscolar.objects.create(calendario=self.calendario, fecha=fecha,
            clasificacion=DiaCalendarioEscolar.Clasificacion.DOCENCIA)
        return ProgramacionMenuEscolar.objects.create(
            empresa=self.empresa, calendario=self.calendario, asignacion=self.asignacion,
            centro=self.centro, fecha=fecha, dia_semana=fecha.weekday(),
            programa=self.programa, version=self.version, producto="Pan",
            programa_snapshot="Regular", version_snapshot="V1", modalidad_snapshot="REGULAR",
            estado=ProgramacionMenuEscolar.Estado.PROGRAMADO, confirmada=True)

    def generar(self, hasta=None):
        return generar_borrador_inabie(context=self.ctx, desde=self.desde, hasta=hasta or self.desde)

    def test_01_02_03_04_borrador_por_fechas_y_matricula(self):
        self.fila(self.desde)
        self.fila(date(2026, 8, 29))
        orden, creada = self.generar(date(2026, 8, 29))
        linea = orden.detalles.get()
        self.assertTrue(creada)
        self.assertEqual(orden.estado, "BORRADOR")
        self.assertIsNone(orden.proveedor)
        self.assertEqual(linea.necesidad_base, Decimal("190"))
        self.assertEqual(linea.disponible_base, Decimal("10"))
        self.assertEqual(linea.sugerido_base, Decimal("180"))
        self.assertEqual(linea.empaques_sugeridos, 8)
        self.assertEqual(linea.cantidad, 8)
        self.assertEqual([t["matricula"] for t in linea.traza], [700, 250])
        self.assertEqual(orden.moneda, self.moneda)
        self.assertEqual((orden.origen, orden.periodo_desde, orden.periodo_hasta),
                         ("INABIE", self.desde, date(2026, 8, 29)))

    def test_05_06_07_08_12_borrador_editable_sin_movimiento(self):
        self.fila(self.desde)
        orden, _ = self.generar()
        linea = orden.detalles.get()
        editar_borrador_inabie(context=self.ctx, orden_id=orden.pk, observaciones="Revisar precio")
        editar_linea_inabie(context=self.ctx, orden_id=orden.pk, linea_id=linea.pk, cantidad=0)
        linea.refresh_from_db()
        self.assertEqual(linea.cantidad, 0)
        extra = agregar_linea_inabie(context=self.ctx, orden_id=orden.pk,
                                    producto_id=self.harina.pk, cantidad=2)
        self.assertEqual(extra.origen, "MANUAL")
        eliminar_linea_inabie(context=self.ctx, orden_id=orden.pk, linea_id=linea.pk)
        self.assertEqual(orden.detalles.count(), 1)
        transicionar_orden(context=self.ctx, orden_id=orden.pk, nuevo="CANCELADA")
        self.harina.refresh_from_db()
        self.assertEqual(self.harina.stock_actual, Decimal("10"))
        self.assertEqual(MovimientoInventario.objects.filter(empresa=self.empresa).count(), 0)

    def test_09_10_11_13_transiciones_e_idempotencia(self):
        self.fila(self.desde)
        orden, _ = self.generar()
        repetida, creada = self.generar()
        self.assertFalse(creada)
        self.assertEqual(repetida.pk, orden.pk)
        self.assertEqual(OrdenCompraEnterprise.objects.filter(empresa=self.empresa).count(), 1)
        with self.assertRaises(ValidationError):
            transicionar_orden(context=self.ctx, orden_id=orden.pk, nuevo="PENDIENTE_APROBACION")
        editar_borrador_inabie(context=self.ctx, orden_id=orden.pk,
                              proveedor_id=self.proveedor.pk)
        transicionar_orden(context=self.ctx, orden_id=orden.pk, nuevo="PENDIENTE_APROBACION")
        transicionar_orden(context=self.ctx, orden_id=orden.pk, nuevo="APROBADA")
        orden.refresh_from_db()
        self.assertEqual(orden.estado, "APROBADA")

    def test_cubierto_por_stock_permanece_visible_con_cero(self):
        self.harina.stock_actual = 200
        self.harina.save(update_fields=["stock_actual"])
        self.fila(self.desde)
        orden, _ = self.generar()
        linea = orden.detalles.get()
        self.assertEqual(linea.necesidad_base, Decimal("140"))
        self.assertEqual(linea.disponible_base, Decimal("200"))
        self.assertEqual(linea.sugerido_base, 0)
        self.assertEqual(linea.cantidad, 0)
        editar_borrador_inabie(context=self.ctx, orden_id=orden.pk, proveedor_id=self.proveedor.pk)
        with self.assertRaises(ValidationError):
            transicionar_orden(context=self.ctx, orden_id=orden.pk, nuevo="PENDIENTE_APROBACION")

    def test_aprobacion_y_recepcion_rechazan_proveedor_ausente(self):
        self.fila(self.desde)
        orden, _ = self.generar()
        orden.estado = "PENDIENTE_APROBACION"
        orden.save(update_fields=["estado"])
        with self.assertRaises(ValidationError):
            transicionar_orden(context=self.ctx, orden_id=orden.pk, nuevo="APROBADA")
        orden.estado = "ACEPTADA"
        orden.save(update_fields=["estado"])
        with self.assertRaises(ValidationError):
            crear_recepcion(context=self.ctx, orden_id=orden.pk, datos={})
        self.assertEqual(MovimientoInventario.objects.filter(empresa=self.empresa).count(), 0)

    def test_aislamiento_y_moneda_base_obligatoria(self):
        self.fila(self.desde)
        otro_usuario = get_user_model().objects.create_user("otra")
        otra = Empresa.objects.create(usuario=otro_usuario, nombre="Otra")
        otro_usuario.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="compras", codename__in=(
                "add_ordencompraenterprise", "change_ordencompraenterprise")))
        otro_ctx = OperationContext(empresa=otra, usuario=otro_usuario,
                                     clave_idempotente="otra-empresa")
        with self.assertRaises(ValidationError):
            generar_borrador_inabie(context=otro_ctx, desde=self.desde, hasta=self.desde)
        orden, _ = self.generar()
        with self.assertRaises(OrdenCompraEnterprise.DoesNotExist):
            editar_borrador_inabie(context=otro_ctx, orden_id=orden.pk)

    def test_pantalla_genera_y_muestra_detalle(self):
        self.fila(self.desde)
        self.client.force_login(self.usuario)
        respuesta = self.client.post(reverse("compras:inabie_orden_generar"),
            {"desde": str(self.desde), "hasta": str(self.desde)})
        self.assertEqual(respuesta.status_code, 302)
        orden = OrdenCompraEnterprise.objects.get(empresa=self.empresa)
        detalle = self.client.get(reverse("compras:inabie_orden_detalle", kwargs={"pk": orden.pk}))
        self.assertEqual(detalle.status_code, 200)
        self.assertContains(detalle, "Disponible")
        self.assertContains(detalle, "Ver cálculo")


    def test_admin_empresa_sin_permisos_django_puede_generar_inabie(self):
        self.fila(self.desde)
        saas = EmpresaSaaS.objects.create(
            nombre="Panaderia A SaaS", rnc="101", correo="saas-admin@test.local",
            activa=True, requiere_pago=False,
        )
        PerfilUsuario.objects.create(
            user=self.usuario, empresa=saas, rol="operaciones",
            correo_validado=True, activo=True,
        )
        admin = get_user_model().objects.create_user("admin-inabie", password="x")
        PerfilUsuario.objects.create(
            user=admin, empresa=saas, rol="admin_empresa",
            correo_validado=True, activo=True,
        )
        self.assertFalse(admin.has_perm("compras.add_ordencompraenterprise"))
        self.client.force_login(admin)
        respuesta = self.client.post(
            reverse("compras:inabie_orden_generar"),
            {"desde": str(self.desde), "hasta": str(self.desde)},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            OrdenCompraEnterprise.objects.filter(empresa=self.empresa, origen="INABIE").count(),
            1,
        )

    def test_usuario_consulta_sin_permiso_no_puede_operar_inabie(self):
        saas = EmpresaSaaS.objects.create(
            nombre="Panaderia Consulta SaaS", rnc="102", correo="saas-consulta@test.local",
            activa=True, requiere_pago=False,
        )
        PerfilUsuario.objects.create(
            user=self.usuario, empresa=saas, rol="operaciones",
            correo_validado=True, activo=True,
        )
        consulta = get_user_model().objects.create_user("consulta-inabie", password="x")
        PerfilUsuario.objects.create(
            user=consulta, empresa=saas, rol="consulta",
            correo_validado=True, activo=True,
        )
        self.client.force_login(consulta)
        respuesta = self.client.get(reverse("compras:inabie_orden_generar"))
        self.assertEqual(respuesta.status_code, 403)
