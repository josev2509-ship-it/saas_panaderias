from comercial.application.o2c_full import crear_despacho,autorizar_despacho,emitir_conduce
def crear(*,context,packing_ids):
    o=crear_despacho(context=context,packing_ids=packing_ids);return {"id":o.pk,"numero":o.numero,"estado":o.estado}
def autorizar(*,context,pk):return {"estado":autorizar_despacho(context=context,pk=pk).estado}
def conduce(*,context,pk):
    o=emitir_conduce(context=context,despacho_id=pk);return {"id":o.pk,"numero":o.numero}
