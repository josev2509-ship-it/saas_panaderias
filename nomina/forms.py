from django import forms
from .models import ConceptoNomina,LiquidacionLaboral,PeriodoNomina,TipoNomina

class TenantForm(forms.ModelForm):
 def __init__(self,*args,empresa=None,**kwargs):
  self.empresa=empresa;super().__init__(*args,**kwargs)
  for f in self.fields.values():f.widget.attrs.setdefault("class","form-control")
  for name in ("tipo","empleado"):
   f=self.fields.get(name)
   if f is not None and hasattr(f,"queryset"):f.queryset=f.queryset.filter(empresa=empresa)
class PeriodoForm(TenantForm):
 class Meta:model=PeriodoNomina;exclude=("empresa","creado_en");widgets={"desde":forms.DateInput(attrs={"type":"date"}),"hasta":forms.DateInput(attrs={"type":"date"})}
class ConceptoForm(TenantForm):
 class Meta:model=ConceptoNomina;exclude=("empresa","creado_en")
class LiquidacionForm(TenantForm):
 class Meta:model=LiquidacionLaboral;exclude=("empresa","creado_en");widgets={"fecha":forms.DateInput(attrs={"type":"date"})}
