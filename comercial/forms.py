from django import forms

from django.forms import inlineformset_factory

from .models import Cliente, ContactoCliente, DetallePedido, DireccionCliente, Pedido


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
        exclude = ("empresa", "creado_por", "fecha_creacion", "fecha_actualizacion")
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
