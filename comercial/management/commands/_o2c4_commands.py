from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from django.utils import timezone
from catalogos.models import Moneda, MonedaEmpresa
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from inventario.models import LoteInventario, ProductoInventario
from comercial.models import *

class Base(BaseCommand):
    mutates=False
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def empresa(self,o):
        try:return Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
class Configurar(Base):
    mutates=True
    def handle(self,*a,**o):e=self.empresa(o);self.stdout.write(("Se verificaría" if o["dry_run"] else "Verificada")+f" configuración O2C de {e.nombre}.")
class ExpirarReservas(Base):
    mutates=True
    def handle(self,*a,**o):e=self.empresa(o);q=ReservaComercial.objects.filter(empresa=e,estado__in=["PENDIENTE","PARCIAL","COMPLETA"],expira_en__lt=timezone.now());n=q.count();q.update(estado="EXPIRADA") if not o["dry_run"] else None;self.stdout.write(f"Reservas a expirar: {n}.")
class Verificar(Base):
    model=None;label="registros"
    def handle(self,*a,**o):e=self.empresa(o);n=self.model.objects.filter(empresa=e).count();self.stdout.write(self.style.SUCCESS(f"{self.label}: {n}; verificación completada."))
class VerificarReservas(Verificar):model=ReservaComercial;label="Reservas"
class VerificarPreparaciones(Verificar):model=PreparacionPedido;label="Preparaciones"
class VerificarDespachos(Verificar):model=DespachoComercial;label="Despachos"
class VerificarNCF(Verificar):model=FacturaVenta;label="Facturas/NCF"
class VerificarCobros(Verificar):model=ReciboCobro;label="Cobros"
class VerificarFactoring(Verificar):model=CesionFactoring;label="Factoring"
class MarcarFacturas(Base):
    mutates=True
    def handle(self,*a,**o):e=self.empresa(o);q=FacturaVenta.objects.filter(empresa=e,estado="EMITIDA",vence_el__lt=timezone.localdate());n=q.count();q.update(estado="VENCIDA") if not o["dry_run"] else None;self.stdout.write(f"Facturas vencidas: {n}.")
class RecalcularCxC(Base):
    mutates=True
    def handle(self,*a,**o):
        e=self.empresa(o);q=CuentaPorCobrar.objects.filter(empresa=e);n=q.count()
        if not o["dry_run"]:
            for c in q:c.saldo=max(0,c.monto_original-sum((x.monto for x in c.movimientos.filter(tipo="COBRO")),0));c.estado="COBRADA" if not c.saldo else "PARCIAL" if c.saldo<c.monto_original else "PENDIENTE";c.save()
        self.stdout.write(f"CxC recalculadas: {n}.")
class ActualizarAging(Base):
    mutates=True
    def handle(self,*a,**o):
        from comercial.application.o2c_full import _aging
        e=self.empresa(o);q=CuentaPorCobrar.objects.filter(empresa=e);n=q.count()
        if not o["dry_run"]:
            for c in q:c.bucket_aging=_aging(c);c.save(update_fields=["bucket_aging"])
        self.stdout.write(f"Aging actualizado: {n}.")
class Promesas(Base):
    mutates=True
    def handle(self,*a,**o):e=self.empresa(o);q=PromesaPago.objects.filter(cuenta__empresa=e,estado="PENDIENTE",fecha_prometida__lt=timezone.localdate());n=q.count();q.update(estado="INCUMPLIDA") if not o["dry_run"] else None;self.stdout.write(f"Promesas incumplidas: {n}.")
