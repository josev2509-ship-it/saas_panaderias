from django.db.models import Q

from .models import Proveedor


def proveedores_empresa(*,empresa,filtros=None):
    qs=Proveedor.objects.filter(empresa=empresa).select_related("categoria","moneda_habitual__moneda","condicion_pago")
    filtros=filtros or {}
    if filtros.get("q"):
        q=filtros["q"]
        qs=qs.filter(Q(codigo__icontains=q)|Q(razon_social__icontains=q)|Q(nombre_comercial__icontains=q)|Q(rnc_normalizado__icontains=q))
    for campo in ("estado","categoria","nivel_riesgo","moneda_habitual","condicion_pago"):
        if filtros.get(campo): qs=qs.filter(**{campo:filtros[campo]})
    for campo in ("documentacion_completa","es_proveedor_critico","es_preferido"):
        if filtros.get(campo) in {"0","1"}: qs=qs.filter(**{campo:filtros[campo]=="1"})
    return qs
