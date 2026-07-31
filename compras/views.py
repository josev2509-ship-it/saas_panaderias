import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from conduces.decorators import modulo_requerido
from conduces.services import obtener_empresa_usuario
from core.application.operation_context import OperationContext
from documentos.services import obtener_documentos
from .application.proveedores import (
    activar_proveedor, bloquear_proveedor, crear_contacto_proveedor,
    crear_direccion_proveedor, crear_proveedor, inactivar_proveedor,
    reactivar_proveedor, registrar_cuenta_bancaria, rechazar_cuenta_bancaria,
    suspender_proveedor, verificar_cuenta_bancaria,
    vincular_producto_proveedor, vincular_proveedor_legado,
)
from .forms import (
    ContactoProveedorForm, CuentaBancariaProveedorForm, DireccionProveedorForm,
    ProductoProveedorForm, ProveedorForm, ProveedorLegadoMapForm, TransicionForm,
)
from .models import CuentaBancariaProveedor, Proveedor, ProveedorLegadoMap
from .selectors import proveedores_empresa


def _empresa(request): return obtener_empresa_usuario(request)
def _context(request): return OperationContext(empresa=_empresa(request),usuario=request.user,request=request,referencia=request.path)


@login_required
@modulo_requerido("modulo_compras","compras.view_proveedor")
def dashboard(request):
    qs=Proveedor.objects.filter(empresa=_empresa(request))
    resumen={x:qs.filter(estado=x).count() for x in Proveedor.Estado.values}
    return render(request,"compras/dashboard.html",{
        "resumen":resumen,"total":qs.count(),"criticos":qs.filter(es_proveedor_critico=True).count(),
        "sin_contacto":qs.exclude(contactos__principal=True,contactos__activo=True).count(),
        "sin_fiscal":qs.exclude(direcciones__tipo="FISCAL",direcciones__activa=True).count(),
        "revision_pendiente":qs.filter(Q(proxima_revision_documental__lte=timezone.localdate())|Q(documentacion_completa=False)).distinct().count(),
        "por_categoria":qs.values("categoria__nombre").annotate(total=Count("id")).order_by("-total"),
        "por_riesgo":qs.values("nivel_riesgo").annotate(total=Count("id")).order_by("nivel_riesgo"),
    })


@login_required
@modulo_requerido("modulo_compras","compras.view_proveedor")
def lista(request):
    filtros={k:request.GET.get(k,"").strip() for k in ("q","estado","categoria","nivel_riesgo","moneda_habitual","condicion_pago","documentacion_completa","es_proveedor_critico","es_preferido")}
    pagina=Paginator(proveedores_empresa(empresa=_empresa(request),filtros=filtros),25).get_page(request.GET.get("page"))
    return render(request,"compras/lista.html",{"proveedores":pagina,"filtros":filtros,"estados":Proveedor.Estado.choices,"riesgos":Proveedor.Riesgo.choices})


@login_required
@modulo_requerido("modulo_compras")
def editar(request,pk=None):
    permiso="compras.change_proveedor" if pk else "compras.add_proveedor"
    if not request.user.has_perm(permiso): raise PermissionDenied
    empresa=_empresa(request); obj=get_object_or_404(Proveedor,pk=pk,empresa=empresa) if pk else None
    form=ProveedorForm(request.POST or None,instance=obj,empresa=empresa)
    if request.method=="POST" and form.is_valid():
        try:
            saved=(__import__("compras.application.proveedores",fromlist=["actualizar_proveedor"]).actualizar_proveedor(
                context=_context(request),proveedor_id=obj.pk,datos=form.cleaned_data) if obj else crear_proveedor(context=_context(request),datos=form.cleaned_data))
            messages.success(request,"Proveedor guardado correctamente.")
            return redirect("compras:detalle",pk=saved.pk)
        except ValidationError as exc: form.add_error(None,exc)
    return render(request,"compras/form.html",{"form":form,"objeto":obj})


@login_required
@modulo_requerido("modulo_compras","compras.view_proveedor")
def detalle(request,pk):
    proveedor=get_object_or_404(Proveedor.objects.select_related("categoria"),pk=pk,empresa=_empresa(request))
    return render(request,"compras/detalle.html",{
        "proveedor":proveedor,"documentos":obtener_documentos(proveedor,_empresa(request)),
        "contacto_form":ContactoProveedorForm(empresa=_empresa(request)),
        "direccion_form":DireccionProveedorForm(empresa=_empresa(request)),
        "producto_form":ProductoProveedorForm(empresa=_empresa(request)),
        "cuenta_form":CuentaBancariaProveedorForm(empresa=_empresa(request)),
        "legado_form":ProveedorLegadoMapForm(empresa=_empresa(request)),
        "transicion_form":TransicionForm(),
    })


