from compras.application.financial import actualizar_aging_cxp,reporte_cxp
from contabilidad.models import CuentaPorPagarEnterprise
def obtener(*,empresa,cuenta_id):return CuentaPorPagarEnterprise.objects.select_related("proveedor","factura","moneda__moneda").prefetch_related("movimientos","cuotas").get(pk=cuenta_id,empresa=empresa)
listar=reporte_cxp;actualizar_aging=actualizar_aging_cxp
