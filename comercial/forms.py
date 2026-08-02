from django import forms
from decimal import Decimal

from django.forms import inlineformset_factory

from .models import (
    Cliente, ContactoCliente, DetallePedido, DireccionCliente, Pedido,
    ConfiguracionComercialEmpresa, CanalVenta, SegmentoCliente, ClasificacionCliente,
    TipoCliente, TipoEntrega, PrioridadComercial, MotivoComercial, EquipoComercial,
    VendedorComercial, ZonaComercial, RutaComercial, PoliticaCredito, PoliticaDescuento,
    PoliticaEntrega, PoliticaFacturacion, PoliticaDevolucion, PoliticaComision,
    SecuenciaDocumento,
    Prospecto, OportunidadComercial, ActividadComercial,
    ProductoComercial, ListaPrecio, DetalleListaPrecio, CotizacionVenta, DetalleCotizacionVenta,
)


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"


class ClienteForm(StyledModelForm):
    class Meta:
        model = Cliente
        exclude = (
            "empresa", "creado_por", "fecha_creacion", "fecha_actualizacion",
            "credito_utilizado", "categoria_riesgo", "score_riesgo",
            "explicacion_riesgo", "version_formula_riesgo", "fecha_calculo_riesgo",
        )
        widgets = {
            "direccion_fiscal": forms.Textarea(attrs={"rows": 3}),
            "observaciones": forms.Textarea(attrs={"rows": 4}),
            "limite_credito": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "descuento_maximo": forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.01"}),
            "dias_credito": forms.NumberInput(attrs={"min": "0"}),
        }


class DireccionClienteForm(StyledModelForm):
    class Meta:
        model = DireccionCliente
        exclude = ("cliente", "fecha_creacion", "fecha_actualizacion")
        widgets = {
            "direccion": forms.Textarea(attrs={"rows": 3}),
            "referencia": forms.Textarea(attrs={"rows": 2}),
            "instrucciones_entrega": forms.Textarea(attrs={"rows": 3}),
            "latitud": forms.NumberInput(attrs={"step": "0.0000001"}),
            "longitud": forms.NumberInput(attrs={"step": "0.0000001"}),
        }


class ContactoClienteForm(StyledModelForm):
    class Meta:
        model = ContactoCliente
        exclude = ("cliente", "fecha_creacion", "fecha_actualizacion")


class PedidoForm(StyledModelForm):
    class Meta:
        model = Pedido
        fields = (
            "cliente", "direccion_entrega", "contacto", "fecha_pedido", "fecha_entrega",
            "hora_entrega_desde", "hora_entrega_hasta", "prioridad", "condicion_pago",
            "dias_credito", "lista_precio", "moneda", "observaciones_cliente", "observaciones_internas",
        )
        widgets = {
            "fecha_pedido": forms.DateInput(attrs={"type": "date"}),
            "fecha_entrega": forms.DateInput(attrs={"type": "date"}),
            "hora_entrega_desde": forms.TimeInput(attrs={"type": "time"}),
            "hora_entrega_hasta": forms.TimeInput(attrs={"type": "time"}),
            "observaciones_cliente": forms.Textarea(attrs={"rows": 3}),
            "observaciones_internas": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Cliente.objects.filter(
            empresa=empresa, estado__in=[Cliente.Estado.ACTIVO, Cliente.Estado.EN_EVALUACION]
        )
        cliente_id = self.data.get("cliente") if self.is_bound else getattr(self.instance, "cliente_id", None)
        self.fields["direccion_entrega"].queryset = DireccionCliente.objects.filter(
            cliente_id=cliente_id, cliente__empresa=empresa, activa=True
        )
        self.fields["contacto"].queryset = ContactoCliente.objects.filter(
            cliente_id=cliente_id, cliente__empresa=empresa, activo=True
        )


class DetallePedidoForm(StyledModelForm):
    class Meta:
        model = DetallePedido
        fields = (
            "producto", "cantidad", "precio_unitario", "porcentaje_descuento",
            "porcentaje_impuesto", "observaciones", "orden",
        )
        widgets = {
            "cantidad": forms.NumberInput(attrs={"min": "0.0001", "step": "0.0001"}),
            "precio_unitario": forms.NumberInput(attrs={"min": "0", "step": "0.0001"}),
            "porcentaje_descuento": forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.01"}),
            "porcentaje_impuesto": forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.01"}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = self.fields["producto"].queryset.filter(
            empresa=empresa, activo=True, tipo="producto_terminado"
        )


DetallePedidoFormSet = inlineformset_factory(
    Pedido, DetallePedido, form=DetallePedidoForm, extra=1, can_delete=True, min_num=0, validate_min=False
)


class RechazoPedidoForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo del rechazo", widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}), max_length=1000
    )


