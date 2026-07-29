from django import forms

from .models import Cliente, ContactoCliente, DireccionCliente


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
