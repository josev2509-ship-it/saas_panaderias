from django import forms
from datetime import date
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from django.db.models import Q
from django.utils import timezone

from comercial.models import Pedido

from .models import (
    DetallePlanProduccion, DetalleRecetaProduccion, OrdenProduccion, PlanProduccion,
    ProductoInventario, RecetaProduccion,
)


class StyledForm:
    def aplicar_estilo(self):
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"


class RecetaProduccionForm(StyledForm, forms.ModelForm):
    class Meta:
        model = RecetaProduccion
        fields = (
            "codigo","nombre","producto_terminado","version","rendimiento_base","unidad_rendimiento",
            "porcentaje_merma_estimada","tiempo_preparacion_minutos","tiempo_produccion_minutos",
            "instrucciones","activa","fecha_vigencia_desde","fecha_vigencia_hasta",
        )
        widgets = {
            "fecha_vigencia_desde": forms.DateInput(attrs={"type":"date"}),
            "fecha_vigencia_hasta": forms.DateInput(attrs={"type":"date"}),
            "instrucciones": forms.Textarea(attrs={"rows":4}),
        }
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,**kwargs); self.aplicar_estilo()
        self.fields["producto_terminado"].queryset = ProductoInventario.objects.filter(empresa=empresa, activo=True, tipo="producto_terminado")


class IngredienteForm(StyledForm, forms.ModelForm):
    class Meta:
        model = DetalleRecetaProduccion
        fields = ("materia_prima","cantidad","unidad_medida","porcentaje_merma","es_opcional","observaciones","orden")
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,**kwargs); self.aplicar_estilo()
        self.fields["materia_prima"].queryset = ProductoInventario.objects.filter(empresa=empresa, activo=True).exclude(tipo="producto_terminado")


IngredientesFormSet = inlineformset_factory(RecetaProduccion, DetalleRecetaProduccion, form=IngredienteForm, extra=1, can_delete=True)


class PlanProduccionForm(StyledForm, forms.ModelForm):
    class Meta:
        model = PlanProduccion
        fields = ("fecha_plan","observaciones")
        widgets = {"fecha_plan":forms.DateInput(attrs={"type":"date"}),"observaciones":forms.Textarea(attrs={"rows":3})}
    def __init__(self,*args,**kwargs): super().__init__(*args,**kwargs); self.aplicar_estilo()


class DetallePlanForm(StyledForm, forms.ModelForm):
    class Meta:
        model = DetallePlanProduccion
        fields = ("producto_terminado","receta","cantidad_solicitada","cantidad_planificada","unidad_medida","prioridad","fecha_requerida","observaciones")
        widgets = {"fecha_requerida":forms.DateInput(attrs={"type":"date"})}
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,**kwargs); self.aplicar_estilo()
        self.fields["producto_terminado"].queryset = ProductoInventario.objects.filter(empresa=empresa,activo=True,tipo="producto_terminado")
        self.fields["receta"].queryset = RecetaProduccion.objects.filter(empresa=empresa,activa=True)


DetallesPlanFormSet = inlineformset_factory(PlanProduccion, DetallePlanProduccion, form=DetallePlanForm, extra=1, can_delete=True)


class GenerarPlanPedidosForm(StyledForm, forms.Form):
    fecha_plan = forms.DateField(widget=forms.DateInput(attrs={"type":"date"}), initial=timezone.localdate)
    fecha_desde = forms.DateField(widget=forms.DateInput(attrs={"type":"date"}), required=False)
    fecha_hasta = forms.DateField(widget=forms.DateInput(attrs={"type":"date"}), required=False)
    pedidos = forms.ModelMultipleChoiceField(queryset=Pedido.objects.none(), widget=forms.CheckboxSelectMultiple)
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,**kwargs); self.aplicar_estilo()
        qs=Pedido.objects.filter(empresa=empresa,estado=Pedido.Estado.APROBADO)
        if self.data.get("fecha_desde"): qs=qs.filter(fecha_entrega__gte=self.data["fecha_desde"])
        if self.data.get("fecha_hasta"): qs=qs.filter(fecha_entrega__lte=self.data["fecha_hasta"])
        self.fields["pedidos"].queryset=qs


class OrdenProduccionForm(StyledForm, forms.ModelForm):
    class Meta:
        model=OrdenProduccion
        fields=("plan","detalle_plan","producto_terminado","receta","fecha_programada","turno","prioridad","cantidad_planificada","unidad_medida","responsable","observaciones")
        widgets={"fecha_programada":forms.DateInput(attrs={"type":"date"}),"observaciones":forms.Textarea(attrs={"rows":3})}
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,**kwargs); self.aplicar_estilo()
        if not self.instance.pk:
            self.instance.empresa = empresa
        self.fields["plan"].queryset=PlanProduccion.objects.filter(empresa=empresa).exclude(estado=PlanProduccion.Estado.CANCELADO)
        self.fields["detalle_plan"].queryset=DetallePlanProduccion.objects.filter(plan__empresa=empresa)
        self.fields["producto_terminado"].queryset=ProductoInventario.objects.filter(empresa=empresa,activo=True,tipo="producto_terminado")
        fecha = self.data.get("fecha_programada") if self.is_bound else getattr(self.instance, "fecha_programada", None)
        try:
            fecha = date.fromisoformat(str(fecha)) if fecha else timezone.localdate()
        except ValueError:
            fecha = timezone.localdate()
        self.fields["receta"].queryset=RecetaProduccion.objects.filter(
            empresa=empresa, activa=True, fecha_vigencia_desde__lte=fecha
        ).filter(Q(fecha_vigencia_hasta__isnull=True) | Q(fecha_vigencia_hasta__gte=fecha))
        self.fields["responsable"].queryset=User.objects.filter(is_active=True)


class InicioOrdenForm(StyledForm, forms.Form):
    cantidad_iniciada=forms.DecimalField(min_value=0.0001,decimal_places=4,max_digits=14)
    comentario=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":2}))
    def __init__(self,*args,**kwargs): super().__init__(*args,**kwargs); self.aplicar_estilo()


class CompletarOrdenForm(StyledForm, forms.Form):
    cantidad_producida=forms.DecimalField(min_value=0,decimal_places=4,max_digits=14)
    cantidad_rechazada=forms.DecimalField(min_value=0,decimal_places=4,max_digits=14)
    comentario=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":2}))
    def __init__(self,*args,**kwargs): super().__init__(*args,**kwargs); self.aplicar_estilo()
