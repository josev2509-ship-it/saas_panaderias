import tempfile
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone

from comercial.models import Cliente, DetallePedido, Pedido
from comercial.pedidos_services import calcular_linea, siguiente_numero
from documentos.models import Documento

from .models import (
    DetallePlanProduccion, DetalleRecetaProduccion, MovimientoInventario,
    NecesidadMateriaPrima, OrdenProduccion, PlanProduccion, ProductoInventario,
    RecetaProduccion,
)
from .produccion_forms import (
    DetallePlanForm, GenerarPlanPedidosForm, IngredienteForm, OrdenProduccionForm,
    PlanProduccionForm, RecetaProduccionForm,
)
from .produccion_services import (
    calcular_necesidades, duplicar_receta, generar_ordenes_desde_plan,
    generar_plan_desde_pedidos, recalcular_necesidades_plan, transicionar_orden,
)
from . import tests_produccion as pruebas_base


class ProduccionCumplimientoTest(TestCase):
    setUp = pruebas_base.ProduccionSprintTest.setUp
    dar_permisos = pruebas_base.ProduccionSprintTest.dar_permisos
    orden = pruebas_base.ProduccionSprintTest.orden
    pedido_aprobado = pruebas_base.ProduccionSprintTest.pedido_aprobado
    def plan(self, empresa=None, estado=PlanProduccion.Estado.BORRADOR):
        empresa = empresa or self.empresa
        return PlanProduccion.objects.create(
            empresa=empresa, numero=siguiente_numero(empresa, tipo="PLA"),
            fecha_plan=timezone.localdate(), estado=estado,
        )

    def test_usuario_solo_ve_planes_de_su_empresa(self):
        propio = self.plan()
        ajeno = self.plan(self.empresa_b)
        self.client.force_login(self.user)
        respuesta = self.client.get("/inventario/produccion/planes/")
        self.assertContains(respuesta, propio.numero)
        self.assertNotContains(respuesta, f'href="/inventario/produccion/planes/{ajeno.pk}/"')

    def test_usuario_solo_ve_ordenes_de_su_empresa(self):
        propia = self.orden()
        receta_b = RecetaProduccion.objects.create(
            empresa=self.empresa_b, codigo="R-B", nombre="B",
            producto_terminado=self.terminado_b, rendimiento_base=1,
            unidad_rendimiento="u", activa=True, fecha_vigencia_desde=timezone.localdate(),
        )
        ajena = self.orden(empresa=self.empresa_b, receta=receta_b, producto=self.terminado_b)
        self.client.force_login(self.user)
        respuesta = self.client.get("/inventario/produccion/ordenes/")
        self.assertContains(respuesta, propia.numero)
        self.assertNotContains(respuesta, f'href="/inventario/produccion/ordenes/{ajena.pk}/"')

    def test_numeracion_es_unica_dentro_de_empresa(self):
        numero = siguiente_numero(self.empresa, tipo="OP")
        self.orden().delete()
        OrdenProduccion.objects.create(
            empresa=self.empresa, numero=numero, producto_terminado=self.terminado,
            receta=self.receta, fecha_programada=timezone.localdate(),
            cantidad_planificada=1, unidad_medida="unidad",
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            OrdenProduccion.objects.create(
                empresa=self.empresa, numero=numero, producto_terminado=self.terminado,
                receta=self.receta, fecha_programada=timezone.localdate(),
                cantidad_planificada=1, unidad_medida="unidad",
            )

    def test_solo_se_permiten_transiciones_validas(self):
        orden = self.orden(OrdenProduccion.Estado.BORRADOR)
        for accion in ("iniciar", "completar"):
            with self.assertRaises(Exception):
                transicionar_orden(
                    orden=orden, empresa=self.empresa, usuario=self.user,
                    accion=accion, cantidad_producida=1,
                )

    def test_no_se_puede_completar_orden_no_iniciada(self):
        orden = self.orden(OrdenProduccion.Estado.PROGRAMADA)
        with self.assertRaises(Exception):
            transicionar_orden(
                orden=orden, empresa=self.empresa, usuario=self.user,
                accion="completar", cantidad_producida=1, cantidad_rechazada=0,
            )

    def test_duplicacion_no_copia_documentos(self):
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            ct = ContentType.objects.get_for_model(self.receta)
            Documento.objects.create(
                empresa=self.empresa, titulo="Ficha", archivo=ContentFile(b"%PDF-1.4", name="ficha.pdf"),
                nombre_original="ficha.pdf", extension="pdf", tamano_bytes=8,
                content_type=ct, object_id=self.receta.pk,
            )
            nueva = duplicar_receta(receta=self.receta, usuario=self.user)
            self.assertFalse(
                Documento.objects.filter(content_type=ct, object_id=nueva.pk).exists()
            )

    def test_calculo_necesidades_devuelve_decimal(self):
        necesidad = calcular_necesidades(
            cantidad=Decimal("150"), receta=self.receta, empresa=self.empresa
        )[0]
        self.assertIsInstance(necesidad.cantidad_teorica, Decimal)
        self.assertIsInstance(necesidad.cantidad_con_merma, Decimal)

    def test_campos_tecnicos_no_forman_parte_de_formularios_post(self):
        self.assertNotIn("empresa", RecetaProduccionForm(empresa=self.empresa).fields)
        for campo in ("empresa", "numero", "estado", "aprobado_por", "fecha_aprobacion"):
            self.assertNotIn(campo, PlanProduccionForm().fields)
        for campo in (
            "empresa", "numero", "estado", "fecha_inicio_real", "fecha_fin_real",
            "cantidad_iniciada", "cantidad_producida", "cantidad_rechazada",
        ):
            self.assertNotIn(campo, OrdenProduccionForm(empresa=self.empresa).fields)
        for campo in (
            "cantidad_teorica", "cantidad_con_merma", "estado", "empresa",
        ):
            self.assertFalse(any(campo in form.fields for form in (
                RecetaProduccionForm(empresa=self.empresa), PlanProduccionForm(),
                OrdenProduccionForm(empresa=self.empresa),
            )))

    def test_formulario_rechaza_producto_terminado_ajeno_o_inactivo(self):
        inactivo = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="INACT", nombre="Inactivo",
            tipo="producto_terminado", activo=False,
        )
        base = {
            "codigo": "RX", "nombre": "Manipulada", "version": 1,
            "rendimiento_base": "10", "unidad_rendimiento": "unidad",
            "porcentaje_merma_estimada": "0",
            "fecha_vigencia_desde": timezone.localdate().isoformat(),
        }
        for producto in (self.terminado_b, inactivo):
            form = RecetaProduccionForm({**base, "producto_terminado": producto.pk}, empresa=self.empresa)
            self.assertFalse(form.is_valid())

    def test_formulario_rechaza_materia_prima_ajena_o_inactiva(self):
        inactiva = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="MPI", nombre="MP inactiva",
            tipo="materia_prima", activo=False,
        )
        for materia in (self.materia_b, inactiva):
            form = IngredienteForm({
                "materia_prima": materia.pk, "cantidad": "1",
                "unidad_medida": "kg", "porcentaje_merma": "0", "orden": 1,
            }, empresa=self.empresa)
            self.assertFalse(form.is_valid())

    def test_formulario_orden_rechaza_receta_otro_producto_y_vencida(self):
        otro = ProductoInventario.objects.create(
            empresa=self.empresa, codigo="PT-X", nombre="Otro PT",
            tipo="producto_terminado", activo=True,
        )
        receta_otro = RecetaProduccion.objects.create(
            empresa=self.empresa, codigo="R-X", nombre="Otra", producto_terminado=otro,
            rendimiento_base=1, unidad_rendimiento="unidad", activa=True,
            fecha_vigencia_desde=timezone.localdate(),
        )
        datos = {
            "producto_terminado": self.terminado.pk, "receta": receta_otro.pk,
            "fecha_programada": timezone.localdate().isoformat(), "turno": "UNICO",
            "prioridad": "NORMAL", "cantidad_planificada": "10",
            "unidad_medida": "unidad", "observaciones": "",
        }
        self.assertFalse(OrdenProduccionForm(datos, empresa=self.empresa).is_valid())
        self.receta.fecha_vigencia_hasta = timezone.localdate() - timedelta(days=1)
        self.receta.save()
        datos["receta"] = self.receta.pk
        self.assertFalse(OrdenProduccionForm(datos, empresa=self.empresa).is_valid())

    def test_formulario_generacion_rechaza_pedido_ajeno_o_no_aprobado(self):
        aprobado, _ = self.pedido_aprobado()
        aprobado.empresa = self.empresa_b
        aprobado.cliente = Cliente.objects.create(
            empresa=self.empresa_b, codigo="CB", nombre_comercial="B",
            tipo_cliente=Cliente.Tipo.CLIENTE_PRIVADO,
        )
        aprobado.numero = siguiente_numero(self.empresa_b)
        aprobado.save()
        borrador, _ = self.pedido_aprobado()
        borrador.estado = Pedido.Estado.BORRADOR
        borrador.save()
        form = GenerarPlanPedidosForm({
            "fecha_plan": timezone.localdate().isoformat(),
            "pedidos": [aprobado.pk, borrador.pk],
        }, empresa=self.empresa)
        self.assertFalse(form.is_valid())

    def test_detalle_plan_rechaza_detalle_de_otro_pedido(self):
        pedido1, linea1 = self.pedido_aprobado()
        pedido2, linea2 = self.pedido_aprobado()
        plan = self.plan()
        detalle = DetallePlanProduccion(
            plan=plan, producto_terminado=self.terminado, receta=self.receta,
            cantidad_solicitada=1, cantidad_planificada=1, unidad_medida="unidad",
            prioridad="NORMAL", fecha_requerida=timezone.localdate(),
            pedido_origen=pedido1, detalle_pedido_origen=linea2,
        )
        with self.assertRaises(Exception):
            detalle.full_clean()

    def test_generacion_plan_es_atomica(self):
        pedido, _ = self.pedido_aprobado()
        with patch("inventario.produccion_services.registrar_evento", side_effect=RuntimeError("fallo")):
            with self.assertRaises(RuntimeError):
                generar_plan_desde_pedidos(
                    empresa=self.empresa, pedidos=[pedido],
                    fecha_plan=timezone.localdate(), usuario=self.user,
                )
        self.assertFalse(PlanProduccion.objects.exists())

    def test_generacion_ordenes_es_atomica_y_no_duplica(self):
        pedido, _ = self.pedido_aprobado()
        plan = generar_plan_desde_pedidos(
            empresa=self.empresa, pedidos=[pedido],
            fecha_plan=timezone.localdate(), usuario=self.user,
        )
        plan.estado = PlanProduccion.Estado.APROBADO
        plan.save()
        with patch("inventario.produccion_services.registrar_evento", side_effect=RuntimeError("fallo")):
            with self.assertRaises(RuntimeError):
                generar_ordenes_desde_plan(
                    plan=plan, empresa=self.empresa, usuario=self.user,
                )
        self.assertFalse(OrdenProduccion.objects.exists())
        generar_ordenes_desde_plan(plan=plan, empresa=self.empresa, usuario=self.user)
        cantidad = OrdenProduccion.objects.count()
        with self.assertRaises(Exception):
            generar_ordenes_desde_plan(plan=plan, empresa=self.empresa, usuario=self.user)
        self.assertEqual(OrdenProduccion.objects.count(), cantidad)

    def test_completar_no_altera_inventario_ni_crea_consumos(self):
        stock_mp = self.materia.stock_actual
        stock_pt = self.terminado.stock_actual
        movimientos = MovimientoInventario.objects.count()
        orden = self.orden(OrdenProduccion.Estado.EN_PROCESO)
        orden.cantidad_iniciada = 100
        orden.save()
        transicionar_orden(
            orden=orden, empresa=self.empresa, usuario=self.user, accion="completar",
            cantidad_producida=95, cantidad_rechazada=5,
        )
        self.materia.refresh_from_db()
        self.terminado.refresh_from_db()
        self.assertEqual(self.materia.stock_actual, stock_mp)
        self.assertEqual(self.terminado.stock_actual, stock_pt)
        self.assertEqual(MovimientoInventario.objects.count(), movimientos)

    def test_recalculo_necesidades_orden_no_duplica(self):
        orden = self.orden()
        calcular_necesidades(
            cantidad=100, receta=self.receta, empresa=self.empresa,
            orden=orden, fecha_requerida=orden.fecha_programada,
        )
        calcular_necesidades(
            cantidad=100, receta=self.receta, empresa=self.empresa,
            orden=orden, fecha_requerida=orden.fecha_programada,
        )
        self.assertEqual(NecesidadMateriaPrima.objects.filter(orden=orden).count(), 1)

    def test_recalculo_necesidades_plan_no_duplica(self):
        plan = self.plan()
        DetallePlanProduccion.objects.create(
            plan=plan, producto_terminado=self.terminado, receta=self.receta,
            cantidad_solicitada=100, cantidad_planificada=100,
            unidad_medida="unidad", fecha_requerida=plan.fecha_plan,
        )
        for _ in range(2):
            recalcular_necesidades_plan(plan)
        self.assertEqual(NecesidadMateriaPrima.objects.filter(plan=plan).count(), 1)

    def test_receta_usada_por_orden_no_se_puede_eliminar(self):
        self.orden()
        with self.assertRaises(ProtectedError):
            self.receta.delete()

    def test_permisos_personalizados_existen_y_se_asignan_a_grupo(self):
        nombres = {
            "aprobar_planproduccion", "cancelar_planproduccion",
            "programar_ordenproduccion", "iniciar_ordenproduccion",
            "completar_ordenproduccion", "cancelar_ordenproduccion",
        }
        permisos = Permission.objects.filter(
            content_type__app_label="inventario", codename__in=nombres,
        )
        self.assertEqual(set(permisos.values_list("codename", flat=True)), nombres)
        grupo = Group.objects.create(name="Producción")
        grupo.permissions.add(*permisos)
        self.assertEqual(grupo.permissions.filter(codename__in=nombres).count(), len(nombres))

    def test_no_existen_migraciones_pendientes(self):
        call_command("makemigrations", check=True, dry_run=True, verbosity=0)
