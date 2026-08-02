from comercial.application.o2c_full import crear_factura_desde_entrega,emitir_factura
def crear(*,context,entrega_id,vence_el,ncf=""):
    o=crear_factura_desde_entrega(context=context,entrega_id=entrega_id,vence_el=vence_el,ncf=ncf);return {"id":o.pk,"numero":o.numero,"estado":o.estado}
def emitir(*,context,pk):
    o=emitir_factura(context=context,pk=pk);return {"id":o.pk,"estado":o.estado,"cxc_id":o.cuenta_cobrar.pk}
