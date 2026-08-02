from comercial.application.o2c_full import crear_preparacion,generar_picking,crear_packing
def preparar(*,context,reserva_id):
    o=crear_preparacion(context=context,reserva_id=reserva_id);return {"id":o.pk,"numero":o.numero,"estado":o.estado}
def picking(*,context,preparacion_id):return {"id":generar_picking(context=context,preparacion_id=preparacion_id).pk}
def packing(*,context,picking_id):return {"id":crear_packing(context=context,picking_id=picking_id).pk}
