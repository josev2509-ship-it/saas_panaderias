from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from conduces.models import (
    CentroEducativo, ComprobanteFiscal, Conduce, DetalleFactura, Empresa,
    Factura, MenuDiario, ProductoFacturacion,
)
from catalogos.models import Moneda, MonedaEmpresa


TARGETS = {
    "clientes": 20, "proveedores": 15, "prospectos": 15,
    "oportunidades": 10, "cotizaciones": 20, "pedidos": 25,
    "entregas": 15, "facturas_cliente": 20, "cobros": 15,
    "cuentas_vencidas": 10, "solicitudes": 15, "rfq": 10,
    "ofertas": 15, "ordenes": 10, "recepciones": 12,
    "facturas_proveedor": 15, "pagos": 12,
}

PIPELINE = (
    "generar_datos_demo_configuracion_comercial",
    "generar_datos_demo_o2c_parte_1",
    "generar_datos_demo_crm",
    "generar_datos_demo_o2c_completo",
    "generar_datos_demo_p2p",
    "generar_datos_demo_administrativos",
)


def _generar_inabie(empresa):
    hoy = timezone.localdate()
    centro, _ = CentroEducativo.objects.get_or_create(
        empresa=empresa, codigo="DEMO-001",
        defaults={"nombre": "Centro Educativo Demo", "director": "Dirección Demo",
                  "provincia": "Santo Domingo", "regional_distrito": "10-01",
                  "matricula": 250, "orden_carga": 1},
    )
    menu, _ = MenuDiario.objects.get_or_create(
        empresa=empresa, fecha=hoy,
        defaults={"producto": "Pan nutritivo con leche"},
    )
    conduces = []
    for index, estado in enumerate(("borrador", "generado", "entregado"), start=1):
        conduce, _ = Conduce.objects.get_or_create(
            empresa=empresa, numero=f"DEMO-INABIE-{index:04d}",
            defaults={"fecha": hoy - timedelta(days=3-index), "centro": centro,
                      "producto": menu.producto, "cantidad": centro.matricula, "estado": estado},
        )
        conduces.append(conduce)
    producto, _ = ProductoFacturacion.objects.get_or_create(
        empresa=empresa, categoria="PAN",
        defaults={"nombre_factura": "Pan nutritivo demo", "precio_sin_itbis": Decimal("25.00"),
                  "aplica_itbis": False, "porcentaje_itbis": 0, "activo": True},
    )
    comprobante, _ = ComprobanteFiscal.objects.get_or_create(
        empresa=empresa, ncf="B1500000001",
        defaults={"tipo": "B15", "fecha_validez": hoy + timedelta(days=365),
                  "usado": True, "fecha_uso": hoy},
    )
    factura, _ = Factura.objects.get_or_create(
        empresa=empresa, comprobante=comprobante,
        defaults={"fecha_factura": hoy, "fecha_inicio": conduces[0].fecha, "fecha_fin": hoy,
                  "cantidad_conduces": len(conduces), "conduce_inicial": conduces[0].numero,
                  "conduce_final": conduces[-1].numero, "subtotal_exento": Decimal("18750"),
                  "subtotal": Decimal("18750"), "total": Decimal("18750"), "estado": "emitida"},
    )
    DetalleFactura.objects.get_or_create(
        factura=factura, producto=producto.nombre_factura,
        defaults={"categoria": producto.categoria, "cantidad": 750,
                  "precio_sin_itbis": producto.precio_sin_itbis,
                  "aplica_itbis": producto.aplica_itbis, "valor": Decimal("18750")},
    )


