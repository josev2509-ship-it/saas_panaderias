from django import forms
from django.utils import timezone

from catalogos.models import Almacen
from contabilidad.models import CuentaPorPagarEnterprise, FacturaProveedor, OrdenPago
from tesoreria.models import Caja,CuentaBancariaEmpresa

from .models import (AdjudicacionCompra, ComparativoCompra, DetalleOrdenCompraEnterprise,
                     DetalleRFQ, OfertaProveedor, OrdenCompraEnterprise, ProcesoRFQ,
                     Proveedor, RecepcionCompra)

class TenantForm(forms.Form):
    def __init__(self,*args,empresa=None,**kwargs):self.empresa=empresa;super().__init__(*args,**kwargs)

class OfertaForm(TenantForm):
    rfq=forms.ModelChoiceField(queryset=ProcesoRFQ.objects.none());proveedor=forms.ModelChoiceField(queryset=Proveedor.objects.none());valida_hasta=forms.DateField(widget=forms.DateInput(attrs={"type":"date"}));tasa_cambio=forms.DecimalField(min_value=.000001,initial=1);plazo_entrega_dias=forms.IntegerField(min_value=0);garantia_dias=forms.IntegerField(min_value=0);observaciones=forms.CharField(required=False,widget=forms.Textarea)
    def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["rfq"].queryset=ProcesoRFQ.objects.filter(empresa=empresa,estado__in=["PUBLICADA","ABIERTA","EXTENDIDA"]);self.fields["proveedor"].queryset=Proveedor.objects.filter(empresa=empresa,estado="ACTIVO",bloqueado=False)
