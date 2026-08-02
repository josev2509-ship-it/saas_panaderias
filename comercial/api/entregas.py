from comercial.application.o2c_full import confirmar_entrega
def confirmar(*,context,conduce_id,receptor):
    o=confirmar_entrega(context=context,conduce_id=conduce_id,receptor=receptor);return {"id":o.pk,"numero":o.numero,"estado":o.estado}
