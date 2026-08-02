from comercial.application.o2c_full import registrar_cobro,aplicar_cobro
def registrar(*,context,**datos):
    o=registrar_cobro(context=context,**datos);return {"id":o.pk,"numero":o.numero,"estado":o.estado}
def aplicar(*,context,recibo_id,cuenta_id,monto):return {"cuenta_id":aplicar_cobro(context=context,recibo_id=recibo_id,cuenta_id=cuenta_id,monto=monto).pk}
