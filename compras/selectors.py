from django.db.models import Count, Q, Sum

from .models import Proveedor, SolicitudCompra


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


def solicitudes_empresa(*,empresa,usuario=None,filtros=None):
    qs=SolicitudCompra.objects.filter(empresa=empresa).select_related("solicitante","centro_costo","tipo_compra","moneda__moneda","proveedor_sugerido","workflow_instancia").prefetch_related("lineas")
    if usuario and not usuario.has_perm("compras.view_todas_solicitudescompra"): qs=qs.filter(solicitante=usuario)
    filtros=filtros or {}
    if filtros.get("q"): qs=qs.filter(Q(numero__icontains=filtros["q"])|Q(titulo__icontains=filtros["q"]))
    for key in ("estado","prioridad","centro_costo","tipo_compra","proveedor_sugerido","solicitante"):
        if filtros.get(key): qs=qs.filter(**{key:filtros[key]})
    if filtros.get("desde"): qs=qs.filter(fecha_solicitud__gte=filtros["desde"])
    if filtros.get("hasta"): qs=qs.filter(fecha_solicitud__lte=filtros["hasta"])
    if filtros.get("urgentes"): qs=qs.filter(es_urgente=True)
    return qs

def dashboard_solicitudes(*,empresa):
    qs=SolicitudCompra.objects.filter(empresa=empresa);totals=qs.aggregate(total=Sum("total_estimado"),aprobado=Sum("total_estimado",filter=Q(estado="APROBADA")))
    return {"estados":{state:qs.filter(estado=state).count() for state in SolicitudCompra.Estado.values},"urgentes":qs.filter(es_urgente=True).count(),"presupuesto_no_validado":qs.filter(disponibilidad_presupuestaria="NO_VALIDADA").count(),"total_estimado":totals["total"] or 0,"total_aprobado":totals["aprobado"] or 0,"por_centro":qs.values("centro_costo__nombre").annotate(total=Count("id")).order_by("-total")[:10],"por_prioridad":qs.values("prioridad").annotate(total=Count("id"))}
