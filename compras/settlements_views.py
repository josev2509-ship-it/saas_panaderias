from io import BytesIO
from uuid import uuid4

from django import forms
from django.contrib.auth.decorators import login_required,permission_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST

from catalogos.models import MonedaEmpresa
from conduces.decorators import modulo_requerido
from conduces.services import obtener_empresa_usuario
from contabilidad.models import (AnticipoProveedor,AplicacionAnticipoProveedor,CertificadoRetencionProveedor,
 CompensacionP2P,CuentaPorPagarEnterprise,RetencionProveedor)
from core.application.operation_context import OperationContext
from compras.models import Proveedor
from comercial.models import CuentaPorCobrar
from compras.application.financial import aplicar_anticipo,crear_anticipo,revertir_aplicacion_anticipo
from compras.application.settlements import (anular_compensacion,aplicar_compensacion_aprobada,
 aplicar_retencion,aprobar_compensacion,emitir_certificado,proponer_compensacion,
 revertir_compensacion,revertir_retencion)

def _empresa(r):return obtener_empresa_usuario(r)
def _ctx(r):return OperationContext(empresa=_empresa(r),usuario=r.user,request=r,clave_idempotente=r.headers.get("Idempotency-Key") or f"web:{r.path}:{uuid4()}")
class TenantForm(forms.Form):
 def __init__(self,*a,empresa=None,**k):self.empresa=empresa;super().__init__(*a,**k)
class CompensacionForm(TenantForm):
 cuenta_pagar=forms.ModelChoiceField(queryset=CuentaPorPagarEnterprise.objects.none());cuenta_cobrar=forms.ModelChoiceField(queryset=CuentaPorCobrar.objects.none(),required=False);anticipo=forms.ModelChoiceField(queryset=AnticipoProveedor.objects.none(),required=False);monto=forms.DecimalField(min_value=.01);tasa_cambio=forms.DecimalField(min_value=.000001,initial=1)
 def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["cuenta_pagar"].queryset=CuentaPorPagarEnterprise.objects.filter(empresa=empresa,saldo__gt=0);self.fields["cuenta_cobrar"].queryset=CuentaPorCobrar.objects.filter(empresa=empresa,saldo__gt=0);self.fields["anticipo"].queryset=AnticipoProveedor.objects.filter(empresa=empresa,saldo__gt=0)
 def clean(self):
  d=super().clean()
  if sum(bool(d.get(x)) for x in ("cuenta_cobrar","anticipo"))!=1:raise forms.ValidationError("Seleccione exactamente una fuente.")
  return d
class AnticipoForm(TenantForm):
 proveedor=forms.ModelChoiceField(queryset=Proveedor.objects.none());moneda=forms.ModelChoiceField(queryset=MonedaEmpresa.objects.none());monto=forms.DecimalField(min_value=.01);referencia=forms.CharField(max_length=100)
 def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["proveedor"].queryset=Proveedor.objects.filter(empresa=empresa,estado="ACTIVO");self.fields["moneda"].queryset=MonedaEmpresa.objects.filter(empresa=empresa,activa=True)
class RetencionForm(TenantForm):
 cuenta=forms.ModelChoiceField(queryset=CuentaPorPagarEnterprise.objects.none());tipo=forms.ChoiceField(choices=RetencionProveedor.TIPOS);codigo=forms.CharField(max_length=30);base=forms.DecimalField(min_value=.01);tasa=forms.DecimalField(min_value=.000001)
 def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["cuenta"].queryset=CuentaPorPagarEnterprise.objects.filter(empresa=empresa,saldo__gt=0)

@login_required
@modulo_requerido("modulo_compras")
def lista(request,recurso):
 empresa=_empresa(request);mapping={"compensaciones":CompensacionP2P.objects.filter(empresa=empresa),"anticipos":AnticipoProveedor.objects.filter(empresa=empresa),"retenciones":RetencionProveedor.objects.filter(empresa=empresa)}
 if recurso not in mapping:return HttpResponse(status=404)
 return render(request,"compras/p2p/settlements.html",{"recurso":recurso,"objetos":mapping[recurso].order_by("-pk")[:100]})

