from django import forms

from .models import ConceptoNomina, LiquidacionLaboral, NovedadNomina, PeriodoNomina, PlantillaDocumentoRRHH


class TenantForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        for name in ("tipo", "empleado", "concepto", "periodo"):
            field = self.fields.get(name)
            if field is not None and hasattr(field, "queryset"):
                field.queryset = field.queryset.filter(empresa=empresa)


class PeriodoForm(TenantForm):
    class Meta:
        model = PeriodoNomina
        exclude = ("empresa", "creado_en")
        widgets = {"desde": forms.DateInput(attrs={"type": "date"}), "hasta": forms.DateInput(attrs={"type": "date"})}


class ConceptoForm(TenantForm):
    class Meta:
        model = ConceptoNomina
        exclude = ("empresa", "creado_en")


class NovedadForm(TenantForm):
    class Meta:
        model = NovedadNomina
        exclude = ("empresa", "creado_en", "estado")

    def clean_monto(self):
        amount = self.cleaned_data["monto"]
        if amount < 0:
            raise forms.ValidationError("El monto no puede ser negativo.")
        return amount


class LiquidacionForm(TenantForm):
    fecha_salida = forms.DateField(required=True, widget=forms.DateInput(attrs={"type": "date"}))
    tipo_terminacion = forms.ChoiceField(choices=(("DESAHUCIO", "Desahucio"), ("DESPIDO_INJUSTIFICADO", "Despido injustificado"), ("RENUNCIA", "Renuncia"), ("MUTUO_ACUERDO", "Mutuo acuerdo"), ("MATERNIDAD", "Protección por maternidad (revisión)"), ("FUERO_SINDICAL", "Fuero sindical (revisión)"), ("PROTECCION_ESPECIAL", "Otra protección especial (revisión)")))

    class Meta:
        model = LiquidacionLaboral
        fields = ("empleado", "fecha_salida", "tipo_terminacion")
        widgets = {"fecha_salida": forms.DateInput(attrs={"type": "date"})}


class PlantillaDocumentoForm(TenantForm):
    class Meta:
        model = PlantillaDocumentoRRHH
        exclude = ("empresa", "creado_en")
