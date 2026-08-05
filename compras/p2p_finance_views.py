"""Pantallas operativas tenant-safe para el cierre financiero P2P."""
from io import BytesIO
from uuid import uuid4

from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalogos.models import MonedaEmpresa
from conduces.decorators import modulo_requerido
from conduces.services import obtener_empresa_usuario
from contabilidad.models import (AnticipoProveedor, CertificadoRetencionProveedor,CompensacionP2P,
 CuentaPorPagarEnterprise, FacturaProveedor, NotaCreditoProveedor, NotaDebitoProveedor,
 RetencionProveedor)
from core.application.operation_context import OperationContext
from compras.application.financial import (anular_anticipo, anular_nota, aplicar_anticipo,
 aplicar_nota, crear_anticipo_borrador, crear_nota_borrador, decidir_anticipo,
 decidir_nota, enviar_nota_aprobacion, revertir_aplicacion_anticipo,
 revertir_aplicacion_nota)
from compras.application.settlements import (anular_retencion, aplicar_retencion_aprobada,
 crear_retencion_borrador, decidir_retencion, emitir_certificado, revertir_retencion)
from compras.models import Proveedor
from documentos.models import Documento
from tesoreria.models import (ConciliacionBancaria, CuentaBancariaEmpresa,
 ImportacionExtractoBancario, LineaExtractoBancario,MovimientoTesoreria)
from tesoreria.services import (desconciliar_linea, importar_extracto, reconciliar_linea,
 seleccionar_coincidencia_manual)


def _empresa(request): return obtener_empresa_usuario(request)
def _ctx(request): return OperationContext(empresa=_empresa(request), usuario=request.user, request=request, clave_idempotente=request.headers.get("Idempotency-Key") or f"web:{request.path}:{uuid4()}")


class TenantForm(forms.Form):
    def __init__(self, *args, empresa=None, **kwargs): self.empresa=empresa; super().__init__(*args, **kwargs)


class NotaForm(TenantForm):
    tipo=forms.ChoiceField(choices=(("CREDITO","Crédito"),("DEBITO","Débito")))
    factura=forms.ModelChoiceField(queryset=FacturaProveedor.objects.none())
    numero=forms.CharField(max_length=30); monto=forms.DecimalField(min_value=.01)
    motivo=forms.CharField(widget=forms.Textarea)
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,empresa=empresa,**kwargs);self.fields["factura"].queryset=FacturaProveedor.objects.filter(empresa=empresa,estado__in=["VALIDADA","PARCIALMENTE_PAGADA"])


class AnticipoForm(TenantForm):
    proveedor=forms.ModelChoiceField(queryset=Proveedor.objects.none())
    moneda=forms.ModelChoiceField(queryset=MonedaEmpresa.objects.none())
    monto=forms.DecimalField(min_value=.01); referencia=forms.CharField(max_length=100)
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,empresa=empresa,**kwargs);self.fields["proveedor"].queryset=Proveedor.objects.filter(empresa=empresa,estado="ACTIVO");self.fields["moneda"].queryset=MonedaEmpresa.objects.filter(empresa=empresa,activa=True)


class RetencionForm(TenantForm):
    cuenta=forms.ModelChoiceField(queryset=CuentaPorPagarEnterprise.objects.none())
    tipo=forms.ChoiceField(choices=RetencionProveedor.TIPOS);codigo=forms.CharField(max_length=30)
    base=forms.DecimalField(min_value=.01);tasa=forms.DecimalField(min_value=.000001)
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,empresa=empresa,**kwargs);self.fields["cuenta"].queryset=CuentaPorPagarEnterprise.objects.filter(empresa=empresa,saldo__gt=0)


class ExtractoForm(TenantForm):
    cuenta=forms.ModelChoiceField(queryset=CuentaBancariaEmpresa.objects.none());archivo=forms.FileField()
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,empresa=empresa,**kwargs);self.fields["cuenta"].queryset=CuentaBancariaEmpresa.objects.filter(empresa=empresa,activa=True)


@login_required
@modulo_requerido("modulo_compras")
def lista(request,recurso):
    empresa=_empresa(request);mapping={"anticipos":AnticipoProveedor.objects.filter(empresa=empresa),"retenciones":RetencionProveedor.objects.filter(empresa=empresa),"certificados":CertificadoRetencionProveedor.objects.filter(empresa=empresa),"compensaciones":CompensacionP2P.objects.filter(empresa=empresa),"notas-credito":NotaCreditoProveedor.objects.filter(empresa=empresa),"notas-debito":NotaDebitoProveedor.objects.filter(empresa=empresa),"extractos":ImportacionExtractoBancario.objects.filter(empresa=empresa),"conciliaciones":ConciliacionBancaria.objects.filter(empresa=empresa)}
    if recurso not in mapping:return HttpResponse(status=404)
    qs=mapping[recurso];estado=request.GET.get("estado","").strip()
    if estado:qs=qs.filter(estado=estado)
    return render(request,"compras/p2p/finance_list.html",{"recurso":recurso,"objetos":qs.order_by("-pk")[:100],"estado":estado})


