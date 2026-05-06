from django.urls import path
from django.http import HttpResponse
from . import views


# ==========================
# FALLBACK
# ==========================
def vista_no_disponible(request, *args, **kwargs):
    return HttpResponse(
        "Vista no disponible o no encontrada en views.py",
        status=404
    )


# ==========================
# FUNCIÓN DINÁMICA
# ==========================
def obtener_vista(nombre):
    return getattr(views, nombre, vista_no_disponible)


urlpatterns = [

    # ================= DASHBOARD =================
    path('', obtener_vista('inicio'), name='inicio'),

    # ================= CENTROS =================
    path('carga-centros/', obtener_vista('pantalla_carga_centros'), name='carga_centros'),
    path('cargar-centros/', obtener_vista('cargar_centros_excel'), name='cargar_centros_excel'),
    path('plantilla-centros/', obtener_vista('descargar_plantilla_centros'), name='plantilla_centros'),

    path('centros/crear/', obtener_vista('crear_centro'), name='crear_centro'),
    path('centros/editar/<int:centro_id>/', obtener_vista('editar_centro'), name='editar_centro'),
    path('centros/eliminar/<int:centro_id>/', obtener_vista('eliminar_centro'), name='eliminar_centro'),

    path('centros/mapa/', obtener_vista('mapa_centros'), name='mapa_centros'),
    path('centros/mapa/actualizar-ubicacion/', obtener_vista('actualizar_ubicacion_centro'), name='actualizar_ubicacion_centro'),

    # ================= MENÚ =================
    path('carga-menu/', obtener_vista('pantalla_carga_menu'), name='carga_menu'),
    path('cargar-menu/', obtener_vista('cargar_menu_excel'), name='cargar_menu_excel'),
    path('plantilla-menu/', obtener_vista('descargar_plantilla_menu'), name='plantilla_menu'),

    path('menu/crear/', obtener_vista('crear_menu_diario'), name='crear_menu_diario'),
    path('menu/editar/<int:menu_id>/', obtener_vista('editar_menu_diario'), name='editar_menu_diario'),
    path('menu/eliminar/<int:menu_id>/', obtener_vista('eliminar_menu_diario'), name='eliminar_menu_diario'),

    # ================= CONDUCES =================
    path('generar-conduces/', obtener_vista('generar_conduces_automaticos'), name='generar_conduces'),

    path('buscar-conduces/', obtener_vista('buscar_conduces'), name='buscar_conduces'),
    path('acciones-conduces/', obtener_vista('acciones_conduces'), name='acciones_conduces'),

    path('conduce/<int:conduce_id>/vista/', obtener_vista('vista_conduce'), name='vista_conduce'),
    path('conduce/<int:conduce_id>/editar/', obtener_vista('editar_conduce'), name='editar_conduce'),
    path('conduce/<int:conduce_id>/anular/', obtener_vista('anular_conduce'), name='anular_conduce'),
    path('conduce/<int:conduce_id>/eliminar/', obtener_vista('eliminar_conduce'), name='eliminar_conduce'),
    path('conduce/<int:conduce_id>/pdf/', obtener_vista('visualizar_pdf_conduce'), name='visualizar_pdf_conduce'),

    # ================= REPORTES =================
    path('relacion-diaria/pdf/', obtener_vista('generar_relacion_diaria_pdf'), name='generar_relacion_diaria_pdf'),
    path('relacion-general/pdf/', obtener_vista('generar_relacion_general_pdf'), name='generar_relacion_general_pdf'),

    # ================= FACTURACIÓN =================
    path('facturacion/', obtener_vista('facturacion'), name='facturacion'),
    path('facturacion/generar/', obtener_vista('generar_factura'), name='generar_factura'),

    path('facturacion/<int:factura_id>/pdf/', obtener_vista('pdf_factura'), name='pdf_factura'),
    path('facturacion/<int:factura_id>/editar/', obtener_vista('editar_factura'), name='editar_factura'),
    path('facturacion/<int:factura_id>/anular/', obtener_vista('anular_factura'), name='anular_factura'),
    path('facturacion/<int:factura_id>/eliminar/', obtener_vista('eliminar_factura'), name='eliminar_factura'),

    path('facturacion/productos/crear/', obtener_vista('crear_producto_facturacion'), name='crear_producto_facturacion'),
    path('facturacion/productos/<int:producto_id>/editar/', obtener_vista('editar_producto_facturacion'), name='editar_producto_facturacion'),
    path('facturacion/productos/<int:producto_id>/eliminar/', obtener_vista('eliminar_producto_facturacion'), name='eliminar_producto_facturacion'),

    path('facturacion/comprobantes/crear/', obtener_vista('crear_comprobante_fiscal'), name='crear_comprobante_fiscal'),
    path('facturacion/comprobantes/<int:comprobante_id>/editar/', obtener_vista('editar_comprobante'), name='editar_comprobante'),
    path('facturacion/comprobantes/<int:comprobante_id>/eliminar/', obtener_vista('eliminar_comprobante'), name='eliminar_comprobante'),
    path('facturacion/ncf/rango/', obtener_vista('crear_rango_ncf'), name='crear_rango_ncf'),

    # ================= CONFIGURACIÓN EMPRESA =================
    path('mi-empresa/', obtener_vista('mi_empresa'), name='mi_empresa'),
    path('mi-empresa/usuarios/crear/', obtener_vista('crear_usuario_empresa'), name='crear_usuario_empresa'),

    # ================= CARTAS ADMINISTRATIVAS =================
    path('cartas/', obtener_vista('cartas_administrativas'), name='cartas_administrativas'),
    path('cartas/generar-pdf/', obtener_vista('generar_carta_pdf'), name='generar_carta_pdf'),
    
    # ================= AUTENTICACIÓN =================
    path('registro/', obtener_vista('registro'), name='registro'),
    path('verificar-correo/', obtener_vista('verificar_correo'), name='verificar_correo'),
    path('reenviar-codigo/', obtener_vista('reenviar_codigo_correo'), name='reenviar_codigo_correo'),
    path('login/', obtener_vista('login_usuario'), name='login_usuario'),
    path('logout/', obtener_vista('logout_usuario'), name='logout_usuario'),
]
