from comercial.application.o2c_full import solicitar_factoring
def solicitar(*,context,**datos):
    o=solicitar_factoring(context=context,**datos);return {"id":o.pk,"numero":o.numero,"estado":o.estado}
