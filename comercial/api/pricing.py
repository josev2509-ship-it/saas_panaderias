from comercial.application.o2c import resolver_precio_comercial,crear_producto_comercial,crear_lista_precio,activar_lista_precio
def resolver_precio(**kwargs):return resolver_precio_comercial(**kwargs)
def crear_producto(**kwargs):return crear_producto_comercial(**kwargs).pk
def crear_lista(**kwargs):return crear_lista_precio(**kwargs).pk
def activar_lista(**kwargs):return activar_lista_precio(**kwargs).pk
