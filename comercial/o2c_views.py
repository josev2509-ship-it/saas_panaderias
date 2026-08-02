import csv
from io import BytesIO
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse,FileResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.application.o2c import *
from comercial.forms import ProductoComercialForm,ListaPrecioForm,DetalleListaPrecioForm,CotizacionVentaForm,LineaCotizacionForm,SimuladorPrecioForm
from comercial.models import *
from comercial.selectors_o2c import *
from conduces.services import obtener_empresa_usuario
from core.application.operation_context import OperationContext
def _empresa(r):
    e=obtener_empresa_usuario(r)
    if not e:raise PermissionDenied
    return e
def _ctx(r,e):return OperationContext(empresa=e,usuario=r.user,request=r,clave_idempotente=r.headers.get("Idempotency-Key",""))
@login_required
def dashboard(request):
    e=_empresa(request);return render(request,"comercial/o2c/dashboard.html",{"empresa":e,"resumen":resumen_o2c(e),"cotizaciones":cotizaciones(e)[:6],"pedidos":pedidos_o2c(e)[:6]})
@login_required
def cliente_360(request,pk):
    e=_empresa(request);c=get_object_or_404(clientes_360(e),pk=pk);return render(request,"comercial/o2c/cliente360.html",{"empresa":e,"cliente":c,"contactos":c.contactos.all(),"direcciones":c.direcciones.all(),"cotizaciones":c.cotizaciones.all()[:10],"pedidos":c.pedidos.all()[:10],"actividades":c.actividades_crm.all()[:10],"auditoria":EventoAuditoria.objects.filter(empresa=e,object_id=c.pk)[:12]})
@require_POST
@login_required
def cliente_accion(request,pk,accion):
    c=_ctx(request,_empresa(request))
    if accion=="riesgo":calcular_riesgo_cliente(context=c,cliente_id=pk)
    elif accion=="limite":actualizar_limite_credito(context=c,cliente_id=pk,limite=request.POST.get("limite",0))
    elif accion in ("ACTIVO","SUSPENDIDO","BLOQUEADO_CREDITO","INACTIVO"):cambiar_estado_cliente(context=c,cliente_id=pk,estado=accion,motivo=request.POST.get("motivo",""))
    else:raise PermissionDenied
    return redirect("comercial:cliente_360",pk=pk)
@login_required
def productos_lista(request):return render(request,"comercial/o2c/lista.html",{"empresa":_empresa(request),"pagina":Paginator(productos_comerciales(_empresa(request)),25).get_page(request.GET.get("page")),"titulo":"Productos comerciales","tipo":"producto"})
@login_required
def producto_form(request,pk=None):
    e=_empresa(request);obj=get_object_or_404(ProductoComercial,empresa=e,pk=pk) if pk else None
    if not request.user.has_perm(f"comercial.{'change' if obj else 'add'}_productocomercial"):raise PermissionDenied
    f=ProductoComercialForm(request.POST or None,request.FILES or None,instance=obj,empresa=e)
    if request.method=="POST" and f.is_valid():
        if obj:item=f.save(commit=False);item.empresa=e;item.full_clean();item.save()
        else:item=crear_producto_comercial(context=_ctx(request,e),datos=f.cleaned_data)
        return redirect("comercial:producto_detalle",pk=item.pk)
    return render(request,"comercial/o2c/form.html",{"empresa":e,"form":f,"titulo":"Producto comercial"})
@login_required
def producto_detalle(request,pk):return render(request,"comercial/o2c/detalle.html",{"empresa":_empresa(request),"objeto":get_object_or_404(productos_comerciales(_empresa(request)),pk=pk),"tipo":"producto"})
@login_required
def listas(request):return render(request,"comercial/o2c/lista.html",{"empresa":_empresa(request),"pagina":Paginator(listas_precio(_empresa(request)),25).get_page(request.GET.get("page")),"titulo":"Listas de precios","tipo":"lista"})
@login_required
def lista_form(request,pk=None):
    e=_empresa(request);obj=get_object_or_404(ListaPrecio,empresa=e,pk=pk) if pk else None
    if not request.user.has_perm(f"comercial.{'change' if obj else 'add'}_listaprecio"):raise PermissionDenied
    f=ListaPrecioForm(request.POST or None,instance=obj,empresa=e)
    if request.method=="POST" and f.is_valid():
        if obj:item=f.save(commit=False);item.empresa=e;item.full_clean();item.save()
        else:item=crear_lista_precio(context=_ctx(request,e),datos=f.cleaned_data)
        return redirect("comercial:lista_detalle",pk=item.pk)
    return render(request,"comercial/o2c/form.html",{"empresa":e,"form":f,"titulo":"Lista de precios"})
