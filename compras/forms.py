from django import forms

from catalogos.models import CondicionPago, Impuesto, MonedaEmpresa, UnidadMedida
from inventario.models import ProductoInventario
from .models import (
    CategoriaProveedor, ContactoProveedor, CuentaBancariaProveedor,
    DireccionProveedor, ProductoProveedor, Proveedor, ProveedorLegadoMap,
)


class ScopedForm(forms.ModelForm):
    def __init__(self,*args,empresa=None,**kwargs):
        self.empresa=empresa
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class","form-control")
        scoped={
            "categoria":CategoriaProveedor,"proveedor":Proveedor,"proveedor_nuevo":Proveedor,
            "producto":ProductoInventario,"moneda":MonedaEmpresa,"moneda_habitual":MonedaEmpresa,
            "condicion_pago":CondicionPago,"impuesto_predeterminado":Impuesto,
            "unidad_compra":UnidadMedida,"unidad_base_producto":UnidadMedida,
        }
        for name,model in scoped.items():
            if name in self.fields and empresa:
                self.fields[name].queryset=model.objects.filter(empresa=empresa)


class ProveedorForm(ScopedForm):
    class Meta:
        model=Proveedor
        exclude=("empresa","estado","bloqueado","motivo_bloqueo","fecha_bloqueo","bloqueado_por",
                 "rnc_normalizado","documentacion_completa","fecha_ultima_revision_documental",
                 "proxima_revision_documental","creado_por","actualizado_por","fecha_creacion","fecha_actualizacion")


def related_form(model,exclude=()):
    meta=type("Meta",(),{"model":model,"exclude":("empresa","creado_por","actualizado_por","fecha_creacion","fecha_actualizacion",*exclude)})
    return type(f"{model.__name__}Form",(ScopedForm,),{"Meta":meta})


ContactoProveedorForm=related_form(ContactoProveedor,("proveedor",))
DireccionProveedorForm=related_form(DireccionProveedor,("proveedor",))
ProductoProveedorForm=related_form(ProductoProveedor,("proveedor",))


class CuentaBancariaProveedorForm(ScopedForm):
    numero_cuenta=forms.CharField(widget=forms.PasswordInput(render_value=True),help_text="Se mostrará enmascarado por defecto.")
    class Meta:
        model=CuentaBancariaProveedor
        exclude=("empresa","proveedor","numero_enmascarado","verificada","fecha_verificacion","verificada_por",
                 "estado","motivo_rechazo","creado_por","actualizado_por","fecha_creacion","fecha_actualizacion")


ProveedorLegadoMapForm=related_form(ProveedorLegadoMap,("proveedor_nuevo","confirmado_por"))


class TransicionForm(forms.Form):
    motivo=forms.CharField(min_length=5,widget=forms.Textarea(attrs={"rows":3,"class":"form-control"}),label="Motivo")