def _generar_produccion(empresa):
    from inventario.models import (
        DetallePlanProduccion, DetalleRecetaProduccion, LoteInventario,
        OrdenProduccion, PlanProduccion, ProductoInventario, RecetaProduccion,
    )
    from inventario.produccion_services import generar_ordenes_desde_plan, transicionar_orden

    if OrdenProduccion.objects.filter(empresa=empresa, numero="DEMO-OP-0001").exists():
        return
    hoy = timezone.localdate(); user = empresa.usuario
    terminado, _ = ProductoInventario.objects.get_or_create(
        empresa=empresa, codigo="DEMO-PT-PROD",
        defaults={"nombre": "Pan terminado demo", "tipo": "producto_terminado",
                  "unidad_medida": "unidad", "stock_actual": Decimal("0"), "activo": True},
    )
    materia, _ = ProductoInventario.objects.get_or_create(
        empresa=empresa, codigo="DEMO-MP-HARINA",
        defaults={"nombre": "Harina demo", "tipo": "materia_prima", "clasificacion_operativa": "materia_prima",
                  "unidad_medida": "kg", "stock_actual": Decimal("100"), "activo": True},
    )
    LoteInventario.objects.get_or_create(
        empresa=empresa, producto=materia, lote="DEMO-HARINA-L1",
        defaults={"fecha_ingreso": hoy, "fecha_vencimiento": hoy + timedelta(days=120),
                  "cantidad_inicial": Decimal("100"), "cantidad_disponible": Decimal("100")},
    )
    receta, _ = RecetaProduccion.objects.get_or_create(
        empresa=empresa, codigo="DEMO-REC-001",
        defaults={"nombre": "Receta pan demo", "producto_terminado": terminado, "version": 1,
                  "rendimiento_base": Decimal("100"), "unidad_rendimiento": "unidad",
                  "porcentaje_merma_estimada": Decimal("2"), "activa": True,
                  "fecha_vigencia_desde": hoy, "creado_por": user},
    )
    DetalleRecetaProduccion.objects.get_or_create(
        receta=receta, materia_prima=materia,
        defaults={"cantidad": Decimal("10"), "unidad_medida": "kg", "porcentaje_merma": Decimal("2")},
    )
    plan = PlanProduccion.objects.create(
        empresa=empresa, numero="DEMO-PLAN-0001", fecha_plan=hoy,
        estado=PlanProduccion.Estado.APROBADO, origen=PlanProduccion.Origen.MANUAL,
        observaciones="Plan sintético RC1", creado_por=user, aprobado_por=user,
        fecha_aprobacion=timezone.now(),
    )
    DetallePlanProduccion.objects.create(
        plan=plan, producto_terminado=terminado, receta=receta,
        cantidad_solicitada=Decimal("100"), cantidad_planificada=Decimal("100"),
        unidad_medida="unidad", fecha_requerida=hoy,
    )
    orden = generar_ordenes_desde_plan(plan=plan, empresa=empresa, usuario=user)[0]
    orden.numero = "DEMO-OP-0001"; orden.save(update_fields=["numero"])
    orden = transicionar_orden(orden=orden, empresa=empresa, usuario=user, accion="programar")
    orden = transicionar_orden(orden=orden, empresa=empresa, usuario=user, accion="iniciar", cantidad_iniciada=100)
    transicionar_orden(orden=orden, empresa=empresa, usuario=user, accion="completar", cantidad_producida=98, cantidad_rechazada=2)


class Command(BaseCommand):
    help = "Orquesta datos sintéticos demo mediante generadores certificados y tenant-safe."

    def add_arguments(self, parser):
        parser.add_argument("--empresa", type=int, required=True)
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            empresa = Empresa.objects.get(pk=options["empresa"])
        except Empresa.DoesNotExist as exc:
            raise CommandError("Empresa no encontrada.") from exc
        if options["dry_run"]:
            self.stdout.write(f"Empresa {empresa.pk}; objetivos: {TARGETS}")
            self.stdout.write("Pipeline certificado: " + ", ".join(PIPELINE))
            return
        moneda, _ = Moneda.objects.get_or_create(
            codigo="DOP",
            defaults={"nombre": "Peso dominicano", "simbolo": "RD$"},
        )
        MonedaEmpresa.objects.get_or_create(
            empresa=empresa,
            moneda=moneda,
            defaults={"es_base": True, "activa": True},
        )
        for command in PIPELINE:
            call_command(command, empresa=empresa.pk)
        _generar_inabie(empresa)
        _generar_produccion(empresa)
        self.stdout.write(self.style.SUCCESS(
            "Pipeline demo ejecutado idempotentemente. Las transacciones O2C/P2P "
            "permanecen gobernadas por sus generadores y servicios certificados."
        ))
