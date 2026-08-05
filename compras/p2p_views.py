from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.db.models import Count,Q,Sum
from django.utils import timezone

from conduces.decorators import modulo_requerido
from conduces.services import obtener_empresa_usuario
from contabilidad.models import (AnticipoProveedor,CertificadoRetencionProveedor,CompensacionP2P,
 CuentaPorPagarEnterprise, FacturaProveedor, OrdenPago,RetencionProveedor)
from documentos.services import obtener_documentos

from .models import (AdjudicacionCompra, ComparativoCompra, DevolucionCompra,WizardSession,
                     OfertaProveedor, OrdenCompraEnterprise, Proveedor, RecepcionCompra)

RESOURCES={"ofertas":(OfertaProveedor,"Ofertas"),"comparativos":(ComparativoCompra,"Comparativos"),"adjudicaciones":(AdjudicacionCompra,"Adjudicaciones"),"ordenes":(OrdenCompraEnterprise,"Órdenes de compra"),"recepciones":(RecepcionCompra,"Recepciones"),"devoluciones":(DevolucionCompra,"Devoluciones"),"facturas":(FacturaProveedor,"Facturas de proveedor"),"cxp":(CuentaPorPagarEnterprise,"Cuentas por pagar"),"pagos":(OrdenPago,"Pagos"),"proveedores":(Proveedor,"Proveedores")}

RESOURCES.update({"compensaciones":(CompensacionP2P,"Compensaciones"),"anticipos":(AnticipoProveedor,"Anticipos"),"retenciones":(RetencionProveedor,"Retenciones"),"wizards":(WizardSession,"Wizards P2P")})

@login_required
@modulo_requerido("modulo_compras")
def dashboard(request):
    from .models import ExpedienteCompra
    empresa=obtener_empresa_usuario(request);today=timezone.localdate();month=today.replace(day=1)
    fin={"compensaciones":CompensacionP2P.objects.filter(empresa=empresa,estado__in=["PROPUESTA","APROBADA"]).count(),"anticipos":AnticipoProveedor.objects.filter(empresa=empresa,saldo__gt=0).aggregate(v=Sum("saldo"))["v"] or 0}
    fin.update(RetencionProveedor.objects.filter(empresa=empresa).aggregate(retenciones=Sum("monto",filter=Q(fecha__gte=month,estado="APLICADA")),certificados=Count("certificado",filter=Q(certificado__emitido_en__date__gte=month),distinct=True)))
    wiz=WizardSession.objects.filter(empresa=empresa).aggregate(activos=Count("pk",filter=Q(estado="ACTIVO",expira_en__gt=timezone.now())),abandonados=Count("pk",filter=Q(estado__in=["EXPIRADO","FALLIDO"])))
    kpis=[
        ("Compras del mes",OrdenCompraEnterprise.objects.filter(empresa=empresa,fecha__gte=month).aggregate(v=Sum("total"))["v"] or 0,"ordenes",""),
        ("Órdenes abiertas",OrdenCompraEnterprise.objects.filter(empresa=empresa).exclude(estado__in=["CERRADA","CANCELADA"]).count(),"ordenes",""),
        ("Recepciones pendientes",RecepcionCompra.objects.filter(empresa=empresa,estado__in=["BORRADOR","EN_PROCESO","PARCIAL","CON_DIFERENCIAS"]).count(),"recepciones","PARCIAL"),
        ("Facturas pendientes",FacturaProveedor.objects.filter(empresa=empresa).exclude(estado__in=["PAGADA","ANULADA"]).count(),"facturas","VALIDADA"),
        ("CxP",CuentaPorPagarEnterprise.objects.filter(empresa=empresa).aggregate(v=Sum("saldo"))["v"] or 0,"cxp",""),
        ("Aging vencido",CuentaPorPagarEnterprise.objects.filter(empresa=empresa,vence_el__lt=today,saldo__gt=0).count(),"cxp","VENCIDA"),
        ("Pagos programados",OrdenPago.objects.filter(empresa=empresa,estado="APROBADA").count(),"pagos","APROBADA"),
        ("Proveedores críticos",Proveedor.objects.filter(empresa=empresa,nivel_riesgo="CRITICO").count(),"proveedores","CRITICO"),
        ("Entregas tardías",OrdenCompraEnterprise.objects.filter(empresa=empresa,entrega_hasta__lt=today).exclude(estado__in=["RECIBIDA","FACTURADA","CERRADA","CANCELADA"]).count(),"ordenes","ACEPTADA"),
        ("Ahorro negociado",OfertaProveedor.objects.filter(empresa=empresa,estado="EVALUADA").aggregate(v=Sum("descuento"))["v"] or 0,"ofertas","EVALUADA"),
        ("Compensaciones pendientes",fin["compensaciones"] or 0,"compensaciones",""),
        ("Anticipos disponibles",fin["anticipos"] or 0,"anticipos",""),
        ("Retenciones del periodo",fin["retenciones"] or 0,"retenciones",""),
        ("Certificados emitidos",fin["certificados"] or 0,"retenciones",""),
        ("Wizards activos",wiz["activos"] or 0,"wizards",""),
        ("Wizards abandonados",wiz["abandonados"] or 0,"wizards",""),
    ]
    return render(request,"compras/p2p_dashboard.html",{"kpis":kpis,"p2p_menu":[(x,label) for x,(_,label) in RESOURCES.items()],"expedientes":ExpedienteCompra.objects.filter(empresa=empresa).select_related("responsable","centro_costo")[:25]})

@login_required
@modulo_requerido("modulo_compras")
def lista(request,recurso):
    if recurso not in RESOURCES:raise PermissionDenied
    model,titulo=RESOURCES[recurso];empresa=obtener_empresa_usuario(request);qs=model.objects.filter(empresa=empresa).order_by("-pk");estado=request.GET.get("estado","").strip()
    if estado and any(f.name=="estado" for f in model._meta.fields):qs=qs.filter(estado=estado)
    return render(request,"compras/p2p/recurso_lista.html",{"pagina":Paginator(qs,50).get_page(request.GET.get("page")),"titulo":titulo,"recurso":recurso,"estado":estado})

@login_required
@modulo_requerido("modulo_compras")
def detalle(request,recurso,pk):
    if recurso not in RESOURCES:raise PermissionDenied
    model,titulo=RESOURCES[recurso];empresa=obtener_empresa_usuario(request);objeto=get_object_or_404(model,pk=pk,empresa=empresa)
    return render(request,"compras/p2p/recurso_detalle.html",{"objeto":objeto,"titulo":titulo,"recurso":recurso,"documentos":obtener_documentos(objeto,empresa)})