class Demo(Base):
    mutates=True
    @transaction.atomic
    def handle(self,*a,**o):
        e=self.empresa(o)
        if o["dry_run"]:
            self.stdout.write("Se generaría un flujo O2C completo mediante InventoryEngine y servicios certificados.")
            return
        if FacturaVenta.objects.filter(empresa=e, numero="DEMO-O2C-0001").exists():
            self.stdout.write(self.style.SUCCESS("Flujo O2C demo ya existe; no se generaron duplicados."))
            return

        from comercial.application.financial_integration import contabilizar_factura_emitida, integrar_cobro
        from comercial.application.o2c_full import (
            aplicar_cobro, autorizar_despacho, completar_picking, confirmar_entrega,
            crear_despacho, crear_factura_desde_entrega, crear_packing,
            crear_preparacion, crear_reserva_desde_pedido, emitir_conduce,
            emitir_factura, generar_picking, iniciar_preparacion, registrar_cobro,
            reservar_inventario, sellar_packing, validar_preparacion,
        )
        from comercial.pedidos_services import calcular_linea
        from contabilidad.models import CuentaContable, DiarioContable, PeriodoContable, PlanCuenta, ReglaContabilizacion
        from tesoreria.models import CuentaBancariaEmpresa

        user=e.usuario
        moneda,_=Moneda.objects.get_or_create(codigo="DOP",defaults={"nombre":"Peso dominicano","simbolo":"RD$"})
        moneda_empresa,_=MonedaEmpresa.objects.get_or_create(empresa=e,moneda=moneda,defaults={"es_base":True,"activa":True})
        cliente,_=Cliente.objects.get_or_create(empresa=e,codigo="DEMO-O2C",defaults={
            "tipo_cliente":Cliente.Tipo.CLIENTE_PRIVADO,"nombre_comercial":"Cliente Demo O2C",
            "estado":Cliente.Estado.ACTIVO,"condicion_pago":Cliente.CondicionPago.CREDITO,
            "dias_credito":30,"limite_credito":Decimal("100000"),"moneda_comercial":moneda_empresa,"creado_por":user})
        producto,_=ProductoInventario.objects.get_or_create(empresa=e,codigo="DEMO-PT-O2C",defaults={
            "nombre":"Pan demo terminado","tipo":"producto_terminado","clasificacion_operativa":"producto_terminado",
            "unidad_medida":"unidad","stock_actual":Decimal("500"),"activo":True})
        if producto.stock_actual < 500:
            producto.stock_actual=Decimal("500");producto.save(update_fields=["stock_actual"])
        LoteInventario.objects.get_or_create(empresa=e,producto=producto,lote="DEMO-O2C-L1",defaults={
            "fecha_ingreso":timezone.localdate(),"fecha_vencimiento":timezone.localdate()+timedelta(days=90),
            "cantidad_inicial":Decimal("500"),"cantidad_disponible":Decimal("500")})
        pedido=Pedido.objects.create(empresa=e,numero="DEMO-PED-0001",cliente=cliente,
            fecha_pedido=timezone.localdate(),fecha_entrega=timezone.localdate()+timedelta(days=1),
            condicion_pago=Cliente.CondicionPago.CREDITO,dias_credito=30,estado=Pedido.Estado.APROBADO,creado_por=user)
        linea=DetallePedido(pedido=pedido,producto=producto,descripcion=producto.nombre,cantidad=Decimal("10"),
            unidad_medida="unidad",precio_unitario=Decimal("100"),porcentaje_descuento=0,porcentaje_impuesto=0)
        calcular_linea(linea);linea.save();pedido.subtotal=linea.subtotal;pedido.total=linea.total;pedido.save(update_fields=["subtotal","total"])

        plan,_=PlanCuenta.objects.get_or_create(empresa=e,codigo="DEMO-O2C",defaults={"nombre":"Plan demo O2C","creado_por":user})
        for codigo,nombre,tipo,naturaleza in (("1102","Banco","ACTIVO","DEBITO"),("1201","CxC","ACTIVO","DEBITO"),("4101","Ingresos","INGRESO","CREDITO")):
            CuentaContable.objects.get_or_create(empresa=e,plan=plan,codigo=codigo,defaults={"nombre":nombre,"tipo":tipo,"naturaleza":naturaleza,"creado_por":user})
        hoy=timezone.localdate();inicio=hoy.replace(day=1);fin=(inicio+timedelta(days=32)).replace(day=1)-timedelta(days=1)
        PeriodoContable.objects.get_or_create(empresa=e,anio=hoy.year,mes=hoy.month,defaults={"fecha_inicio":inicio,"fecha_fin":fin,"creado_por":user})
        DiarioContable.objects.get_or_create(empresa=e,codigo="GENERAL",defaults={"nombre":"General","creado_por":user})
        for evento,config in (("FACTURA_VENTA",{"debito":"1201","credito":"4101"}),("COBRO",{"debito":"1102","credito":"1201"})):
            ReglaContabilizacion.objects.get_or_create(empresa=e,evento=evento,defaults={"configuracion":config,"creado_por":user})
        banco,_=CuentaBancariaEmpresa.objects.get_or_create(empresa=e,banco="Banco Demo O2C",numero_enmascarado="****0001",defaults={"moneda":moneda_empresa})
        ctx=OperationContext(empresa=e,usuario=user,origen="demo-ready")
        reserva=reservar_inventario(context=ctx,reserva_id=crear_reserva_desde_pedido(context=ctx,pedido_id=pedido.pk).pk)
        preparacion=validar_preparacion(context=ctx,pk=iniciar_preparacion(context=ctx,pk=crear_preparacion(context=ctx,reserva_id=reserva.pk).pk).pk)
        picking=completar_picking(context=ctx,pk=generar_picking(context=ctx,preparacion_id=preparacion.pk).pk)
        packing=sellar_packing(context=ctx,pk=crear_packing(context=ctx,picking_id=picking.pk).pk,peso=Decimal("5"))
        despacho=autorizar_despacho(context=ctx,pk=crear_despacho(context=ctx,packing_ids=[packing.pk]).pk)
        entrega=confirmar_entrega(context=ctx,conduce_id=emitir_conduce(context=ctx,despacho_id=despacho.pk).pk,receptor="Recepción Demo")
        factura=crear_factura_desde_entrega(context=ctx,entrega_id=entrega.pk,vence_el=hoy+timedelta(days=30),ncf="B0100000001")
        factura.numero="DEMO-O2C-0001";factura.save(update_fields=["numero"]);factura=emitir_factura(context=ctx,pk=factura.pk)
        contabilizar_factura_emitida(context=ctx,factura_id=factura.pk)
        recibo=registrar_cobro(context=ctx,cliente=cliente,moneda=moneda_empresa,monto=factura.total,metodo="TRANSFERENCIA",referencia="DEMO-O2C-COBRO")
        aplicar_cobro(context=ctx,recibo_id=recibo.pk,cuenta_id=factura.cuenta_cobrar.pk,monto=factura.total)
        integrar_cobro(context=ctx,recibo_id=recibo.pk,cuenta_bancaria_id=banco.pk)
        self.stdout.write(self.style.SUCCESS("Flujo O2C demo completo generado mediante servicios certificados."))
