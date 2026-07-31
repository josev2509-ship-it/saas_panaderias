from django import forms

from inventario.models import ProductoInventario
from comercial.models import SecuenciaDocumento


class DiagnosticoProductoForm(forms.Form):
    producto = forms.ModelChoiceField(queryset=ProductoInventario.objects.none())

    def __init__(self, *args, empresa, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = ProductoInventario.objects.filter(
            empresa=empresa, activo=True
        )


class ReconstruccionSaldoForm(DiagnosticoProductoForm):
    motivo = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), min_length=5)


class TechnicalFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar")
    estado = forms.CharField(required=False)
    operacion = forms.CharField(required=False)
    fecha_desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    fecha_hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))


class ReintentoEventoForm(forms.Form):
    motivo = forms.CharField(
        min_length=5, max_length=250, required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class AccionIdempotenciaForm(forms.Form):
    motivo = forms.CharField(
        min_length=5, max_length=250,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class SecuenciaDocumentoForm(forms.ModelForm):
    class Meta:
        model = SecuenciaDocumento
        fields = ("prefijo", "longitud", "activo", "reinicia_anualmente")

    def clean(self):
        cleaned = super().clean()
        from core.domain.rules import validate_document_length, validate_prefix
        try:
            validate_prefix(cleaned.get("prefijo") or self.instance.tipo)
            validate_document_length(cleaned.get("longitud"))
        except Exception as exc:
            raise forms.ValidationError(str(exc))
        return cleaned


class SecuenciaDocumentoCreateForm(SecuenciaDocumentoForm):
    class Meta(SecuenciaDocumentoForm.Meta):
        fields = (
            "tipo", "periodo", "prefijo", "longitud", "activo",
            "reinicia_anualmente",
        )
