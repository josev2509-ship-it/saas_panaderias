from datetime import timedelta
from decimal import Decimal
from django.core.management.base import CommandError
from django.utils import timezone
from catalogos.models import MonedaEmpresa
from inventario.models import ProductoInventario
from comercial.models import Cliente,ContactoCliente,DireccionCliente,ProductoComercial,ListaPrecio,DetalleListaPrecio
from ._o2c_base import EmpresaCommand
class Command(EmpresaCommand):
    mutates=True
    def handle(self,*a,**o):
        e=self.empresa(o)
        if o["dry_run"]:return self.stdout.write("Se generarían idempotentemente 50 clientes, 100 productos comerciales y listas demo; cotizaciones y pedidos se crean mediante el flujo certificado.")
        moneda=MonedaEmpresa.objects.filter(empresa=e,activa=True).order_by("-es_base").first()
        if not moneda:raise CommandError("Configure una moneda activa para la empresa.")
        for i in range(1,51):
            c,_=Cliente.objects.get_or_create(empresa=e,codigo=f"DEMO-C{i:03d}",defaults={"tipo_cliente":Cliente.Tipo.CLIENTE_PRIVADO,"nombre_comercial":f"Cliente Demo {i}","rnc_cedula":f"DEMOCLI{i:06d}","correo":f"cliente-{i}@example.invalid","condicion_pago":Cliente.CondicionPago.CREDITO,"dias_credito":30,"limite_credito":Decimal("100000"),"moneda_comercial":moneda,"creado_por":e.usuario})
            ContactoCliente.objects.get_or_create(cliente=c,nombre="Contacto Demo",defaults={"correo":f"contacto-{i}@example.invalid","es_principal":True,"recibe_facturas":True})
            DireccionCliente.objects.get_or_create(cliente=c,nombre="Entrega Demo",defaults={"tipo":DireccionCliente.Tipo.ENTREGA,"direccion":f"Dirección sintética {i}","es_principal":True})
        for i in range(1,101):
            inv,_=ProductoInventario.objects.get_or_create(empresa=e,codigo=f"DEMO-P{i:03d}",defaults={"nombre":f"Producto Demo {i}","tipo":"producto_terminado","clasificacion_operativa":"producto_terminado","unidad_medida":"unidad"})
            ProductoComercial.objects.get_or_create(empresa=e,codigo=f"DEMO-PC{i:03d}",defaults={"producto_inventario":inv,"nombre":f"Producto Comercial Demo {i}","unidad_venta":"unidad","precio_base":Decimal(i+10),"moneda":moneda})
        lista,_=ListaPrecio.objects.get_or_create(empresa=e,codigo="DEMO-GENERAL",version=1,defaults={"nombre":"Lista general demo","moneda":moneda,"vigencia_desde":timezone.localdate(),"vigencia_hasta":timezone.localdate()+timedelta(days=365),"estado":"ACTIVA","predeterminada":True,"creado_por":e.usuario})
        for p in ProductoComercial.objects.filter(empresa=e,codigo__startswith="DEMO-PC")[:100]:DetalleListaPrecio.objects.get_or_create(lista=lista,producto=p,presentacion="",cantidad_minima=1,defaults={"precio":p.precio_base})
        self.stdout.write(self.style.SUCCESS("Datos demo O2C parte 1 generados idempotentemente."))
