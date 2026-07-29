from django import forms
from django.conf import settings

from .models import Documento, TipoDocumento


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ("tipo_documento", "titulo", "descripcion", "archivo", "fecha_documento", "fecha_vencimiento", "confidencial")
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "fecha_documento": forms.DateInput(attrs={"type": "date"}),
            "fecha_vencimiento": forms.DateInput(attrs={"type": "date"}),
            "archivo": forms.FileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png,.webp"}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        self.fields["tipo_documento"].queryset = TipoDocumento.objects.filter(empresa=empresa, activo=True)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"
        limite = getattr(settings, "DOCUMENTOS_MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
        self.fields["archivo"].help_text = f"PDF, JPG, JPEG, PNG o WEBP. Máximo {limite // (1024 * 1024)} MB."


class ReemplazoDocumentoForm(forms.Form):
    archivo = forms.FileField(widget=forms.FileInput(attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png,.webp"}))
