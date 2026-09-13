from django import forms
from datetime import date
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from django.db.models import Q
from django.utils import timezone

from comercial.models import Pedido
from .recipe_units import opciones_unidad

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
            "unidad_rendimiento": forms.Select(choices=opciones_unidad()),
            "fecha_vigencia_desde": forms.DateInput(attrs={"type":"date"}),
            "fecha_vigencia_hasta": forms.DateInput(attrs={"type":"date"}),
            "instrucciones": forms.Textarea(attrs={"rows":4}),
        }
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,**kwargs); self.aplicar_estilo()
        self.fields["producto_terminado"].queryset = ProductoInventario.objects.filter(empresa=empresa, activo=True, tipo="producto_terminado")
        actual = getattr(self.instance, "unidad_rendimiento", "")
        if actual and actual not in dict(self.fields["unidad_rendimiento"].choices):
            self.fields["unidad_rendimiento"].choices = [*self.fields["unidad_rendimiento"].choices, (actual, actual)]


class IngredienteForm(StyledForm, forms.ModelForm):
    class Meta:
        model = DetalleRecetaProduccion
        fields = ("materia_prima","cantidad","unidad_medida","porcentaje_merma","es_opcional","observaciones","orden")
        widgets = {"unidad_medida": forms.Select(choices=opciones_unidad())}
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,**kwargs); self.aplicar_estilo()
        self.fields["materia_prima"].queryset = ProductoInventario.objects.filter(empresa=empresa, activo=True).exclude(tipo="producto_terminado")
        actual = getattr(self.instance, "unidad_medida", "")
        if actual and actual not in dict(self.fields["unidad_medida"].choices):
            self.fields["unidad_medida"].choices = [*self.fields["unidad_medida"].choices, (actual, actual)]


class FormulaRecetaUploadForm(forms.Form):
    MAX_BYTES = 10 * 1024 * 1024
    archivo = forms.FileField(
        label="Fórmula en PDF o imagen",
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png", "class": "form-control"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if archivo.size > self.MAX_BYTES:
            raise forms.ValidationError("El archivo no puede superar 10 MB.")
        extension = "." + archivo.name.lower().rsplit(".", 1)[-1] if "." in archivo.name else ""
        firmas = {".pdf": b"%PDF-", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff", ".png": b"\x89PNG\r\n\x1a\n"}
        mimes = {".pdf": {"application/pdf"}, ".jpg": {"image/jpeg"}, ".jpeg": {"image/jpeg"}, ".png": {"image/png"}}
        if extension not in firmas:
            raise forms.ValidationError("Solo se permiten archivos PDF, JPG, JPEG o PNG.")
        if archivo.content_type and archivo.content_type not in mimes[extension]:
            raise forms.ValidationError("El tipo MIME no corresponde a la extensión del archivo.")
        cabecera = archivo.read(8)
        archivo.seek(0)
        if not cabecera.startswith(firmas[extension]):
            formato = "PDF" if extension == ".pdf" else extension[1:].upper()
            raise forms.ValidationError(f"El contenido del archivo no corresponde a un {formato} válido.")
        return archivo


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
