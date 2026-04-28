from django.urls import path
from django.http import HttpResponse
from . import views


def vista_no_disponible(request, *args, **kwargs):
    return HttpResponse(
        "Esta vista aún no está disponible o el nombre de la función no coincide en views.py.",
        status=404
    )


def obtener_vista(nombre):
    return getattr(views, nombre, vista_no_disponible)


urlpatterns = [
    # PANTALLA PRINCIPAL
    path('', obtener_vista('inicio'), name='inicio'),

    # CARGA DE DATOS
    path('carga-centros/', obtener_vista('pantalla_carga_centros'), name='carga_centros'),
    path('carga-menu/', obtener_vista('pantalla_carga_menu'), name='carga_menu'),

    path('plantilla-centros/', obtener_vista('descargar_plantilla_centros'), name='plantilla_centros'),
    path('plantilla-menu/', obtener_vista('descargar_plantilla_menu'), name='plantilla_menu'),

    path('cargar-centros/', obtener_vista('cargar_centros_excel'), name='cargar_centros_excel'),
    path('cargar-menu/', obtener_vista('cargar_menu_excel'), name='cargar_menu_excel'),

    # GENERACIÓN DE CONDUCES
    path('generar-conduces/', obtener_vista('generar_conduces_automaticos'), name='generar_conduces'),

    # CONSULTA Y GESTIÓN
    path('buscar-conduces/', obtener_vista('buscar_conduces'), name='buscar_conduces'),
    path('acciones-conduces/', obtener_vista('acciones_conduces'), name='acciones_conduces'),

    path('conduce/<int:conduce_id>/vista/', obtener_vista('vista_conduce'), name='vista_conduce'),
    path('conduce/<int:conduce_id>/editar/', obtener_vista('editar_conduce'), name='editar_conduce'),
    path('conduce/<int:conduce_id>/anular/', obtener_vista('anular_conduce'), name='anular_conduce'),
    path('conduce/<int:conduce_id>/pdf/', obtener_vista('visualizar_pdf_conduce'), name='visualizar_pdf_conduce'),

    # RELACIONES PDF
    path('relacion-diaria/pdf/', obtener_vista('generar_relacion_diaria_pdf'), name='generar_relacion_diaria_pdf'),
    path('relacion-general/pdf/', obtener_vista('generar_relacion_general_pdf'), name='generar_relacion_general_pdf'),
]