class LineaOfertaForm(TenantForm):
    linea_rfq=forms.ModelChoiceField(queryset=DetalleRFQ.objects.none());cantidad=forms.DecimalField(min_value=.0001);precio_unitario=forms.DecimalField(min_value=0);descuento=forms.DecimalField(min_value=0,initial=0);impuesto=forms.DecimalField(min_value=0,initial=0);marca=forms.CharField(required=False);modelo=forms.CharField(required=False);cumple=forms.BooleanField(required=False,initial=True)
    def __init__(self,*a,empresa=None,rfq=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["linea_rfq"].queryset=DetalleRFQ.objects.filter(empresa=empresa,rfq=rfq)
class ComparativoForm(TenantForm):
    rfq=forms.ModelChoiceField(queryset=ProcesoRFQ.objects.none());ponderaciones=forms.JSONField(required=False,help_text="Objeto JSON; debe sumar 100.")
    def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["rfq"].queryset=ProcesoRFQ.objects.filter(empresa=empresa)
class AdjudicacionForm(TenantForm):
    comparativo=forms.ModelChoiceField(queryset=ComparativoCompra.objects.none());tipo=forms.ChoiceField(choices=AdjudicacionCompra.TIPOS);justificacion=forms.CharField(widget=forms.Textarea);selecciones=forms.JSONField(help_text="Lista de oferta_id, linea_rfq_id y cantidad.")
    def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["comparativo"].queryset=ComparativoCompra.objects.filter(empresa=empresa)
class OrdenDesdeAdjudicacionForm(TenantForm):
    adjudicacion=forms.ModelChoiceField(queryset=AdjudicacionCompra.objects.none());proveedor=forms.ModelChoiceField(queryset=Proveedor.objects.none(),required=False)
    def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["adjudicacion"].queryset=AdjudicacionCompra.objects.filter(empresa=empresa,estado="APROBADA");self.fields["proveedor"].queryset=Proveedor.objects.filter(empresa=empresa)
class RecepcionForm(TenantForm):
    orden=forms.ModelChoiceField(queryset=OrdenCompraEnterprise.objects.none());almacen=forms.ModelChoiceField(queryset=Almacen.objects.none());documento_proveedor=forms.CharField(required=False);fecha=forms.DateTimeField(initial=timezone.now,widget=forms.DateTimeInput(attrs={"type":"datetime-local"}))
    def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["orden"].queryset=OrdenCompraEnterprise.objects.filter(empresa=empresa,estado__in=["ACEPTADA","PARCIALMENTE_RECIBIDA"]);self.fields["almacen"].queryset=Almacen.objects.filter(empresa=empresa,activo=True)
class DetalleRecepcionForm(TenantForm):
    detalle_orden=forms.ModelChoiceField(queryset=DetalleOrdenCompraEnterprise.objects.none());cantidad=forms.DecimalField(min_value=.0001);aceptada=forms.DecimalField(min_value=0,required=False);rechazada=forms.DecimalField(min_value=0,initial=0);lote=forms.CharField(required=False);serie=forms.CharField(required=False);vence_el=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}));motivo=forms.CharField(required=False)
    def __init__(self,*a,empresa=None,orden=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["detalle_orden"].queryset=DetalleOrdenCompraEnterprise.objects.filter(orden=orden,orden__empresa=empresa)
class SolicitudPagoForm(TenantForm):
    cuenta=forms.ModelChoiceField(queryset=CuentaPorPagarEnterprise.objects.none());monto=forms.DecimalField(min_value=.01)
    def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["cuenta"].queryset=CuentaPorPagarEnterprise.objects.filter(empresa=empresa,bloqueada=False,saldo__gt=0)
class FacturaProveedorForm(TenantForm):
    orden=forms.ModelChoiceField(queryset=OrdenCompraEnterprise.objects.none());recepcion=forms.ModelChoiceField(queryset=RecepcionCompra.objects.none());numero=forms.CharField(max_length=50);ncf=forms.CharField(max_length=30,required=False);fecha=forms.DateField(widget=forms.DateInput(attrs={"type":"date"}),initial=timezone.localdate);vence_el=forms.DateField(widget=forms.DateInput(attrs={"type":"date"}));tasa_cambio=forms.DecimalField(min_value=.000001,initial=1);descuentos=forms.DecimalField(min_value=0,initial=0);impuesto=forms.DecimalField(min_value=0,initial=0);retenciones=forms.DecimalField(min_value=0,initial=0);cargos=forms.DecimalField(min_value=0,initial=0);anticipos_aplicados=forms.DecimalField(min_value=0,initial=0);lineas=forms.JSONField(help_text="Lista de detalle_orden_id, cantidad, precio, descuento e impuesto.")
    def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["orden"].queryset=OrdenCompraEnterprise.objects.filter(empresa=empresa,estado__in=["RECIBIDA","PARCIALMENTE_RECIBIDA"]);self.fields["recepcion"].queryset=RecepcionCompra.objects.filter(empresa=empresa,estado__in=["PARCIAL","COMPLETA","CON_DIFERENCIAS"])
class NotaProveedorForm(TenantForm):
    factura=forms.ModelChoiceField(queryset=FacturaProveedor.objects.none());tipo=forms.ChoiceField(choices=[("CREDITO","Crédito"),("DEBITO","Débito")]);numero=forms.CharField(max_length=30);monto=forms.DecimalField(min_value=.01);impuesto=forms.DecimalField(min_value=0,initial=0);retencion=forms.DecimalField(min_value=0,initial=0);motivo=forms.CharField(min_length=5,widget=forms.Textarea)
    def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["factura"].queryset=FacturaProveedor.objects.filter(empresa=empresa).exclude(estado="ANULADA")
class AprobarPagoForm(TenantForm):
    solicitud_id=forms.IntegerField(min_value=1)
class PagoForm(TenantForm):
    orden=forms.ModelChoiceField(queryset=OrdenPago.objects.none())
    monto=forms.DecimalField(min_value=.01);metodo=forms.ChoiceField(choices=OrdenPago.METODOS);retencion=forms.DecimalField(min_value=0,initial=0);referencia=forms.CharField(max_length=100);cuenta_bancaria=forms.ModelChoiceField(queryset=CuentaBancariaEmpresa.objects.none(),required=False);caja=forms.ModelChoiceField(queryset=Caja.objects.none(),required=False)
    def __init__(self,*a,empresa=None,**k):super().__init__(*a,empresa=empresa,**k);self.fields["orden"].queryset=OrdenPago.objects.filter(empresa=empresa,estado__in=["APROBADA","PARCIAL"]);self.fields["cuenta_bancaria"].queryset=CuentaBancariaEmpresa.objects.filter(empresa=empresa,activa=True);self.fields["caja"].queryset=Caja.objects.filter(empresa=empresa)
    def clean(self):
        data=super().clean()
        if bool(data.get("cuenta_bancaria"))==bool(data.get("caja")):raise forms.ValidationError("Seleccione exactamente una cuenta bancaria o caja.")
        return data
class WizardStepForm(TenantForm):
    datos=forms.JSONField(help_text="Objeto JSON con referencias y datos del paso; sin secretos, archivos ni datos bancarios completos.",widget=forms.Textarea(attrs={"rows":8}))

class ExportForm(TenantForm):
    pass
    def __init__(self,*a,**k):
        super().__init__(*a,**k);self.fields["recurso"].choices=[*self.fields["recurso"].choices,("retenciones_fiscales","Retenciones fiscales")]
    recurso=forms.ChoiceField(choices=[(x,x.title()) for x in ("rfq","ofertas","comparativos","adjudicaciones","ordenes","recepciones","devoluciones","facturas","notas_credito","notas_debito","cxp","aging","pagos","conciliacion","proveedores","ahorro","cumplimiento")]);formato=forms.ChoiceField(choices=[("csv","CSV"),("xlsx","XLSX"),("pdf","PDF"),("print","Impresión")]);estado=forms.CharField(required=False)
