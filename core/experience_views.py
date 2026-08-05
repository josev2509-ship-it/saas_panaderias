from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from conduces.services import obtener_empresa_usuario
from comercial.models import Cliente, Pedido, Prospecto, OportunidadComercial, CotizacionVenta
from compras.models import Proveedor
from inventario.models import ProductoInventario
from comercial.models_o2c4 import FacturaVenta
from compras.p2p_models import OrdenCompraEnterprise, RecepcionCompra
from conduces.models import Conduce
from documentos.models import Documento
from contabilidad.models import FacturaProveedor
from .models import AlertaExperiencia, FavoritoNavegacion, NavegacionReciente


def _empresa(request):
    return obtener_empresa_usuario(request)


def _rol(user):
    names = set(user.groups.values_list("name", flat=True))
    rules = (("Director", "DIRECTOR"), ("Compr", "COMPRADOR"), ("Contab", "CONTABILIDAD"), ("Chofer", "CHOFER"), ("Comercial", "COMERCIAL"), ("Produ", "PRODUCCION"), ("Auditor", "AUDITOR"))
    for fragment, role in rules:
        if any(fragment.lower() in name.lower() for name in names): return role
    return "DIRECTOR" if user.is_superuser else "CONSULTA"


WORKSPACES = {
    "comercial": ("Comercial", "comercial:dashboard", ["CRM", "Clientes", "Cotizaciones", "Pedidos"]),
    "compras": ("Compras", "compras:dashboard", ["Solicitudes", "Expedientes", "RFQ", "Órdenes"]),
    "inventario": ("Inventario", "inventario:dashboard", ["Productos", "Movimientos", "Lotes", "Trazabilidad"]),
    "produccion": ("Producción", "inventario:produccion_dashboard", ["Planificación", "Órdenes", "Necesidades", "Calidad"]),
    "operaciones": ("Operaciones", "buscar_conduces", ["Conduces", "Despachos", "Entregas", "Facturación"]),
    "finanzas": ("Finanzas", "contabilidad:dashboard_enterprise", ["CxC", "CxP", "Tesorería", "Contabilidad"]),
}

QUICK_ACTIONS = {"DIRECTOR": (("Reportes", "comercial:dashboard"),), "COMPRADOR": (("Nueva solicitud", "compras:solicitud_crear"),), "COMERCIAL": (("Nuevo prospecto", "comercial:prospecto_crear"), ("Nuevo cliente", "comercial:cliente_crear"), ("Nueva cotización", "comercial:cotizacion_crear"), ("Nuevo pedido", "comercial:pedido_crear")), "CONTABILIDAD": (("Finanzas", "contabilidad:dashboard_enterprise"), ("Registrar cobro", "comercial:fin_cobro_registrar")), "PRODUCCION": (("Órdenes", "inventario:ordenes_lista"),), "CHOFER": (("Conduces", "buscar_conduces"),), "AUDITOR": (("Actividad", "core:actividad"),), "CONSULTA": ()}


ENTERPRISE_360 = {
    "cliente": (Cliente, "comercial.view_cliente", "nombre_comercial", ["Resumen", "Contactos", "Direcciones", "Cotizaciones", "Pedidos", "Entregas", "Facturas", "Cobros", "Crédito", "Documentos", "Actividad", "Auditoría"], []),
    "proveedor": (Proveedor, "compras.view_proveedor", "razon_social", ["Resumen", "Contactos", "Direcciones", "Solicitudes", "RFQ", "Ofertas", "Órdenes", "Recepciones", "Facturas", "Pagos", "Retenciones", "Compensaciones", "Documentos", "Actividad", "Auditoría"], []),
    "pedido": (Pedido, "comercial.view_pedido", "numero", ["Resumen", "Líneas", "Programación", "Reserva", "Preparación", "Despacho", "Entrega", "Facturación", "Cobros", "Documentos", "Actividad", "Auditoría"], ["Pedido", "Aprobación", "Reserva", "Picking", "Packing", "Despacho", "Entrega", "Factura", "Cobro"]),
    "orden": (OrdenCompraEnterprise, "compras.view_ordencompraenterprise", "numero", ["Resumen", "Líneas", "Adjudicación", "Recepciones", "Devoluciones", "Facturas", "Pagos", "Retenciones", "Compensaciones", "Documentos", "Actividad", "Auditoría"], ["Solicitud", "Expediente", "RFQ", "Comparativo", "Adjudicación", "Orden", "Recepción", "Factura", "Pago", "Conciliación"]),
    "factura-cliente": (FacturaVenta, "comercial.view_facturaventa", "numero", ["Resumen", "Líneas", "CxC", "Cobros", "Notas", "Factoring", "Contabilidad", "Documentos", "Actividad", "Auditoría"], []),
    "factura-proveedor": (FacturaProveedor, "contabilidad.view_facturaproveedor", "numero", ["Resumen", "Líneas", "Orden", "Recepción", "CxP", "Pagos", "Notas", "Anticipos", "Retenciones", "Compensaciones", "Contabilidad", "Documentos", "Actividad", "Auditoría"], []),
}

