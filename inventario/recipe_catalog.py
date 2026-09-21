"""Asociación segura de ingredientes detectados con el catálogo por empresa."""

from django.core.exceptions import ValidationError

from .models import AliasIngredienteReceta, ProductoInventario
from .recipe_matching import ResultadoMatching, encontrar_ingrediente, normalizar_nombre
from .units import normalizar_unidad, unidades_compatibles
from .product_codes import siguiente_codigo_producto


UNIDADES_PROVISIONALES = {codigo for codigo, _ in ProductoInventario.UNIDADES_BASE}
CALIFICADORES_DISTINTIVOS = {"fuerte", "normal", "suave", "integral", "especial", "vegetal", "crema"}


def _nombre_limpio(nombre):
    return " ".join(str(nombre or "").split())


def evaluar_ingrediente(*, empresa, nombre, unidad):
    """Preview puro: nunca crea productos ni movimientos."""
    nombre = _nombre_limpio(nombre)
    unidad_canonica = normalizar_unidad(unidad)
    alias = AliasIngredienteReceta.objects.select_related("producto").filter(
        empresa=empresa, alias_normalizado=normalizar_nombre(nombre)).first()
    if alias:
        producto = alias.producto
        if producto.empresa_id == empresa.pk and producto.activo and producto.tipo == "materia_prima" and unidades_compatibles(producto.unidad_medida, unidad):
            return ResultadoMatching(nombre, "ALIAS_CONFIRMADO", producto.pk, producto.nombre)
        return ResultadoMatching(nombre, "REVISAR", candidatos=[{"id": producto.pk, "nombre": producto.nombre}])
    match = encontrar_ingrediente(empresa=empresa, nombre=nombre)
    if match.producto_id:
        producto = ProductoInventario.objects.filter(
            pk=match.producto_id, empresa=empresa, activo=True, tipo="materia_prima"
        ).first()
        if producto and unidades_compatibles(producto.unidad_medida, unidad) and match.estado == "EXACTA_NORMALIZADA":
            return match
        return ResultadoMatching(nombre, "REVISAR", candidatos=[{
            "id": match.producto_id, "nombre": match.producto_nombre,
        }])
    if match.estado == "SIN_COINCIDENCIA" and nombre and len(nombre) <= 180 and unidad_canonica in UNIDADES_PROVISIONALES:
        return ResultadoMatching(nombre, "PROVISIONAL", producto_nombre=nombre)
    # Un calificador explícito diferente identifica un insumo distinto; una
    # búsqueda genérica (p. ej. "Harina") sigue requiriendo revisión.
    calificadores = set(normalizar_nombre(nombre).split()) & CALIFICADORES_DISTINTIVOS
    if match.estado == "REVISAR" and calificadores and nombre and unidad_canonica in UNIDADES_PROVISIONALES:
        candidatos = ProductoInventario.objects.filter(
            pk__in=[c["id"] for c in match.candidatos], empresa=empresa,
        )
        if candidatos and all(
            (set(normalizar_nombre(p.nombre).split()) & CALIFICADORES_DISTINTIVOS)
            and (set(normalizar_nombre(p.nombre).split()) & CALIFICADORES_DISTINTIVOS).isdisjoint(calificadores)
            for p in candidatos
        ):
            return ResultadoMatching(nombre, "PROVISIONAL", producto_nombre=nombre)
    return match


def resolver_provisional_exacto(*, empresa, nombre, unidad):
    """Reutiliza solo igualdad normalizada; jamás recalcula un fuzzy del preview."""
    nombre = _nombre_limpio(nombre)
    unidad = normalizar_unidad(unidad)
    if not nombre or len(nombre) > 180 or unidad not in UNIDADES_PROVISIONALES:
        raise ValidationError("Nombre o unidad de ingrediente no aptos para crear un producto provisional.")
    # La igualdad normalizada conserva calificadores funcionales como
    # fuerte, normal, suave e integral. Nunca elegimos el primer candidato.
    iguales = [p for p in ProductoInventario.objects.filter(
        empresa=empresa, tipo="materia_prima", activo=True,
    ) if normalizar_nombre(p.nombre) == normalizar_nombre(nombre)]
    if len(iguales) > 1 or (iguales and not unidades_compatibles(iguales[0].unidad_medida, unidad)):
        raise ValidationError(f"{nombre}: existen productos ambiguos o con unidad incompatible.")
    if iguales:
        return iguales[0]
    return ProductoInventario.objects.create(
        empresa=empresa, codigo=siguiente_codigo_producto(empresa=empresa, tipo="materia_prima"), nombre=nombre, tipo="materia_prima",
        clasificacion_operativa="materia_prima", afecta_produccion=True,
        unidad_medida=unidad, unidad_compra="", cantidad_por_empaque=1,
        stock_actual=0, stock_minimo=0, precio_unitario_compra=0,
        porcentaje_itbis=0, proveedor="", activo=True,
        origen_catalogo="RECETA", requiere_revision=True,
    )


def resolver_ingrediente_aprobado(*, empresa, nombre, unidad):
    """Compatibilidad con llamadas existentes; el lote usa decisiones fijadas."""
    match = evaluar_ingrediente(empresa=empresa, nombre=nombre, unidad=unidad)
    if match.producto_id:
        return ProductoInventario.objects.get(pk=match.producto_id, empresa=empresa)
    if match.estado != "PROVISIONAL":
        raise ValidationError(f"{nombre}: asociación ambigua o unidad incompatible; requiere revisión.")
    return resolver_provisional_exacto(empresa=empresa, nombre=nombre, unidad=unidad)


def confirmar_alias(*, empresa, nombre, producto, usuario):
    if producto.empresa_id != empresa.pk or producto.tipo != "materia_prima" or not producto.activo:
        raise ValidationError("El alias debe apuntar a una materia prima activa de la empresa.")
    clave = normalizar_nombre(nombre)
    if not clave:
        raise ValidationError("El alias no puede estar vacío.")
    alias, creado = AliasIngredienteReceta.objects.get_or_create(
        empresa=empresa, alias_normalizado=clave,
        defaults={"producto": producto, "creado_por": usuario})
    if not creado and alias.producto_id != producto.pk:
        raise ValidationError("El alias ya fue confirmado para otro producto; requiere revisión.")
    return alias