@login_required
def lista_detalle(request,pk):
    e=_empresa(request);obj=get_object_or_404(listas_precio(e),pk=pk);f=DetalleListaPrecioForm(request.POST or None,empresa=e)
    if request.method=="POST" and f.is_valid():d=f.save(commit=False);d.lista=obj;d.full_clean();d.save();return redirect("comercial:lista_detalle",pk=pk)
    return render(request,"comercial/o2c/detalle.html",{"empresa":e,"objeto":obj,"tipo":"lista","detalles":obj.detalles.all(),"form":f})
@require_POST
@login_required
def lista_activar(request,pk):activar_lista_precio(context=_ctx(request,_empresa(request)),pk=pk);return redirect("comercial:lista_detalle",pk=pk)
@login_required
def simulador(request):
    e=_empresa(request);f=SimuladorPrecioForm(request.POST or None,empresa=e);resultado=None
    if request.method=="POST" and f.is_valid():resultado=resolver_precio_comercial(context=_ctx(request,e),**f.cleaned_data)
    return render(request,"comercial/o2c/simulador.html",{"empresa":e,"form":f,"resultado":resultado})
@login_required
def cotizaciones_lista(request):return render(request,"comercial/o2c/lista.html",{"empresa":_empresa(request),"pagina":Paginator(cotizaciones(_empresa(request)),25).get_page(request.GET.get("page")),"titulo":"Cotizaciones","tipo":"cotizacion"})
@login_required
def cotizacion_form(request,pk=None):
    e=_empresa(request);obj=get_object_or_404(CotizacionVenta,empresa=e,pk=pk) if pk else None
    if obj and obj.estado!="BORRADOR":raise ValidationError("Solo se editan borradores.")
    if not request.user.has_perm(f"comercial.{'change' if obj else 'add'}_cotizacionventa"):raise PermissionDenied
    f=CotizacionVentaForm(request.POST or None,instance=obj,empresa=e)
    if request.method=="POST" and f.is_valid():
        if obj:item=f.save(commit=False);item.empresa=e;item.actualizado_por=request.user;item.save()
        else:item=crear_cotizacion(context=_ctx(request,e),datos=f.cleaned_data)
        return redirect("comercial:cotizacion_detalle",pk=item.pk)
    return render(request,"comercial/o2c/form.html",{"empresa":e,"form":f,"titulo":"Cotización"})
@login_required
def cotizacion_detalle(request,pk):
    e=_empresa(request);c=get_object_or_404(cotizaciones(e),pk=pk);f=LineaCotizacionForm(request.POST or None,empresa=e)
    if request.method=="POST" and f.is_valid():r=resolver_precio_comercial(context=_ctx(request,e),cliente=c.cliente,producto=f.cleaned_data["producto"],cantidad=f.cleaned_data["cantidad"],fecha=c.fecha,moneda=c.moneda,canal=c.cliente.canal,zona=c.cliente.zona,documento_origen=c.numero);agregar_linea_cotizacion(context=_ctx(request,e),cotizacion_id=c.pk,producto=f.cleaned_data["producto"],cantidad=f.cleaned_data["cantidad"],resolucion=r,descuento=f.cleaned_data["descuento"]);return redirect("comercial:cotizacion_detalle",pk=pk)
    return render(request,"comercial/o2c/cotizacion.html",{"empresa":e,"objeto":c,"form":f,"historial":c.historial.all(),"versiones":c.versiones.all()})