@login_required
@permission_required("contabilidad.aplicar_compensacion_p2p",raise_exception=True)
@require_POST
def crear_compensacion(request):
 form=CompensacionForm(request.POST,empresa=_empresa(request))
 if not form.is_valid():return render(request,"compras/p2p/settlement_form.html",{"form":form,"titulo":"Compensación"},status=400)
 d=form.cleaned_data;proponer_compensacion(context=_ctx(request),cuenta_pagar_id=d["cuenta_pagar"].pk,cuenta_cobrar_id=getattr(d.get("cuenta_cobrar"),"pk",None),anticipo_id=getattr(d.get("anticipo"),"pk",None),monto=d["monto"],tasa_cambio=d["tasa_cambio"],clave_idempotencia=request.headers.get("Idempotency-Key") or f"comp:{uuid4()}");return redirect("compras:p2p_settlements", "compensaciones")

@login_required
@permission_required("contabilidad.aplicar_compensacion_p2p",raise_exception=True)
@require_POST
def accion_compensacion(request,pk,accion):
 ctx=_ctx(request)
 if accion=="aprobar":aprobar_compensacion(context=ctx,compensacion_id=pk)
 elif accion=="aplicar":aplicar_compensacion_aprobada(context=ctx,compensacion_id=pk)
 elif accion=="revertir":revertir_compensacion(context=ctx,compensacion_id=pk,motivo=request.POST.get("motivo",""))
 elif accion=="anular":anular_compensacion(context=ctx,compensacion_id=pk,motivo=request.POST.get("motivo",""))
 else:return HttpResponse(status=404)
 return redirect("compras:p2p_settlements","compensaciones")

@login_required
@permission_required("contabilidad.add_anticipoproveedor",raise_exception=True)
@require_POST
def crear_anticipo_view(request):
 form=AnticipoForm(request.POST,empresa=_empresa(request))
 if not form.is_valid():return render(request,"compras/p2p/settlement_form.html",{"form":form,"titulo":"Anticipo"},status=400)
 crear_anticipo(context=_ctx(request),**form.cleaned_data);return redirect("compras:p2p_settlements","anticipos")

@login_required
@permission_required("contabilidad.change_anticipoproveedor",raise_exception=True)
@require_POST
def accion_anticipo(request,pk,accion):
 if accion=="aplicar":aplicar_anticipo(context=_ctx(request),anticipo_id=pk,cuenta_id=request.POST["cuenta_id"],monto=request.POST["monto"],clave_idempotencia=request.headers.get("Idempotency-Key"))
 elif accion=="revertir":revertir_aplicacion_anticipo(context=_ctx(request),aplicacion_id=request.POST["aplicacion_id"],motivo=request.POST.get("motivo",""))
 else:return HttpResponse(status=404)
 return redirect("compras:p2p_settlements","anticipos")

@login_required
@permission_required("contabilidad.aplicar_retencion_proveedor",raise_exception=True)
@require_POST
def crear_retencion(request):
 form=RetencionForm(request.POST,empresa=_empresa(request))
 if not form.is_valid():return render(request,"compras/p2p/settlement_form.html",{"form":form,"titulo":"Retención"},status=400)
 d=form.cleaned_data;aplicar_retencion(context=_ctx(request),cuenta_id=d["cuenta"].pk,tipo=d["tipo"],codigo=d["codigo"],base=d["base"],tasa=d["tasa"],clave_idempotencia=request.headers.get("Idempotency-Key") or f"ret:{uuid4()}");return redirect("compras:p2p_settlements","retenciones")

@login_required
@permission_required("contabilidad.aplicar_retencion_proveedor",raise_exception=True)
@require_POST
def accion_retencion(request,pk,accion):
 emitir_certificado(context=_ctx(request),retencion_id=pk) if accion=="certificado" else revertir_retencion(context=_ctx(request),retencion_id=pk,motivo=request.POST.get("motivo",""));return redirect("compras:p2p_settlements","retenciones")

@login_required
@permission_required("contabilidad.descargar_certificado_retencion",raise_exception=True)
def certificado_pdf(request,pk):
 cert=get_object_or_404(CertificadoRetencionProveedor.objects.select_related("retencion__proveedor"),pk=pk,empresa=_empresa(request));buffer=BytesIO();from reportlab.pdfgen import canvas;c=canvas.Canvas(buffer);c.drawString(72,780,f"Certificado {cert.numero}");c.drawString(72,755,f"Retención: {cert.retencion.tipo} {cert.retencion.monto}");c.drawString(72,730,f"Hash: {cert.contenido_hash}");c.save();return HttpResponse(buffer.getvalue(),content_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{cert.numero}.pdf"'})
