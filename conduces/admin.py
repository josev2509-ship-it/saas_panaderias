from django.contrib import admin, messages
from .models import Empresa, CentroEducativo, MenuDiario, Conduce


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rnc', 'telefono', 'ciudad', 'correo')


@admin.register(CentroEducativo)
class CentroEducativoAdmin(admin.ModelAdmin):
    change_form_template = "admin/centros_form.html"

    list_display = (
        'orden_carga',
        'codigo',
        'nombre',
        'director',
        'telefono',
        'direccion',
        'provincia',
        'regional_distrito',
        'matricula',
    )

    search_fields = ('codigo', 'nombre', 'director')


@admin.register(MenuDiario)
class MenuDiarioAdmin(admin.ModelAdmin):
    change_form_template = "admin/menu_form.html"
    list_display = ('fecha', 'producto')
    search_fields = ('producto',)
    list_filter = ('fecha',)


@admin.action(description="Eliminar conduces seleccionados")
def eliminar_conduces_seleccionados(modeladmin, request, queryset):
    total = queryset.count()
    queryset.delete()

    modeladmin.message_user(
        request,
        f"Se eliminaron correctamente {total} conduces.",
        messages.SUCCESS
    )


@admin.register(Conduce)
class ConduceAdmin(admin.ModelAdmin):
    change_list_template = "admin/conduces_changelist.html"

    list_display = (
        'numero',
        'fecha',
        'empresa',
        'centro',
        'producto',
        'cantidad',
        'estado',
    )

    fields = (
        'empresa',
        'numero',
        'fecha',
        'centro',
        'producto',
        'cantidad',
        'observaciones',
        'estado',
    )

    search_fields = (
        'numero',
        'centro__codigo',
        'centro__nombre',
        'empresa__nombre',
    )

    list_filter = (
        'fecha',
        'empresa',
        'estado',
    )

    actions = [eliminar_conduces_seleccionados]

    list_per_page = 10000
    show_full_result_count = False