@require_POST
@login_required
def cotizacion_accion(request,pk,accion):
    c=_ctx(request,_empresa(request))
    if accion=="versionar":versionar_cotizacion(context=c,pk=pk,motivo=request.POST.get("motivo","Nueva versión"))
    elif accion=="convertir":convertir_cotizacion_a_pedido(context=c,pk=pk,fecha_entrega=timezone.localdate()+timedelta(days=1),direccion=None)
    else:transicionar_cotizacion(context=c,pk=pk,accion=accion,comentario=request.POST.get("comentario",""))
    return redirect("comercial:cotizacion_detalle",pk=pk)
@login_required
def cotizacion_pdf(request,pk):
    e=_empresa(request);c=get_object_or_404(cotizaciones(e),pk=pk);from reportlab.pdfgen.canvas import Canvas;b=BytesIO();pdf=Canvas(b);pdf.setTitle(c.numero);y=800;pdf.drawString(40,y,f"{e.nombre} - Cotización {c.numero}");y-=25;pdf.drawString(40,y,f"Cliente: {c.cliente.nombre_comercial}");y-=30
    for x in c.detalles.all():pdf.drawString(40,y,f"{x.descripcion[:35]} | {x.cantidad} x {x.precio_unitario} = {x.total}");y-=18
    pdf.drawString(40,y-10,f"TOTAL: {c.total} {c.moneda.moneda.codigo}");pdf.save();r=HttpResponse(b.getvalue(),content_type="application/pdf");r["Content-Disposition"]=f'attachment; filename="{c.numero}.pdf"';return r
@login_required
def programacion(request,vista="semana"):
    e=_empresa(request);hoy=timezone.localdate();desde=hoy if vista=="dia" else hoy-timedelta(days=hoy.weekday()) if vista=="semana" else hoy.replace(day=1);hasta=desde if vista=="dia" else desde+timedelta(days=6) if vista=="semana" else (desde+timedelta(days=32)).replace(day=1)-timedelta(days=1);return render(request,"comercial/o2c/programacion.html",{"empresa":e,"items":programaciones(e).filter(fecha_programada__range=(desde,hasta)),"desde":desde,"hasta":hasta,"vista":vista})
@login_required
def reportes(request):return render(request,"comercial/o2c/reportes.html",{"empresa":_empresa(request),"resumen":resumen_o2c(_empresa(request))})
@login_required
def exportar(request,tipo,formato):
    e=_empresa(request);data={"clientes":clientes_360(e),"productos":productos_comerciales(e),"cotizaciones":cotizaciones(e),"pedidos":pedidos_o2c(e),"programacion":programaciones(e)}[tipo];rows=[[x.pk,getattr(x,"numero",getattr(x,"codigo","")),str(x)] for x in data];registrar_evento(empresa=e,usuario=request.user,request=request,modulo="comercial_o2c",accion=EventoAuditoria.Accion.OTRO,descripcion=f"Exportación O2C {tipo} {formato}.",datos_nuevos={"cantidad":len(rows)})
    if formato=="csv":r=HttpResponse(content_type="text/csv; charset=utf-8");w=csv.writer(r);w.writerow(["ID","Código","Descripción"]);[w.writerow([("'"+v) if isinstance(v,str) and v[:1] in "=+-@" else v for v in row]) for row in rows];return r
    if formato=="xlsx":
        from openpyxl import Workbook
        wb=Workbook();ws=wb.active;ws.title=tipo[:31];ws.append(["ID","Código","Descripción"])
        for row in rows:ws.append([("'"+v) if isinstance(v,str) and v[:1] in "=+-@" else v for v in row])
        b=BytesIO();wb.save(b);r=HttpResponse(b.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");r["Content-Disposition"]=f'attachment; filename="{tipo}.xlsx"';return r
    if formato=="pdf":
        from reportlab.pdfgen.canvas import Canvas
        b=BytesIO();p=Canvas(b);p.drawString(40,800,f"{e.nombre} - {tipo.title()}");y=775
        for row in rows[:40]:p.drawString(40,y," | ".join(map(str,row))[:100]);y-=18
        p.save();r=HttpResponse(b.getvalue(),content_type="application/pdf");r["Content-Disposition"]=f'attachment; filename="{tipo}.pdf"';return r
    return render(request,"comercial/o2c/impresion.html",{"empresa":e,"rows":rows,"titulo":tipo.title()})
