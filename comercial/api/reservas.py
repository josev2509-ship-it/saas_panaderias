from comercial.application.o2c_full import consultar_disponibilidad,crear_reserva_desde_pedido,reservar_inventario
def disponibilidad(*,context,pedido):return consultar_disponibilidad(context=context,pedido=pedido)
def reservar(*,context,pedido_id):
    r=crear_reserva_desde_pedido(context=context,pedido_id=pedido_id);r=reservar_inventario(context=context,reserva_id=r.pk);return {"id":r.pk,"numero":r.numero,"estado":r.estado}
