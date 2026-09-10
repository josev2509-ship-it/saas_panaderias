from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from conduces.models import CentroEducativo, DiaNoDocencia, Empresa, MenuDiario
from auditoria.models import EventoAuditoria

from .models import (
    AjusteOrdenProduccion, AlertaAbastecimiento, ConsumoRealProduccion,
    DetalleRecetaProduccion, OrdenProduccion, ProductoInventario, RecetaProduccion,
    MatriculaCentroVigente, SolicitudCambioProducto, VinculoProductoMenu,
)
from .compras_projection import EntradaConfirmada
from .produccion_inabie_services import (
    ajustar_cantidad, cambiar_producto, cerrar_orden_inabie, generar_orden_inabie,
    iniciar_orden_inabie, proyectar_cobertura, resolver_fecha_entrega,
    resolver_producto_menu, solicitar_cambio_producto, decidir_cambio_producto,
)
from .produccion_services import calcular_necesidades


class ProduccionInabieSprint2Tests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user("jefe_prod",password="x")
        self.empresa=Empresa.objects.create(usuario=self.user,nombre="Panificadora A",activa=True,modulo_inabie=True)
        CentroEducativo.objects.create(empresa=self.empresa,codigo="A",nombre="Centro A",matricula=2500)
        CentroEducativo.objects.create(empresa=self.empresa,codigo="B",nombre="Centro B",matricula=1900)
        CentroEducativo.objects.create(empresa=self.empresa,codigo="C",nombre="Centro C",matricula=2000)
        self.pan=ProductoInventario.objects.create(empresa=self.empresa,codigo="PAN",nombre="Pan escolar",tipo="producto_terminado",unidad_medida="unidad",activo=True)
        self.harina=ProductoInventario.objects.create(empresa=self.empresa,codigo="HAR",nombre="Harina",tipo="materia_prima",unidad_medida="lb",stock_actual=Decimal("500"),activo=True)
        self.receta=RecetaProduccion.objects.create(empresa=self.empresa,codigo="R1",nombre="Pan",producto_terminado=self.pan,version=1,rendimiento_base=Decimal("1909"),unidad_rendimiento="unidad",activa=True,fecha_vigencia_desde=timezone.localdate()-timedelta(days=30))
        DetalleRecetaProduccion.objects.create(receta=self.receta,materia_prima=self.harina,cantidad=Decimal("100"),unidad_medida="lb")
        perms=("add_ordenproduccion","view_ordenproduccion","change_ordenproduccion","ajustar_cantidad_ordenproduccion","autorizar_ordenproduccion","autorizar_cambio_producto","cambiar_producto_ordenproduccion","iniciar_ordenproduccion","cerrar_ordenproduccion")
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label="inventario",codename__in=perms))
        self.produccion=timezone.localdate()
        while self.produccion.weekday()!=3:self.produccion+=timedelta(days=1)
        self.entrega=self.produccion+timedelta(days=1)
        MenuDiario.objects.create(empresa=self.empresa,fecha=self.entrega,producto=self.pan.nombre)

    def generar(self):
        return generar_orden_inabie(empresa=self.empresa,fecha_produccion=self.produccion,modalidad="REGULAR",usuario=self.user)

    def test_fecha_entrega_respeta_calendario_y_no_docencia(self):
        self.assertEqual(resolver_fecha_entrega(self.empresa,self.produccion),self.entrega)
        DiaNoDocencia.objects.create(empresa=self.empresa,fecha=self.entrega,motivo="Feriado")
        self.assertEqual(resolver_fecha_entrega(self.empresa,self.produccion),self.entrega+timedelta(days=3))

    def test_modalidad_prepara_usa_fin_de_semana(self):
        self.assertEqual(resolver_fecha_entrega(self.empresa,self.produccion,"PREPARA").weekday(),5)

    def test_orden_toma_menu_matricula_y_cantidad_sugerida(self):
        orden=self.generar()
        self.assertEqual(orden.producto_planificado,self.pan);self.assertEqual(orden.producto_terminado,self.pan)
        self.assertEqual(orden.raciones_matricula,6400);self.assertEqual(orden.cantidad_sugerida,6400);self.assertEqual(orden.cantidad_autorizada,6400)
        self.assertEqual(orden.fecha_entrega,self.entrega);self.assertTrue(orden.numero.startswith(f"OP-{self.produccion.year}-"))

    def test_receta_escala_a_50_y_6400(self):
        n50=calcular_necesidades(cantidad=Decimal("50"),receta=self.receta,empresa=self.empresa)[0]
        n6400=calcular_necesidades(cantidad=Decimal("6400"),receta=self.receta,empresa=self.empresa)[0]
        self.assertEqual(n50.cantidad_teorica,Decimal("2.6192"));self.assertEqual(n6400.cantidad_teorica,Decimal("335.2541"))

    def test_ajuste_exige_justificacion_y_recalcula_autorizada(self):
        orden=self.generar()
        with self.assertRaises(ValidationError):ajustar_cantidad(orden=orden,empresa=self.empresa,usuario=self.user,cantidad=6500,motivo="AJUSTE_OPERATIVO",justificacion="")
        ajustar_cantidad(orden=orden,empresa=self.empresa,usuario=self.user,cantidad=6500,motivo="PRODUCCION_RESPALDO",justificacion="Reserva operativa")
        orden.refresh_from_db();self.assertEqual(orden.cantidad_autorizada,6500);self.assertEqual(orden.necesidades.get().cantidad_teorica,Decimal("340.4924"));self.assertEqual(AjusteOrdenProduccion.objects.count(),1)

    def test_cambio_producto_exige_autorizacion(self):
        orden=self.generar();otro=ProductoInventario.objects.create(empresa=self.empresa,codigo="P2",nombre="Otro",tipo="producto_terminado",activo=True)
        receta=RecetaProduccion.objects.create(empresa=self.empresa,codigo="R2",nombre="Otro",producto_terminado=otro,rendimiento_base=1,unidad_rendimiento="unidad",activa=True,fecha_vigencia_desde=self.produccion)
        with self.assertRaises(PermissionDenied):cambiar_producto(orden=orden,empresa=self.empresa,usuario=self.user,producto=otro,receta=receta,motivo="REPOSICION",justificacion="Cambio",autorizado_por=None)
        cambiar_producto(orden=orden,empresa=self.empresa,usuario=self.user,producto=otro,receta=receta,motivo="REPOSICION",justificacion="Cambio autorizado",autorizado_por=self.user)
        orden.refresh_from_db();self.assertEqual(orden.producto_planificado,self.pan);self.assertEqual(orden.producto_terminado,otro)

    def test_inicio_congela_snapshot_de_receta_y_teorico(self):
        orden=self.generar();orden.estado=OrdenProduccion.Estado.PROGRAMADA;orden.save(update_fields=["estado"])
        iniciar_orden_inabie(orden=orden,empresa=self.empresa,usuario=self.user);orden.refresh_from_db()
        self.assertEqual(orden.estado,"EN_PROCESO");self.assertEqual(orden.iniciada_por,self.user);self.assertEqual(orden.snapshot_produccion["version"],1);self.assertEqual(len(orden.snapshot_produccion["ingredientes"]),1)

    def test_cierre_consumo_real_desviacion_y_proteccion(self):
        orden=self.generar();orden.estado=OrdenProduccion.Estado.PROGRAMADA;orden.save(update_fields=["estado"]);iniciar_orden_inabie(orden=orden,empresa=self.empresa,usuario=self.user)
        with self.assertRaises(ValidationError):cerrar_orden_inabie(orden=orden,empresa=self.empresa,usuario=self.user,cantidad_real=6300,consumos=[{"materia_prima_id":self.harina.pk,"cantidad_real":"400","motivo":"MERMA","justificacion":""}])
        cerrar_orden_inabie(orden=orden,empresa=self.empresa,usuario=self.user,cantidad_real=6300,consumos=[{"materia_prima_id":self.harina.pk,"cantidad_real":"400","motivo":"MERMA","justificacion":"Diferencia validada"}])
        orden.refresh_from_db();self.assertEqual(orden.estado,"CERRADA");self.assertEqual(orden.cantidad_producida,6300);self.assertEqual(ConsumoRealProduccion.objects.count(),1)
        with self.assertRaises(ValidationError):ajustar_cantidad(orden=orden,empresa=self.empresa,usuario=self.user,cantidad=6400,motivo="OTRO",justificacion="No")

    def test_proyeccion_alerta_compra_y_cancelacion(self):
        orden=self.generar();self.harina.stock_actual=Decimal("100");self.harina.save(update_fields=["stock_actual"])
        filas=proyectar_cobertura(empresa=self.empresa,desde=self.entrega,dias_productivos=15)
        self.assertLess(filas[0].saldo_proyectado,0);self.assertGreater(filas[0].compra_sugerida,0);self.assertTrue(AlertaAbastecimiento.objects.get().activa)
        orden.estado=OrdenProduccion.Estado.CANCELADA;orden.save(update_fields=["estado"])
        self.assertEqual(proyectar_cobertura(empresa=self.empresa,desde=self.entrega,dias_productivos=1)[0].necesidad,Decimal("335.2541"))

    def test_proyeccion_cerrada_sustituye_teorico_por_real(self):
        orden=self.generar();orden.estado=OrdenProduccion.Estado.CERRADA;orden.cantidad_producida=6300;orden.save(update_fields=["estado","cantidad_producida"])
        ConsumoRealProduccion.objects.create(empresa=self.empresa,orden=orden,materia_prima=self.harina,cantidad_teorica=orden.necesidades.get().cantidad_con_merma,cantidad_real=Decimal("300"),unidad_medida="lb",diferencia=Decimal("-35.2541"),registrado_por=self.user)
        self.assertEqual(proyectar_cobertura(empresa=self.empresa,desde=self.entrega,dias_productivos=1)[0].necesidad,300)

    def test_pdf_y_tenant_isolation(self):
        orden=self.generar();self.client.force_login(self.user)
        response=self.client.get(reverse("inventario:orden_pdf",args=[orden.pk]));self.assertEqual(response.status_code,200);self.assertEqual(response["Content-Type"],"application/pdf")
        otro=User.objects.create_user("otrotenant");empresa_b=Empresa.objects.create(usuario=otro,nombre="B")
        self.assertEqual(OrdenProduccion.objects.filter(empresa=empresa_b,pk=orden.pk).count(),0)

    def test_menu_enlaza_producto_real_sin_duplicarlo(self):
        menu=MenuDiario.objects.get(empresa=self.empresa,fecha=self.entrega)
        self.assertEqual(resolver_producto_menu(self.empresa,menu),self.pan)
        vinculo=VinculoProductoMenu.objects.get(menu=menu);self.assertEqual(vinculo.producto,self.pan);self.assertFalse(vinculo.revisado)
        self.assertEqual(ProductoInventario.objects.filter(empresa=self.empresa,nombre=self.pan.nombre).count(),1)

    def test_menu_sin_matching_queda_sin_vinculo_para_revision(self):
        menu=MenuDiario.objects.create(empresa=self.empresa,fecha=self.entrega+timedelta(days=1),producto="Producto no homologado")
        self.assertIsNone(resolver_producto_menu(self.empresa,menu));self.assertFalse(VinculoProductoMenu.objects.filter(menu=menu).exists())

    def test_vinculo_menu_rechaza_producto_cross_tenant(self):
        otro=User.objects.create_user("vinculo_otro");empresa_b=Empresa.objects.create(usuario=otro,nombre="B")
        producto_b=ProductoInventario.objects.create(empresa=empresa_b,codigo="B",nombre="B",tipo="producto_terminado")
        vinculo=VinculoProductoMenu(empresa=self.empresa,menu=MenuDiario.objects.get(fecha=self.entrega),producto=producto_b)
        with self.assertRaises(ValidationError):vinculo.full_clean()

    def test_matricula_vigente_cambia_entre_periodos(self):
        centro=CentroEducativo.objects.get(codigo="A")
        MatriculaCentroVigente.objects.create(empresa=self.empresa,centro=centro,modalidad="REGULAR",fecha_desde=self.entrega-timedelta(days=30),fecha_hasta=self.entrega,raciones=2600)
        MatriculaCentroVigente.objects.create(empresa=self.empresa,centro=centro,modalidad="REGULAR",fecha_desde=self.entrega+timedelta(days=1),raciones=2700)
        from .produccion_inabie_services import total_raciones
        self.assertEqual(total_raciones(self.empresa,self.entrega,"REGULAR"),6500)
        self.assertEqual(total_raciones(self.empresa,self.entrega+timedelta(days=1),"REGULAR"),6600)

    def test_matricula_regular_y_prepara_son_independientes(self):
        centro=CentroEducativo.objects.get(codigo="A")
        MatriculaCentroVigente.objects.create(empresa=self.empresa,centro=centro,modalidad="REGULAR",fecha_desde=self.entrega,raciones=2600)
        MatriculaCentroVigente.objects.create(empresa=self.empresa,centro=centro,modalidad="PREPARA",fecha_desde=self.entrega,raciones=500)
        from .produccion_inabie_services import total_raciones
        self.assertEqual(total_raciones(self.empresa,self.entrega,"REGULAR"),6500)
        self.assertEqual(total_raciones(self.empresa,self.entrega,"PREPARA"),4400)

    def test_solicitud_cambio_autorizacion_y_auditoria(self):
        orden=self.generar();otro=ProductoInventario.objects.create(empresa=self.empresa,codigo="AUT",nombre="Autorizado",tipo="producto_terminado",activo=True)
        receta=RecetaProduccion.objects.create(empresa=self.empresa,codigo="RAUT",nombre="Aut",producto_terminado=otro,rendimiento_base=1,unidad_rendimiento="unidad",activa=True,fecha_vigencia_desde=self.produccion)
        solicitud=solicitar_cambio_producto(orden=orden,empresa=self.empresa,usuario=self.user,producto=otro,receta=receta,motivo="REPOSICION",justificacion="Autorización requerida")
        self.assertEqual(solicitud.estado,"PENDIENTE");self.assertEqual(solicitud.producto_original,self.pan)
        decidir_cambio_producto(solicitud=solicitud,empresa=self.empresa,usuario=self.user,decision="AUTORIZAR")
        solicitud.refresh_from_db();orden.refresh_from_db();self.assertEqual(solicitud.estado,"AUTORIZADA");self.assertEqual(orden.producto_terminado,otro);self.assertGreaterEqual(EventoAuditoria.objects.filter(empresa=self.empresa,modulo="produccion").count(),2)

    def test_solicitud_cambio_rechazada_no_cambia_producto(self):
        orden=self.generar();otro=ProductoInventario.objects.create(empresa=self.empresa,codigo="REJ",nombre="Rechazado",tipo="producto_terminado",activo=True)
        receta=RecetaProduccion.objects.create(empresa=self.empresa,codigo="RREJ",nombre="Rej",producto_terminado=otro,rendimiento_base=1,unidad_rendimiento="unidad",activa=True,fecha_vigencia_desde=self.produccion)
        solicitud=solicitar_cambio_producto(orden=orden,empresa=self.empresa,usuario=self.user,producto=otro,receta=receta,motivo="OTRO",justificacion="Solicitud")
        decidir_cambio_producto(solicitud=solicitud,empresa=self.empresa,usuario=self.user,decision="RECHAZAR",comentario="No procede")
        solicitud.refresh_from_db();orden.refresh_from_db();self.assertEqual(solicitud.estado,"RECHAZADA");self.assertEqual(orden.producto_terminado,self.pan)

    @patch("inventario.produccion_inabie_services.entradas_confirmadas")
    def test_entrada_confirmada_antes_de_necesidad_aumenta_disponible(self,mock_entradas):
        self.harina.stock_actual=0;self.harina.save(update_fields=["stock_actual"])
        mock_entradas.return_value=[EntradaConfirmada(self.harina.pk,Decimal("400"),"lb",self.entrega,1)]
        fila=proyectar_cobertura(empresa=self.empresa,desde=self.entrega,dias_productivos=1)[0]
        self.assertEqual(fila.entradas_confirmadas,400);self.assertGreater(fila.saldo_proyectado,0);self.assertIsNone(fila.fecha_agotamiento)

    @patch("inventario.produccion_inabie_services.entradas_confirmadas")
    def test_entrada_posterior_a_necesidad_no_evitan_agotamiento(self,mock_entradas):
        self.harina.stock_actual=0;self.harina.save(update_fields=["stock_actual"])
        mock_entradas.return_value=[EntradaConfirmada(self.harina.pk,Decimal("400"),"lb",self.entrega+timedelta(days=1),1)]
        fila=proyectar_cobertura(empresa=self.empresa,desde=self.entrega,dias_productivos=1)[0]
        self.assertEqual(fila.fecha_agotamiento,self.entrega)

    @patch("inventario.produccion_inabie_services.entradas_confirmadas",return_value=[])
    def test_entrada_no_confirmada_no_cuenta(self,mock_entradas):
        fila=proyectar_cobertura(empresa=self.empresa,desde=self.entrega,dias_productivos=15)[0]
        self.assertEqual(fila.entradas_confirmadas,0);self.assertEqual(mock_entradas.call_count,1)
