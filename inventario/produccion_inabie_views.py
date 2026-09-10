from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

from conduces.decorators import modulo_requerido
from conduces.services import obtener_empresa_usuario

from .models import OrdenProduccion, ProductoInventario, RecetaProduccion, SolicitudCambioProducto
from .produccion_inabie_services import (
    ajustar_cantidad, cerrar_orden_inabie, generar_orden_inabie,
    iniciar_orden_inabie, proyectar_cobertura, solicitar_cambio_producto,
    decidir_cambio_producto,
)


def _empresa(request):
    empresa = obtener_empresa_usuario(request)
    if not empresa:
        raise PermissionDenied("No existe una empresa operativa activa.")
    return empresa


def _error_text(exc):
    return "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)


@login_required
@modulo_requerido("modulo_inabie", permiso_alternativo="inventario.add_ordenproduccion")
def generar_orden(request):
    empresa = _empresa(request)
    if request.method == "POST":
        try:
            orden = generar_orden_inabie(
                empresa=empresa,
                fecha_produccion=date.fromisoformat(request.POST["fecha_produccion"]),
                fecha_entrega=date.fromisoformat(request.POST["fecha_entrega"]) if request.POST.get("fecha_entrega") else None,
                modalidad=request.POST.get("modalidad", "REGULAR"),
                usuario=request.user,
                request=request,
            )
            return redirect("inventario:orden_detalle", pk=orden.pk)
        except (ValidationError, ValueError, KeyError) as exc:
            messages.error(request, _error_text(exc))
    return render(request, "inventario/orden_inabie_generar.html", {"empresa": empresa, "hoy": timezone.localdate()})


@login_required
@modulo_requerido("modulo_inabie", permiso_alternativo="inventario.change_ordenproduccion")
def ajustar_orden(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    empresa = _empresa(request); orden = get_object_or_404(OrdenProduccion, pk=pk, empresa=empresa)
    try:
        ajustar_cantidad(orden=orden, empresa=empresa, usuario=request.user, cantidad=request.POST.get("cantidad_autorizada", "0"), motivo=request.POST.get("motivo", "AJUSTE_OPERATIVO"), justificacion=request.POST.get("justificacion", ""), request=request)
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, _error_text(exc))
    return redirect("inventario:orden_detalle", pk=pk)


@login_required
@modulo_requerido("modulo_inabie", permiso_alternativo="inventario.iniciar_ordenproduccion")
def iniciar(request, pk):
    if request.method != "POST": return HttpResponseNotAllowed(["POST"])
    empresa=_empresa(request); orden=get_object_or_404(OrdenProduccion, pk=pk, empresa=empresa)
    try: iniciar_orden_inabie(orden=orden, empresa=empresa, usuario=request.user, request=request)
    except (ValidationError, PermissionDenied) as exc: messages.error(request, _error_text(exc))
    return redirect("inventario:orden_detalle", pk=pk)


@login_required
@modulo_requerido("modulo_inabie", permiso_alternativo="inventario.cerrar_ordenproduccion")
def cerrar(request, pk):
    if request.method != "POST": return HttpResponseNotAllowed(["POST"])
    empresa=_empresa(request); orden=get_object_or_404(OrdenProduccion, pk=pk, empresa=empresa)
    consumos=[]
    for necesidad in orden.necesidades.all():
        consumos.append({"materia_prima_id": necesidad.materia_prima_id, "cantidad_real": request.POST.get(f"real_{necesidad.materia_prima_id}", "0"), "motivo": request.POST.get(f"motivo_{necesidad.materia_prima_id}", ""), "justificacion": request.POST.get(f"justificacion_{necesidad.materia_prima_id}", "")})
    try: cerrar_orden_inabie(orden=orden, empresa=empresa, usuario=request.user, cantidad_real=request.POST.get("cantidad_real", "0"), consumos=consumos, request=request)
    except (ValidationError, PermissionDenied) as exc: messages.error(request, _error_text(exc))
    return redirect("inventario:orden_detalle", pk=pk)


@login_required
@modulo_requerido("modulo_inabie", permiso_alternativo="inventario.view_ordenproduccion")
def proyeccion(request):
    empresa=_empresa(request)
    try: desde=date.fromisoformat(request.GET.get("desde", ""))
    except ValueError: desde=timezone.localdate()
    try: dias=max(1, min(60, int(request.GET.get("dias", "15"))))
    except ValueError: dias=15
    filas=proyectar_cobertura(empresa=empresa, desde=desde, dias_productivos=dias, modalidad=request.GET.get("modalidad", "REGULAR"))
    return render(request, "inventario/proyeccion_materia_prima.html", {"empresa":empresa, "filas":filas, "desde":desde, "dias":dias})


