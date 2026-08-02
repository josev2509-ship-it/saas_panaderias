import csv
from io import BytesIO
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from conduces.services import obtener_empresa_usuario
from core.application.operation_context import OperationContext
from comercial.models import *
from comercial.application.o2c_full import *

def _e(r):
    e=obtener_empresa_usuario(r)
    if not e:raise PermissionDenied
    return e
def _c(r):return OperationContext(empresa=_e(r),usuario=r.user,request=r,clave_idempotente=r.headers.get("Idempotency-Key",""))
@login_required
def dashboard(request):
    e=_e(request);modelos=[ReservaComercial,PreparacionPedido,TareaPicking,PackingPedido,DespachoComercial,ConduceComercial,EntregaComercial,FacturaVenta,CuentaPorCobrar,ReciboCobro,CesionFactoring];kpis={m.__name__:m.objects.filter(empresa=e).count() for m in modelos if hasattr(m,"empresa")};return render(request,"comercial/o2c_full/dashboard.html",{"empresa":e,"kpis":kpis,"facturas":FacturaVenta.objects.filter(empresa=e).select_related("cliente")[:8],"cxc":CuentaPorCobrar.objects.filter(empresa=e).select_related("cliente","factura")[:8]})
@login_required
def listado(request,tipo):
    e=_e(request);mapa={"reservas":ReservaComercial,"preparaciones":PreparacionPedido,"picking":TareaPicking,"packing":PackingPedido,"despachos":DespachoComercial,"conduces":ConduceComercial,"entregas":EntregaComercial,"facturas":FacturaVenta,"cxc":CuentaPorCobrar,"cobros":ReciboCobro,"factoring":CesionFactoring};m=mapa.get(tipo)
    if not m:raise PermissionDenied
    return render(request,"comercial/o2c_full/lista.html",{"empresa":e,"titulo":tipo.title(),"tipo":tipo,"items":m.objects.filter(empresa=e).order_by("-pk")[:100]})
@require_POST
@login_required
def pedido_reservar(request,pk):
    c=_c(request);r=crear_reserva_desde_pedido(context=c,pedido_id=pk);reservar_inventario(context=c,reserva_id=r.pk);return redirect("comercial:o2c_full_lista",tipo="reservas")
@require_POST
@login_required
def reserva_preparar(request,pk):
    o=crear_preparacion(context=_c(request),reserva_id=pk);return redirect("comercial:o2c_full_lista",tipo="preparaciones")
@require_POST
@login_required
def preparacion_validar(request,pk):
    c=_c(request);iniciar_preparacion(context=c,pk=pk);p=validar_preparacion(context=c,pk=pk);generar_picking(context=c,preparacion_id=p.pk);return redirect("comercial:o2c_full_lista",tipo="picking")
@require_POST
@login_required
def picking_completar(request,pk):
    c=_c(request);p=completar_picking(context=c,pk=pk);crear_packing(context=c,picking_id=p.pk);return redirect("comercial:o2c_full_lista",tipo="packing")
@require_POST
@login_required
def packing_despachar(request,pk):
    c=_c(request);p=sellar_packing(context=c,pk=pk,peso=Decimal(request.POST.get("peso",0)));crear_despacho(context=c,packing_ids=[p.pk]);return redirect("comercial:o2c_full_lista",tipo="despachos")
@require_POST
@login_required
def despacho_conduce(request,pk):
    c=_c(request);autorizar_despacho(context=c,pk=pk);emitir_conduce(context=c,despacho_id=pk);return redirect("comercial:o2c_full_lista",tipo="conduces")
@require_POST
@login_required
def conduce_entregar(request,pk):
    confirmar_entrega(context=_c(request),conduce_id=pk,receptor=request.POST.get("receptor","Receptor"));return redirect("comercial:o2c_full_lista",tipo="entregas")
@require_POST
@login_required
def entrega_facturar(request,pk):
    c=_c(request);f=crear_factura_desde_entrega(context=c,entrega_id=pk,vence_el=timezone.localdate()+timezone.timedelta(days=30),ncf=request.POST.get("ncf",""));emitir_factura(context=c,pk=f.pk);return redirect("comercial:o2c_full_lista",tipo="facturas")
@require_POST
@login_required
def cobrar(request,pk):
    c=_c(request);cuenta=get_object_or_404(CuentaPorCobrar,pk=pk,empresa=c.empresa);m=Decimal(request.POST["monto"]);r=registrar_cobro(context=c,cliente=cuenta.cliente,moneda=cuenta.moneda,monto=m,metodo=request.POST.get("metodo","TRANSFERENCIA"));aplicar_cobro(context=c,recibo_id=r.pk,cuenta_id=cuenta.pk,monto=m);return redirect("comercial:o2c_full_lista",tipo="cxc")
@login_required
def exportar(request,tipo,formato):
    e=_e(request);mapa={"facturas":FacturaVenta,"cxc":CuentaPorCobrar,"cobros":ReciboCobro,"entregas":EntregaComercial,"despachos":DespachoComercial};rows=[[x.pk,getattr(x,"numero",x.pk),getattr(x,"estado","")] for x in mapa[tipo].objects.filter(empresa=e)]
    if formato=="csv":
        r=HttpResponse(content_type="text/csv");w=csv.writer(r);w.writerow(["ID","Número","Estado"]);[w.writerow(row) for row in rows];return r
    if formato=="xlsx":
        from openpyxl import Workbook
        wb=Workbook();ws=wb.active;ws.append(["ID","Número","Estado"]);[ws.append(row) for row in rows];b=BytesIO();wb.save(b);return HttpResponse(b.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    return render(request,"comercial/o2c_full/impresion.html",{"empresa":e,"titulo":tipo,"rows":rows})