@login_required
@modulo_requerido("modulo_compras")
def detalle(request,recurso,pk):
    empresa=_empresa(request);mapping={"anticipos":AnticipoProveedor,"retenciones":RetencionProveedor,"certificados":CertificadoRetencionProveedor,"compensaciones":CompensacionP2P,"notas-credito":NotaCreditoProveedor,"notas-debito":NotaDebitoProveedor,"extractos":ImportacionExtractoBancario,"conciliaciones":ConciliacionBancaria}
    if recurso not in mapping:return HttpResponse(status=404)
    obj=get_object_or_404(mapping[recurso],pk=pk,empresa=empresa);ctype=ContentType.objects.get_for_model(obj);documentos=Documento.objects.filter(empresa=empresa,content_type=ctype,object_id=obj.pk,estado="ACTIVO");historial=getattr(obj,"historial",None);cuentas=CuentaPorPagarEnterprise.objects.filter(empresa=empresa,proveedor_id=getattr(obj,"proveedor_id",getattr(getattr(obj,"factura",None),"proveedor_id",None)),saldo__gt=0);aplicaciones=getattr(obj,"aplicaciones",None);lineas=getattr(obj,"lineas",None)
    return render(request,"compras/p2p/finance_detail.html",{"recurso":recurso,"obj":obj,"documentos":documentos,"historial":historial.all() if historial is not None else [],"cuentas":cuentas,"aplicaciones":aplicaciones.filter(revertida=False) if aplicaciones is not None else [],"lineas":lineas.all() if lineas is not None else [],"conciliaciones":ConciliacionBancaria.objects.filter(empresa=empresa,estado="BORRADOR"),"movimientos":MovimientoTesoreria.objects.filter(empresa=empresa,conciliado=False)[:100]})


def _form_response(request,form_class,title):
    form=form_class(request.POST or None,request.FILES or None,empresa=_empresa(request));return form,render(request,"compras/p2p/settlement_form.html",{"form":form,"titulo":title},status=400 if request.method=="POST" else 200)


@login_required
@permission_required("contabilidad.add_notacreditoproveedor",raise_exception=True)
def nota_crear(request):
    form,response=_form_response(request,NotaForm,"Nota de proveedor")
    if request.method!="POST":return response
    if not form.is_valid():return response
    d=form.cleaned_data;crear_nota_borrador(context=_ctx(request),tipo=d["tipo"],factura_id=d["factura"].pk,numero=d["numero"],monto=d["monto"],motivo=d["motivo"]);return redirect("compras:p2p_finance_list","notas-credito" if d["tipo"]=="CREDITO" else "notas-debito")


@login_required
@permission_required("contabilidad.change_notacreditoproveedor",raise_exception=True)
@require_POST
def nota_accion(request,tipo,pk,accion):
    ctx=_ctx(request);tipo=tipo.upper()
    if accion=="enviar":enviar_nota_aprobacion(context=ctx,tipo=tipo,nota_id=pk)
    elif accion in {"aprobar","rechazar"}:decidir_nota(context=ctx,tipo=tipo,nota_id=pk,decision=accion.upper(),motivo=request.POST.get("motivo",""))
    elif accion=="aplicar":aplicar_nota(context=ctx,tipo=tipo,nota_id=pk,cuenta_id=request.POST["cuenta_id"],monto=request.POST["monto"],clave_idempotencia=request.headers.get("Idempotency-Key") or f"nota:{uuid4()}",tasa_cambio=request.POST.get("tasa_cambio") or None)
    elif accion=="revertir":revertir_aplicacion_nota(context=ctx,aplicacion_id=request.POST["aplicacion_id"],motivo=request.POST.get("motivo",""))
    elif accion=="anular":anular_nota(context=ctx,tipo=tipo,nota_id=pk,motivo=request.POST.get("motivo",""))
    else:return HttpResponse(status=404)
    return redirect("compras:p2p_finance_list","notas-credito" if tipo=="CREDITO" else "notas-debito")


@login_required
@permission_required("contabilidad.add_anticipoproveedor",raise_exception=True)
def anticipo_crear(request):
    form,response=_form_response(request,AnticipoForm,"Anticipo")
    if request.method!="POST":return response
    if not form.is_valid():return response
    crear_anticipo_borrador(context=_ctx(request),**form.cleaned_data);return redirect("compras:p2p_finance_list","anticipos")


@login_required
@permission_required("contabilidad.change_anticipoproveedor",raise_exception=True)
@require_POST
def anticipo_accion(request,pk,accion):
    ctx=_ctx(request)
    if accion=="aprobar":decidir_anticipo(context=ctx,anticipo_id=pk,decision="APROBAR")
    elif accion=="rechazar":decidir_anticipo(context=ctx,anticipo_id=pk,decision="RECHAZAR",motivo=request.POST.get("motivo",""))
    elif accion=="anular":anular_anticipo(context=ctx,anticipo_id=pk,motivo=request.POST.get("motivo",""))
    elif accion=="aplicar":aplicar_anticipo(context=ctx,anticipo_id=pk,cuenta_id=request.POST["cuenta_id"],monto=request.POST["monto"],clave_idempotencia=request.headers.get("Idempotency-Key"))
    elif accion=="revertir":revertir_aplicacion_anticipo(context=ctx,aplicacion_id=request.POST["aplicacion_id"],motivo=request.POST.get("motivo",""))
    else:return HttpResponse(status=404)
    return redirect("compras:p2p_finance_list","anticipos")