@login_required
@modulo_requerido("modulo_inabie", permiso_alternativo="inventario.view_ordenproduccion")
def orden_pdf(request, pk):
    empresa=_empresa(request); orden=get_object_or_404(OrdenProduccion.objects.prefetch_related("necesidades__materia_prima", "consumos_reales__materia_prima", "ajustes"), pk=pk, empresa=empresa)
    stream=BytesIO(); pdf=Canvas(stream, pagesize=letter); y=760
    titulo="REPORTE / CIERRE DE PRODUCCIÓN" if orden.estado == OrdenProduccion.Estado.CERRADA else "ORDEN DE PRODUCCIÓN"
    pdf.setFont("Helvetica-Bold", 15); pdf.drawString(40,y,f"SASTRE ERP - {titulo}"); y-=28; pdf.setFont("Helvetica",9)
    datos=[("Empresa",empresa.nombre),("Orden",orden.numero),("Producción",orden.fecha_programada),("Entrega",orden.fecha_entrega or "-"),("Producto planificado",getattr(orden.producto_planificado,"nombre","-")),("Producto autorizado",orden.producto_terminado.nombre),("Receta / versión",str(orden.receta)),("Matrícula",orden.raciones_matricula),("Sugerida",orden.cantidad_sugerida),("Autorizada",orden.cantidad_autorizada),("Real",orden.cantidad_producida)]
    for label,value in datos: pdf.drawString(40,y,f"{label}: {value}"); y-=15
    y-=8; pdf.setFont("Helvetica-Bold",10); pdf.drawString(40,y,"Materia prima - teórico / real / diferencia"); y-=18; pdf.setFont("Helvetica",8)
    reales={x.materia_prima_id:x for x in orden.consumos_reales.all()}
    for n in orden.necesidades.all():
        real=reales.get(n.materia_prima_id); pdf.drawString(40,y,f"{n.materia_prima.nombre}: {n.cantidad_con_merma} / {real.cantidad_real if real else '-'} / {real.diferencia if real else '-'} {n.unidad_medida}"); y-=14
    pdf.drawString(40,y-10,f"Preparado por: {orden.creado_por or '-'}  Autorizado por: {orden.autorizada_por or '-'}  Cerrado por: {orden.cerrada_por or '-'}")
    pdf.save(); return HttpResponse(stream.getvalue(), content_type="application/pdf", headers={"Content-Disposition":f'attachment; filename="{orden.numero}.pdf"'})


@login_required
@modulo_requerido("modulo_inabie", permiso_alternativo="inventario.cambiar_producto_ordenproduccion")
def cambio_producto(request, pk):
    empresa=_empresa(request);orden=get_object_or_404(OrdenProduccion,pk=pk,empresa=empresa)
    productos=ProductoInventario.objects.filter(empresa=empresa,activo=True,tipo="producto_terminado")
    recetas=RecetaProduccion.objects.filter(empresa=empresa,activa=True)
    if request.method=="POST":
        try:
            producto=get_object_or_404(productos,pk=request.POST.get("producto"));receta=get_object_or_404(recetas,pk=request.POST.get("receta"),producto_terminado=producto)
            solicitar_cambio_producto(orden=orden,empresa=empresa,usuario=request.user,producto=producto,receta=receta,motivo=request.POST.get("motivo","AJUSTE_OPERATIVO"),justificacion=request.POST.get("justificacion",""),request=request)
            return redirect("inventario:orden_cambio_producto",pk=pk)
        except ValidationError as exc: messages.error(request,_error_text(exc))
    return render(request,"inventario/cambio_producto_orden.html",{"empresa":empresa,"orden":orden,"productos":productos,"recetas":recetas,"solicitudes":orden.solicitudes_cambio_producto.select_related("producto_solicitado","solicitado_por","decidido_por")})


@login_required
@modulo_requerido("modulo_inabie", permiso_alternativo="inventario.autorizar_cambio_producto")
def decidir_cambio(request, pk, solicitud_pk):
    if request.method!="POST":return HttpResponseNotAllowed(["POST"])
    empresa=_empresa(request);orden=get_object_or_404(OrdenProduccion,pk=pk,empresa=empresa);solicitud=get_object_or_404(SolicitudCambioProducto,pk=solicitud_pk,orden=orden,empresa=empresa)
    try:decidir_cambio_producto(solicitud=solicitud,empresa=empresa,usuario=request.user,decision=request.POST.get("decision",""),comentario=request.POST.get("comentario",""),request=request)
    except (ValidationError,PermissionDenied) as exc:messages.error(request,_error_text(exc))
    return redirect("inventario:orden_cambio_producto",pk=pk)
