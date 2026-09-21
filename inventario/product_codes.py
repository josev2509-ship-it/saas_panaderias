"""Códigos de catálogo independientes por empresa y tipo."""

from django.db import transaction

from conduces.models import Empresa
from .models import ProductoInventario, SecuenciaProductoInventario


PREFIJOS = {"materia_prima": "MP", "producto_terminado": "PT", "empaque": "EMP", "consumible": "CON", "receta": "REC"}


def siguiente_codigo_producto(*, empresa, tipo):
    # El llamador debe crear el producto dentro de la misma transacción.
    with transaction.atomic():
        Empresa.objects.select_for_update().get(pk=empresa.pk)
        prefijo = PREFIJOS.get(tipo, "PRD")
        secuencia, _ = SecuenciaProductoInventario.objects.select_for_update().get_or_create(
            empresa=empresa, prefijo=prefijo)
        while True:
            secuencia.ultimo_numero += 1
            codigo = f"{prefijo}-{secuencia.ultimo_numero:06d}"
            if tipo == "receta":
                from .models import RecetaProduccion
                ocupado = RecetaProduccion.objects.filter(empresa=empresa, codigo=codigo).exists()
            else:
                ocupado = ProductoInventario.objects.filter(empresa=empresa, codigo=codigo).exists()
            if not ocupado:
                secuencia.save(update_fields=["ultimo_numero"])
                return codigo