class EmpresaScopedModelForm(StyledModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            queryset = getattr(field, "queryset", None)
            if queryset is not None and hasattr(queryset.model, "empresa_id"):
                field.queryset = queryset.filter(empresa=empresa)


class ConfiguracionComercialForm(EmpresaScopedModelForm):
    class Meta:
        model = ConfiguracionComercialEmpresa
        exclude = ("empresa", "estado", "version", "lista_para_vender", "porcentaje_preparacion",
                   "ultima_validacion", "resultado_validacion", "creado_por", "actualizado_por",
                   "fecha_creacion", "fecha_actualizacion")


class CatalogoComercialForm(EmpresaScopedModelForm):
    class Meta:
        model = CanalVenta
        fields = ("codigo", "nombre", "descripcion", "orden")
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}


def catalogo_form_factory(model):
    fields = ["codigo", "nombre", "descripcion", "orden"]
    if model is MotivoComercial:
        fields.append("categoria")
    if model is RutaComercial:
        fields.extend(["zona", "dias_visita"])
    if model is EquipoComercial:
        fields.append("supervisor")
    if model is VendedorComercial:
        fields.extend(["usuario", "equipo", "zona", "rutas", "meta_mensual"])
    return forms.modelform_factory(model, form=EmpresaScopedModelForm, fields=fields)


class PoliticaComercialForm(EmpresaScopedModelForm):
    class Meta:
        model = PoliticaCredito
        fields = ("codigo", "nombre", "vigencia_desde", "vigencia_hasta", "prioridad", "ambito", "reglas")
        widgets = {"vigencia_desde": forms.DateInput(attrs={"type": "date"}),
                   "vigencia_hasta": forms.DateInput(attrs={"type": "date"}),
                   "ambito": forms.Textarea(attrs={"rows": 4}), "reglas": forms.Textarea(attrs={"rows": 6})}


def politica_form_factory(model):
    return forms.modelform_factory(model, form=PoliticaComercialForm,
                                   fields=PoliticaComercialForm.Meta.fields,
                                   widgets=PoliticaComercialForm.Meta.widgets)


class SecuenciaComercialForm(EmpresaScopedModelForm):
    class Meta:
        model = SecuenciaDocumento
        fields = ("prefijo", "longitud", "reinicia_anualmente", "activo")


class FiltroReporteComercialForm(forms.Form):
    tipo = forms.CharField(required=False, max_length=40)
    estado = forms.CharField(required=False, max_length=20)
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))


class ProspectoForm(EmpresaScopedModelForm):
    class Meta:
        model=Prospecto
        exclude=("empresa","numero","estado","motivo_no_calificacion","motivo_descarte","creado_por","actualizado_por","convertido_por","fecha_conversion","cliente_convertido","fecha_creacion","fecha_actualizacion")
        widgets={"direccion":forms.Textarea(attrs={"rows":3}),"observaciones":forms.Textarea(attrs={"rows":3}),"fecha_primer_contacto":forms.DateInput(attrs={"type":"date"}),"fecha_proxima_accion":forms.DateTimeInput(attrs={"type":"datetime-local"})}