RELACIONES={
    "contacto":(ContactoProveedorForm,crear_contacto_proveedor,"add_contactoproveedor"),
    "direccion":(DireccionProveedorForm,crear_direccion_proveedor,"add_direccionproveedor"),
    "producto":(ProductoProveedorForm,vincular_producto_proveedor,"add_productoproveedor"),
    "cuenta":(CuentaBancariaProveedorForm,registrar_cuenta_bancaria,"add_cuentabancariaproveedor"),
    "legado":(ProveedorLegadoMapForm,vincular_proveedor_legado,"gestionar_correspondencia_proveedor"),
}


@login_required
@modulo_requerido("modulo_compras")
def agregar_relacion(request,pk,tipo):
    proveedor=get_object_or_404(Proveedor,pk=pk,empresa=_empresa(request))
    try: form_cls,service,permiso=RELACIONES[tipo]
    except KeyError: raise PermissionDenied
    if request.method!="POST" or not request.user.has_perm(f"compras.{permiso}"): raise PermissionDenied
    form=form_cls(request.POST,empresa=_empresa(request))
    if form.is_valid():
        datos=form.cleaned_data; datos["proveedor_nuevo" if tipo=="legado" else "proveedor"]=proveedor
        service(context=_context(request),datos=datos)
        messages.success(request,"Registro agregado.")
    else:
        messages.error(request,"No fue posible agregar el registro: "+str(form.errors))
    return redirect("compras:detalle",pk=pk)


ACCIONES={"activar":activar_proveedor,"suspender":suspender_proveedor,"bloquear":bloquear_proveedor,"reactivar":reactivar_proveedor,"inactivar":inactivar_proveedor}
@login_required
@modulo_requerido("modulo_compras")
def estado(request,pk,accion):
    if request.method!="POST" or accion not in ACCIONES: raise PermissionDenied
    form=TransicionForm(request.POST)
    if form.is_valid():
        try: ACCIONES[accion](context=_context(request),proveedor_id=pk,motivo=form.cleaned_data["motivo"]); messages.success(request,"Estado actualizado.")
        except ValidationError as exc: messages.error(request,str(exc))
    return redirect("compras:detalle",pk=pk)


@login_required
@modulo_requerido("modulo_compras")
def ver_cuenta(request,pk):
    if not request.user.has_perm("compras.view_datos_bancarios_completos"): raise PermissionDenied
    cuenta=get_object_or_404(CuentaBancariaProveedor,pk=pk,empresa=_empresa(request))
    registrar_evento(empresa=_empresa(request),usuario=request.user,request=request,objeto=cuenta,modulo="compras",
        accion=EventoAuditoria.Accion.OTRO,descripcion="Consulta autorizada de cuenta bancaria completa.",
        datos_nuevos={"cuenta_id":cuenta.pk})
    response=JsonResponse({"numero_cuenta":cuenta.numero_cuenta})
    response["Cache-Control"]="no-store, private"
    response["Pragma"]="no-cache"
    return response


@login_required
@modulo_requerido("modulo_compras")
def revisar_cuenta(request,pk,accion):
    if request.method!="POST": raise PermissionDenied
    cuenta=get_object_or_404(CuentaBancariaProveedor,pk=pk,empresa=_empresa(request))
    try:
        if accion=="verificar": verificar_cuenta_bancaria(context=_context(request),cuenta_id=pk)
        elif accion=="rechazar": rechazar_cuenta_bancaria(context=_context(request),cuenta_id=pk,motivo=request.POST.get("motivo",""))
        else: raise PermissionDenied
        messages.success(request,"Revisión bancaria registrada.")
    except ValidationError as exc: messages.error(request,str(exc))
    return redirect("compras:detalle",pk=cuenta.proveedor_id)


@login_required
@modulo_requerido("modulo_compras","compras.exportar_proveedores")
def exportar(request):
    response=HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"]='attachment; filename="proveedores.csv"'
    writer=csv.writer(response); writer.writerow(["Código","Razón social","RNC","Estado","Riesgo","Categoría","Documentación"])
    qs=proveedores_empresa(empresa=_empresa(request),filtros=request.GET)
    for p in qs: writer.writerow([p.codigo,p.razon_social,p.rnc_identificacion,p.estado,p.nivel_riesgo,p.categoria or "",p.documentacion_completa])
    registrar_evento(empresa=_empresa(request),usuario=request.user,request=request,modulo="compras",accion=EventoAuditoria.Accion.OTRO,descripcion="Exportación segura de proveedores.",datos_nuevos={"filas":qs.count()})
    return response
