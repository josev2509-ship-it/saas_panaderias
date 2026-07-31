from django import forms

from .models import (
    Almacen, CentroCosto, CondicionPago, ConversionUnidad, Impuesto,
    MonedaEmpresa, TipoCompra, UnidadMedida,
)


class ScopedModelForm(forms.ModelForm):
    def __init__(self, *args, empresa=None, **kwargs):
        self.empresa = empresa
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        for name in ("centro_padre", "unidad_origen", "unidad_destino", "producto"):
            if name in self.fields and empresa:
                self.fields[name].queryset = self.fields[name].queryset.filter(empresa=empresa)


def form_for(model):
    meta = type("Meta", (), {"model": model, "exclude": ("empresa", "creado_por", "actualizado_por", "creado_en", "actualizado_en")})
    return type(f"{model.__name__}Form", (ScopedModelForm,), {"Meta": meta})


CondicionPagoForm = form_for(CondicionPago)
UnidadMedidaForm = form_for(UnidadMedida)
ConversionUnidadForm = form_for(ConversionUnidad)
AlmacenForm = form_for(Almacen)
CentroCostoForm = form_for(CentroCosto)
ImpuestoForm = form_for(Impuesto)
TipoCompraForm = form_for(TipoCompra)


class MonedaEmpresaForm(ScopedModelForm):
    class Meta:
        model = MonedaEmpresa
        exclude = ("empresa", "creado_en")
