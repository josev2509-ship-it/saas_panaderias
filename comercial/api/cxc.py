from comercial.models import CuentaPorCobrar
def estado_cuenta(*,empresa,cliente_id):return [{"id":x.pk,"factura":x.factura.numero,"saldo":str(x.saldo),"estado":x.estado,"aging":x.bucket_aging} for x in CuentaPorCobrar.objects.filter(empresa=empresa,cliente_id=cliente_id).select_related("factura")]