class OportunidadForm(EmpresaScopedModelForm):
    class Meta:
        model=OportunidadComercial
        exclude=("empresa","numero","etapa","monto_ponderado","motivo_perdida","motivo_cancelacion","creado_por","actualizado_por","cerrado_por","fecha_cierre_real","fecha_creacion","fecha_actualizacion")
        widgets={"descripcion":forms.Textarea(attrs={"rows":3}),"observaciones":forms.Textarea(attrs={"rows":3}),"fecha_apertura":forms.DateInput(attrs={"type":"date"}),"fecha_estimada_cierre":forms.DateInput(attrs={"type":"date"}),"fecha_proxima_accion":forms.DateTimeInput(attrs={"type":"datetime-local"})}


class ActividadComercialForm(EmpresaScopedModelForm):
    class Meta:
        model=ActividadComercial
        exclude=("empresa","estado","resultado","creado_por","actualizado_por","completado_por","fecha_creacion","fecha_actualizacion")
        widgets={"descripcion":forms.Textarea(attrs={"rows":3}),"fecha_inicio":forms.DateTimeInput(attrs={"type":"datetime-local"}),"fecha_fin":forms.DateTimeInput(attrs={"type":"datetime-local"}),"fecha_recordatorio":forms.DateTimeInput(attrs={"type":"datetime-local"}),"fecha_siguiente_accion":forms.DateTimeInput(attrs={"type":"datetime-local"})}
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,empresa=empresa,**kwargs)
        from django.contrib.auth import get_user_model
        from django.db.models import Q
        self.fields["responsable"].queryset=get_user_model().objects.filter(Q(empresa_principal=empresa)|Q(perfiles_vendedor__empresa=empresa)).distinct()

class ProductoComercialForm(EmpresaScopedModelForm):
    class Meta:model=ProductoComercial;exclude=("empresa","fecha_creacion","fecha_actualizacion");widgets={"descripcion_venta":forms.Textarea(attrs={"rows":3})}
class ListaPrecioForm(EmpresaScopedModelForm):
    class Meta:model=ListaPrecio;exclude=("empresa","version","estado","version_anterior","creado_por","fecha_creacion");widgets={"vigencia_desde":forms.DateInput(attrs={"type":"date"}),"vigencia_hasta":forms.DateInput(attrs={"type":"date"})}
class DetalleListaPrecioForm(EmpresaScopedModelForm):
    class Meta:model=DetalleListaPrecio;exclude=("lista",)
class CotizacionVentaForm(EmpresaScopedModelForm):
    class Meta:model=CotizacionVenta;exclude=("empresa","numero","version","estado","subtotal","descuento_total","impuesto_total","total","creado_por","actualizado_por","aprobado_por","fecha_creacion","fecha_actualizacion");widgets={"fecha":forms.DateInput(attrs={"type":"date"}),"valida_hasta":forms.DateInput(attrs={"type":"date"}),"observaciones":forms.Textarea(attrs={"rows":3})}
class LineaCotizacionForm(EmpresaScopedModelForm):
    descuento=forms.DecimalField(min_value=0,max_value=100,initial=0)
    class Meta:model=DetalleCotizacionVenta;fields=("producto","cantidad","descuento")
class SimuladorPrecioForm(forms.Form):
    cliente=forms.ModelChoiceField(queryset=Cliente.objects.none());producto=forms.ModelChoiceField(queryset=ProductoComercial.objects.none());cantidad=forms.DecimalField(min_value=Decimal("0.0001"));fecha=forms.DateField(widget=forms.DateInput(attrs={"type":"date"}))
    def __init__(self,*a,empresa=None,**k):super().__init__(*a,**k);self.fields["cliente"].queryset=Cliente.objects.filter(empresa=empresa);self.fields["producto"].queryset=ProductoComercial.objects.filter(empresa=empresa,activo=True,disponible_venta=True)
