from django.db.models import Sum,Count,Q
from comercial.models import Cliente,ProductoComercial,ListaPrecio,CotizacionVenta,Pedido,ProgramacionPedido
def clientes_360(empresa):return Cliente.objects.filter(empresa=empresa).select_related("segmento","clasificacion","canal","vendedor","equipo","zona","ruta","moneda_comercial","condicion_pago_catalogo")
def productos_comerciales(empresa):return ProductoComercial.objects.filter(empresa=empresa).select_related("producto_inventario","moneda","impuesto","canal")
def listas_precio(empresa):return ListaPrecio.objects.filter(empresa=empresa).select_related("moneda","cliente","segmento","canal","zona").prefetch_related("detalles__producto")
def cotizaciones(empresa):return CotizacionVenta.objects.filter(empresa=empresa).select_related("cliente","moneda","oportunidad").prefetch_related("detalles__producto")
def pedidos_o2c(empresa):return Pedido.objects.filter(empresa=empresa).select_related("cliente","cotizacion_origen","direccion_entrega")
def programaciones(empresa):return ProgramacionPedido.objects.filter(empresa=empresa).select_related("pedido__cliente","ruta","zona","vendedor").prefetch_related("pedido__detalles__producto")
def resumen_o2c(empresa):
    c=clientes_360(empresa);q=cotizaciones(empresa);p=pedidos_o2c(empresa)
    return {"clientes_activos":c.filter(estado="ACTIVO").count(),"clientes_bloqueados":c.filter(estado="BLOQUEADO_CREDITO").count(),"credito_total":c.aggregate(v=Sum("limite_credito"))["v"] or 0,"credito_utilizado":c.aggregate(v=Sum("credito_utilizado"))["v"] or 0,"productos_venta":productos_comerciales(empresa).filter(activo=True,disponible_venta=True).count(),"listas_activas":listas_precio(empresa).filter(estado="ACTIVA").count(),"cotizaciones_revision":q.filter(estado="EN_REVISION").count(),"cotizaciones_aceptadas":q.filter(estado="ACEPTADA").count(),"pedidos_pendientes":p.filter(estado="PENDIENTE_APROBACION").count(),"pedidos_programados":p.filter(estado="PROGRAMADO").count()}