@login_required
def workspace_home(request):
    empresa = _empresa(request)
    _touch(request, empresa, "Inicio", "Mi Workspace")
    context = _personal_context(request, empresa)
    role = _rol(request.user)
    context.update({"rol_experiencia": role, "workspaces": WORKSPACES, "acciones_rapidas": QUICK_ACTIONS.get(role, ())})
    return render(request, "core/experience/home.html", context)


@login_required
def workspace(request, dominio):
    empresa = _empresa(request)
    if dominio not in WORKSPACES: return HttpResponseBadRequest("Workspace inválido")
    title, route, tabs = WORKSPACES[dominio]
    if dominio == "compras" and not (empresa.modulo_compras and request.user.has_perm("compras.view_proveedor")): return redirect("core:workspace_home")
    _touch(request, empresa, dominio, f"Workspace {title}")
    return render(request, "core/experience/workspace.html", {**_personal_context(request, empresa), "dominio": dominio, "titulo": title, "route": route, "tabs": tabs})


def _personal_context(request, empresa):
    alerts = AlertaExperiencia.objects.filter(empresa=empresa).filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return {"empresa": empresa, "favoritos": FavoritoNavegacion.objects.filter(empresa=empresa, usuario=request.user)[:8], "recientes": NavegacionReciente.objects.filter(empresa=empresa, usuario=request.user)[:8], "alertas_experiencia": alerts.exclude(estado="RESUELTA")[:8]}


def _touch(request, empresa, modulo, etiqueta):
    NavegacionReciente.objects.update_or_create(empresa=empresa, usuario=request.user, url=request.path[:500], defaults={"modulo": modulo[:40], "etiqueta": etiqueta[:120]})
    stale = NavegacionReciente.objects.filter(empresa=empresa, usuario=request.user).order_by("-visitado").values_list("pk", flat=True)[20:]
    NavegacionReciente.objects.filter(pk__in=list(stale)).delete()


@login_required
def busqueda_global(request):
    empresa, query, groups = _empresa(request), request.GET.get("q", "").strip()[:100], []
    _touch(request, empresa, "Navegación", "Búsqueda global")
    if len(query) >= 2:
        if request.user.has_perm("comercial.view_cliente"):
            groups.append(("Clientes", [(x.nombre_comercial, reverse("comercial:cliente_360", args=[x.pk])) for x in Cliente.objects.filter(empresa=empresa).filter(Q(nombre_comercial__icontains=query) | Q(rnc_cedula__icontains=query) | Q(codigo__icontains=query))[:8]]))
        if request.user.has_perm("compras.view_proveedor"):
            groups.append(("Proveedores", [(x.nombre_comercial or x.razon_social, reverse("compras:detalle", args=[x.pk])) for x in Proveedor.objects.filter(empresa=empresa).filter(Q(nombre_comercial__icontains=query) | Q(razon_social__icontains=query) | Q(codigo__icontains=query))[:8]]))
        if request.user.has_perm("comercial.view_pedido"):
            groups.append(("Pedidos", [(str(x), reverse("comercial:pedido_detalle", args=[x.pk])) for x in Pedido.objects.filter(empresa=empresa).filter(Q(numero__icontains=query) | Q(cliente__nombre_comercial__icontains=query))[:8]]))
        if request.user.has_perm("comercial.view_cotizacionventa"):
            groups.append(("Cotizaciones", [(x.numero, reverse("comercial:cotizacion_detalle", args=[x.pk])) for x in CotizacionVenta.objects.filter(empresa=empresa).filter(Q(numero__icontains=query) | Q(cliente__nombre_comercial__icontains=query))[:8]]))
        if request.user.has_perm("comercial.view_prospecto"):
            groups.append(("Prospectos", [(x.nombre, reverse("comercial:prospecto_detalle", args=[x.pk])) for x in Prospecto.objects.filter(empresa=empresa, nombre__icontains=query)[:8]]))
        if request.user.has_perm("inventario.view_productoinventario"):
            groups.append(("Productos", [(x.nombre, reverse("inventario:productos")) for x in ProductoInventario.objects.filter(empresa=empresa, nombre__icontains=query)[:8]]))
        if request.user.has_perm("comercial.view_facturaventa"):
            groups.append(("Facturas cliente", [(x.numero, reverse("comercial:o2c_full_lista", args=["facturas"])) for x in FacturaVenta.objects.filter(empresa=empresa, numero__icontains=query)[:8]]))
        if request.user.has_perm("compras.view_ordencompraenterprise") and empresa.modulo_compras:
            groups.append(("Órdenes de compra", [(x.numero, reverse("compras:p2p_recurso_detalle", args=["ordenes", x.pk])) for x in OrdenCompraEnterprise.objects.filter(empresa=empresa, numero__icontains=query)[:8]]))
        if request.user.has_perm("compras.view_recepcioncompra") and empresa.modulo_compras:
            groups.append(("Recepciones", [(x.numero, reverse("compras:p2p_recurso_detalle", args=["recepciones", x.pk])) for x in RecepcionCompra.objects.filter(empresa=empresa, numero__icontains=query)[:8]]))
        if request.user.has_perm("contabilidad.view_facturaproveedor") and empresa.modulo_compras:
            groups.append(("Facturas proveedor", [(x.numero, reverse("compras:p2p_recurso_detalle", args=["facturas", x.pk])) for x in FacturaProveedor.objects.filter(empresa=empresa, numero__icontains=query)[:8]]))
        if empresa.modulo_conduces:
            groups.append(("Conduces", [(x.numero or str(x.pk), reverse("vista_conduce", args=[x.pk])) for x in Conduce.objects.filter(empresa=empresa, numero__icontains=query)[:8]]))
        if request.user.has_perm("documentos.view_documento"):
            groups.append(("Documentos", [(x.titulo, reverse("documentos:detalle", args=[x.pk])) for x in Documento.objects.filter(empresa=empresa, confidencial=False, titulo__icontains=query)[:8]]))
    return render(request, "core/experience/search.html", {"empresa": empresa, "query": query, "resultados": [(k, v) for k, v in groups if v]})


