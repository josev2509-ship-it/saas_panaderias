from django import forms

from .models import (
    Factura606,
    Proveedor,
)


class ProveedorForm(forms.ModelForm):

    class Meta:
        model = Proveedor

        fields = [
            "nombre",
            "rnc",
            "nombre_comercial",
            "telefono",
            "correo",
            "direccion",
            "estado_dgii",
            "actividad_economica",
            "provincia",
            "municipio",
            "consultado_dgii",
            "activo",
        ]


class Factura606Form(forms.ModelForm):

    class Meta:

        model = Factura606

        fields = "__all__"

        widgets = {

            "proveedor": forms.Select(
                attrs={"class": "form-select"}
            ),

            "tipo_bienes_servicios": forms.Select(
                attrs={"class": "form-select"}
            ),

            "numero_comprobante": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "ncf_modificado": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "fecha_comprobante": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

            "fecha_pago": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

            "monto_facturado": forms.NumberInput(
                attrs={"class": "form-control"}
            ),

            "itbis_facturado": forms.NumberInput(
                attrs={"class": "form-control"}
            ),

            "retencion_renta": forms.NumberInput(
                attrs={"class": "form-control"}
            ),

            "retencion_itbis": forms.NumberInput(
                attrs={"class": "form-control"}
            ),

            "fecha_vencimiento": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

            "estado": forms.Select(
                attrs={"class": "form-select"}
            ),

            "observacion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3
                }
            ),
        }