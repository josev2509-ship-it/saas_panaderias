from django import forms

from catalogos.models import Almacen, CentroCosto, CondicionPago, Impuesto, MonedaEmpresa, TipoCompra, UnidadMedida
from inventario.models import ProductoInventario
from .models import (
    CategoriaProveedor, ContactoProveedor, CuentaBancariaProveedor,
    DireccionProveedor, ProductoProveedor, Proveedor, ProveedorLegadoMap,
    DetalleSolicitudCompra, SolicitudCompra,
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


class SolicitudCompraForm(ScopedForm):
    class Meta:
        model=SolicitudCompra
        fields=("titulo","descripcion_corta","area_solicitante","centro_costo","responsable_centro_costo","almacen_destino","proyecto_codigo","proyecto_nombre","tipo_compra","naturaleza","prioridad","origen_necesidad","es_urgente","compra_directa_propuesta","motivo_compra_directa","requiere_contrato","requiere_inspeccion","requiere_activo_fijo","requiere_entrega_parcial","recurrente","frecuencia_recurrencia","fecha_solicitud","fecha_necesaria","fecha_limite_proceso","periodo_presupuestario","moneda","disponibilidad_presupuestaria","referencia_presupuestaria","observacion_presupuestaria","proveedor_sugerido","justificacion_proveedor_sugerido","proveedor_exclusivo_declarado","motivo_exclusividad","justificacion","impacto_no_compra","alcance","observaciones_internas","observaciones_aprobadores","riesgos_identificados")
        widgets={"fecha_solicitud":forms.DateInput(attrs={"type":"date"}),"fecha_necesaria":forms.DateInput(attrs={"type":"date"}),"fecha_limite_proceso":forms.DateInput(attrs={"type":"date"})}
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,empresa=empresa,**kwargs)
        for name,model in {"centro_costo":CentroCosto,"almacen_destino":Almacen,"tipo_compra":TipoCompra}.items():
            self.fields[name].queryset=model.objects.filter(empresa=empresa,activo=True)
        self.fields["proveedor_sugerido"].queryset=Proveedor.objects.filter(empresa=empresa,estado=Proveedor.Estado.ACTIVO,bloqueado=False)

class DetalleSolicitudCompraForm(ScopedForm):
    class Meta:
        model=DetalleSolicitudCompra
        fields=("tipo_linea","producto","descripcion","especificacion_tecnica","cantidad","unidad_medida","factor_conversion","precio_unitario_estimado","descuento_porcentaje","descuento_monto","impuesto","fecha_necesaria_linea","almacen_destino","centro_costo","proveedor_sugerido","marca_referencia","modelo_referencia","permite_equivalente","justificacion_no_equivalente","observaciones")
        widgets={"fecha_necesaria_linea":forms.DateInput(attrs={"type":"date"})}
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,empresa=empresa,**kwargs)
        for name,model in {"almacen_destino":Almacen,"centro_costo":CentroCosto}.items(): self.fields[name].queryset=model.objects.filter(empresa=empresa,activo=True)
        self.fields["proveedor_sugerido"].queryset=Proveedor.objects.filter(empresa=empresa,estado=Proveedor.Estado.ACTIVO,bloqueado=False)

class MotivoSolicitudForm(forms.Form): motivo=forms.CharField(min_length=5,widget=forms.Textarea(attrs={"rows":3,"class":"form-control"}))
class FiltroSolicitudForm(forms.Form):
    q=forms.CharField(required=False);estado=forms.ChoiceField(required=False,choices=(("","Todos"),*SolicitudCompra.Estado.choices));prioridad=forms.ChoiceField(required=False,choices=(("","Todas"),*SolicitudCompra.Prioridad.choices));desde=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}));hasta=forms.DateField(required=False,widget=forms.DateInput(attrs={"type":"date"}));urgentes=forms.BooleanField(required=False)
