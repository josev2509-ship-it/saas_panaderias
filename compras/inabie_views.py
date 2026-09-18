from uuid import uuid4

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from conduces.decorators import modulo_requerido
from conduces.services import obtener_empresa_usuario
from core.application.operation_context import OperationContext
from inventario.models import ProductoInventario
from .application.inabie_orders import (
    agregar_linea_inabie, editar_borrador_inabie, editar_linea_inabie,
    eliminar_linea_inabie, generar_borrador_inabie, usuario_puede_operar_inabie,
)
from .application.p2p import transicionar_orden
from .models import OrdenCompraEnterprise, Proveedor


class PeriodoForm(forms.Form):
    desde = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    hasta = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        datos = super().clean()
        if datos.get("desde") and datos.get("hasta") and datos["desde"] > datos["hasta"]:
            raise forms.ValidationError("La fecha inicial no puede superar la final.")
        return datos


def _context(request):
    return OperationContext(
        empresa=obtener_empresa_usuario(request), usuario=request.user, request=request,
        referencia=request.path,
        clave_idempotente=request.headers.get("Idempotency-Key") or f"inabie:{uuid4()}",
    )


def _permiso(request, codigo):
    if not usuario_puede_operar_inabie(request.user, codigo):
        raise PermissionDenied


@login_required
@modulo_requerido("modulo_compras")
@modulo_requerido("modulo_inabie")
def generar(request):
    _permiso(request, "add_ordencompraenterprise")
    form = PeriodoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            orden, creada = generar_borrador_inabie(context=_context(request), **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Borrador INABIE creado." if creada else "Ya existe un borrador u orden para ese período; se abrió el existente.")
            return redirect("compras:inabie_orden_detalle", pk=orden.pk)
    return render(request, "compras/inabie/generar.html", {"form": form})


@login_required
@modulo_requerido("modulo_compras")
@modulo_requerido("modulo_inabie")
def detalle(request, pk):
    _permiso(request, "view_ordencompraenterprise")
    empresa = obtener_empresa_usuario(request)
    orden = get_object_or_404(OrdenCompraEnterprise.objects.select_related("proveedor", "moneda__moneda"),
                              pk=pk, empresa=empresa, origen="INABIE")
    return render(request, "compras/inabie/detalle.html", {
        "orden": orden, "lineas": orden.detalles.select_related("producto").order_by("id"),
        "proveedores": Proveedor.objects.filter(empresa=empresa, estado="ACTIVO", bloqueado=False),
        "productos": ProductoInventario.objects.filter(empresa=empresa, activo=True).order_by("nombre"),
    })


@login_required
@require_POST
@modulo_requerido("modulo_compras")
@modulo_requerido("modulo_inabie")
def accion(request, pk, accion):
    ctx = _context(request)
    try:
        if accion == "guardar":
            editar_borrador_inabie(context=ctx, orden_id=pk,
                proveedor_id=request.POST.get("proveedor_id", ""),
                observaciones=request.POST.get("observaciones", ""))
        elif accion == "agregar":
            agregar_linea_inabie(context=ctx, orden_id=pk,
                producto_id=request.POST.get("producto_id"), cantidad=request.POST.get("cantidad"))
        elif accion == "presentar":
            _permiso(request, "change_ordencompraenterprise")
            transicionar_orden(context=ctx, orden_id=pk, nuevo="PENDIENTE_APROBACION")
        elif accion == "cancelar":
            _permiso(request, "cancelar_orden_compra")
            transicionar_orden(context=ctx, orden_id=pk, nuevo="CANCELADA")
        else:
            raise PermissionDenied
    except (ValidationError, ValueError, ProductoInventario.DoesNotExist, Proveedor.DoesNotExist) as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Borrador actualizado.")
    return redirect("compras:inabie_orden_detalle", pk=pk)


@login_required
@require_POST
@modulo_requerido("modulo_compras")
@modulo_requerido("modulo_inabie")
def accion_linea(request, pk, linea_id, accion):
    ctx = _context(request)
    try:
        if accion == "guardar":
            editar_linea_inabie(context=ctx, orden_id=pk, linea_id=linea_id,
                               cantidad=request.POST.get("cantidad"))
        elif accion == "eliminar":
            eliminar_linea_inabie(context=ctx, orden_id=pk, linea_id=linea_id)
        else:
            raise PermissionDenied
    except ValidationError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Línea actualizada.")
    return redirect("compras:inabie_orden_detalle", pk=pk)