@login_required
def alertas(request):
    qs = AlertaExperiencia.objects.filter(empresa=_empresa(request)).filter(Q(usuario=request.user) | Q(usuario__isnull=True))
    return render(request, "core/experience/alerts.html", {"alertas_experiencia": qs})


@login_required
def actividad(request):
    qs = NavegacionReciente.objects.filter(empresa=_empresa(request), usuario=request.user)
    if request.GET.get("q"): qs = qs.filter(Q(etiqueta__icontains=request.GET["q"][:100]) | Q(modulo__icontains=request.GET["q"][:100]))
    if request.GET.get("modulo"): qs = qs.filter(modulo=request.GET["modulo"][:40])
    if request.GET.get("fecha"): qs = qs.filter(visitado__date=request.GET["fecha"])
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    return render(request, "core/experience/activity.html", {"recientes": page, "modulos": NavegacionReciente.objects.filter(empresa=_empresa(request), usuario=request.user).values_list("modulo", flat=True).distinct()})


@login_required
def enterprise_360(request, tipo, pk):
    if tipo not in ENTERPRISE_360: return HttpResponseBadRequest("Vista 360 inválida")
    model, permission, label_field, tabs, timeline = ENTERPRISE_360[tipo]
    if not request.user.has_perm(permission):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    empresa = _empresa(request)
    objeto = get_object_or_404(model, pk=pk, empresa=empresa)
    _touch(request, empresa, "360", f"{tipo}: {getattr(objeto, label_field)}")
    kpis = [("Estado", getattr(objeto, "estado", "Disponible")), ("Total", getattr(objeto, "total", "—")), ("Referencia", getattr(objeto, label_field))]
    return render(request, "core/experience/enterprise_360.html", {"empresa": empresa, "objeto": objeto, "tipo": tipo, "titulo_360": getattr(objeto, label_field), "tabs_360": tabs, "timeline_360": timeline, "kpis_360": kpis})


@require_POST
@login_required
def favorito_toggle(request):
    empresa, url = _empresa(request), request.POST.get("url", "")[:500]
    if not url.startswith("/"): return HttpResponseBadRequest("URL inválida")
    item, created = FavoritoNavegacion.objects.get_or_create(empresa=empresa, usuario=request.user, url=url, defaults={"etiqueta": request.POST.get("etiqueta", "Favorito")[:120], "tipo": request.POST.get("tipo", "pantalla")[:30]})
    if not created: item.delete()
    if request.headers.get("x-requested-with") == "XMLHttpRequest": return JsonResponse({"favorite": created})
    messages.success(request, "Favorito agregado." if created else "Favorito eliminado.")
    return redirect(request.POST.get("next") or "core:workspace_home")


@require_POST
@login_required
def alerta_accion(request, pk, accion):
    alert = get_object_or_404(AlertaExperiencia.objects.filter(Q(usuario=request.user) | Q(usuario__isnull=True)), pk=pk, empresa=_empresa(request))
    states = {"leer": "LEIDA", "posponer": "POSPUESTA", "resolver": "RESUELTA"}
    if accion not in states: return HttpResponseBadRequest("Acción inválida")
    alert.estado = states[accion]; alert.save(update_fields=["estado", "actualizado"])
    return redirect("core:alertas")
