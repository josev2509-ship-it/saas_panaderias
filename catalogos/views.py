from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from conduces.decorators import modulo_requerido
from conduces.services import obtener_empresa_usuario

from .forms import (
    AlmacenForm, CentroCostoForm, CondicionPagoForm, ConversionUnidadForm,
    ImpuestoForm, MonedaEmpresaForm, TipoCompraForm, UnidadMedidaForm,
)
from .models import (
    Almacen, CentroCosto, CondicionPago, ConversionUnidad, Impuesto,
    MonedaEmpresa, TipoCompra, UnidadMedida,
)
from .services import cambiar_actividad, guardar_catalogo

CATALOGOS = {
    "condiciones-pago": (CondicionPago, CondicionPagoForm, "Condiciones de pago"),
    "unidades": (UnidadMedida, UnidadMedidaForm, "Unidades de medida"),
    "conversiones": (ConversionUnidad, ConversionUnidadForm, "Conversiones"),
    "almacenes": (Almacen, AlmacenForm, "Almacenes"),
    "centros-costo": (CentroCosto, CentroCostoForm, "Centros de costo"),
    "impuestos": (Impuesto, ImpuestoForm, "Impuestos"),
    "tipos-compra": (TipoCompra, TipoCompraForm, "Tipos de compra"),
    "monedas": (MonedaEmpresa, MonedaEmpresaForm, "Monedas habilitadas"),
}


def _config(clave):
    try:
        return CATALOGOS[clave]
    except KeyError as exc:
        raise Http404 from exc


@login_required
@modulo_requerido("modulo_catalogos", "catalogos.view_condicionpago")
def centro(request):
    return render(request, "catalogos/centro.html", {"catalogos": CATALOGOS})


@login_required
@modulo_requerido("modulo_catalogos")
def lista(request, clave):
    model, _, titulo = _config(clave)
    permiso = f"{model._meta.app_label}.view_{model._meta.model_name}"
    if not request.user.has_perm(permiso):
        raise PermissionDenied
    empresa = obtener_empresa_usuario(request)
    queryset = model.objects.filter(empresa=empresa)
    termino = request.GET.get("q", "").strip()
    if termino and hasattr(model, "nombre"):
        queryset = queryset.filter(Q(nombre__icontains=termino) | Q(codigo__icontains=termino))
    return render(request, "catalogos/lista.html", {
        "titulo": titulo, "clave": clave, "objetos": Paginator(queryset, 25).get_page(request.GET.get("page")), "q": termino,
    })


@login_required
@modulo_requerido("modulo_catalogos")
def editar(request, clave, pk=None):
    model, form_class, titulo = _config(clave)
    permiso = f"{model._meta.app_label}.{'change' if pk else 'add'}_{model._meta.model_name}"
    if not request.user.has_perm(permiso):
        raise PermissionDenied
    empresa = obtener_empresa_usuario(request)
    objeto = get_object_or_404(model, pk=pk, empresa=empresa) if pk else model()
    form = form_class(request.POST or None, instance=objeto, empresa=empresa)
    if request.method == "POST" and form.is_valid():
        if model is MonedaEmpresa:
            nuevo = form.save(commit=False)
            nuevo.empresa = empresa
            nuevo.save()
        else:
            guardar_catalogo(instancia=objeto, empresa=empresa, usuario=request.user, datos=form.cleaned_data, request=request)
        return redirect("catalogos:lista", clave=clave)
    return render(request, "catalogos/form.html", {"form": form, "titulo": titulo, "objeto": objeto, "clave": clave})


@login_required
@modulo_requerido("modulo_catalogos")
def actividad(request, clave, pk):
    model, _, _ = _config(clave)
    if request.method != "POST" or not request.user.has_perm(f"{model._meta.app_label}.change_{model._meta.model_name}"):
        raise PermissionDenied
    empresa = obtener_empresa_usuario(request)
    objeto = get_object_or_404(model, pk=pk, empresa=empresa)
    cambiar_actividad(model=model, pk=pk, empresa=empresa, usuario=request.user, activo=not objeto.activo, request=request)
    return redirect("catalogos:lista", clave=clave)