@login_required
@permission_required("contabilidad.add_retencionproveedor",raise_exception=True)
def retencion_crear(request):
    form,response=_form_response(request,RetencionForm,"Retención")
    if request.method!="POST":return response
    if not form.is_valid():return response
    d=form.cleaned_data;crear_retencion_borrador(context=_ctx(request),cuenta_id=d["cuenta"].pk,tipo=d["tipo"],codigo=d["codigo"],base=d["base"],tasa=d["tasa"],clave_idempotencia=request.headers.get("Idempotency-Key") or f"ret:{uuid4()}");return redirect("compras:p2p_finance_list","retenciones")


@login_required
@permission_required("contabilidad.change_retencionproveedor",raise_exception=True)
@require_POST
def retencion_accion(request,pk,accion):
    ctx=_ctx(request)
    if accion=="aprobar":decidir_retencion(context=ctx,retencion_id=pk,decision="APROBAR")
    elif accion=="rechazar":decidir_retencion(context=ctx,retencion_id=pk,decision="RECHAZAR",motivo=request.POST.get("motivo",""))
    elif accion=="aplicar":aplicar_retencion_aprobada(context=ctx,retencion_id=pk)
    elif accion=="certificado":emitir_certificado(context=ctx,retencion_id=pk)
    elif accion=="revertir":revertir_retencion(context=ctx,retencion_id=pk,motivo=request.POST.get("motivo",""))
    elif accion=="anular":anular_retencion(context=ctx,retencion_id=pk,motivo=request.POST.get("motivo",""))
    else:return HttpResponse(status=404)
    return redirect("compras:p2p_finance_list","retenciones")


@login_required
@permission_required("tesoreria.add_importacionextractobancario",raise_exception=True)
def extracto_importar(request):
    form,response=_form_response(request,ExtractoForm,"Importar extracto bancario")
    if request.method!="POST":return response
    if not form.is_valid():return response
    archivo=form.cleaned_data["archivo"]
    if archivo.size>5*1024*1024:return HttpResponse("Archivo demasiado grande",status=400)
    importar_extracto(context=_ctx(request),cuenta=form.cleaned_data["cuenta"],contenido=archivo.read(),nombre_archivo=archivo.name,confirmar=True);return redirect("compras:p2p_finance_list","extractos")


@login_required
@permission_required("tesoreria.change_lineaextractobancario",raise_exception=True)
@require_POST
def matching_accion(request,pk,accion):
    empresa=_empresa(request);ctx=_ctx(request);linea=get_object_or_404(LineaExtractoBancario,pk=pk,importacion__empresa=empresa)
    if accion=="manual":
        conc=get_object_or_404(ConciliacionBancaria,pk=request.POST["conciliacion_id"],empresa=empresa,cuenta=linea.importacion.cuenta);seleccionar_coincidencia_manual(context=ctx,conciliacion=conc,linea_id=pk,movimiento_id=request.POST["movimiento_id"],motivo=request.POST.get("motivo",""))
    elif accion=="desconciliar":desconciliar_linea(context=ctx,linea_id=pk,motivo=request.POST.get("motivo",""))
    elif accion=="reconciliar":
        conc=get_object_or_404(ConciliacionBancaria,pk=request.POST["conciliacion_id"],empresa=empresa,cuenta=linea.importacion.cuenta);reconciliar_linea(context=ctx,conciliacion=conc,linea_id=pk,movimiento_id=request.POST["movimiento_id"],motivo=request.POST.get("motivo",""))
    else:return HttpResponse(status=404)
    return redirect("compras:p2p_finance_list","extractos")


@login_required
@permission_required("contabilidad.view_notacreditoproveedor",raise_exception=True)
def pdf(request,recurso,pk):
    mapping={"anticipos":AnticipoProveedor,"notas-credito":NotaCreditoProveedor,"notas-debito":NotaDebitoProveedor,"retenciones":RetencionProveedor};obj=get_object_or_404(mapping.get(recurso,NotaCreditoProveedor),pk=pk,empresa=_empresa(request)) if recurso in mapping else None
    if obj is None:return HttpResponse(status=404)
    buffer=BytesIO();from reportlab.pdfgen import canvas;c=canvas.Canvas(buffer);c.drawString(72,780,f"{recurso.replace('-', ' ').title()} #{obj.pk}");c.drawString(72,755,f"Estado: {obj.estado}");c.drawString(72,730,f"Monto: {obj.monto}");c.save();return HttpResponse(buffer.getvalue(),content_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{recurso}-{obj.pk}.pdf"'})


@login_required
@permission_required("contabilidad.descargar_certificado_retencion",raise_exception=True)
def certificado(request,pk):
    cert=get_object_or_404(CertificadoRetencionProveedor.objects.select_related("retencion"),pk=pk,empresa=_empresa(request));return pdf(request,"retenciones",cert.retencion_id)
