from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import AsignadorNivel,CondicionReglaAprobacion,NivelAprobacion,ReglaAprobacion,SuplenciaAprobador
class ScopedForm(forms.ModelForm):
 def __init__(self,*a,empresa=None,**kw):
  self.empresa=empresa;super().__init__(*a,**kw)
  for f in self.fields.values(): f.widget.attrs.setdefault("class","form-control")
  for n in ("usuario","titular","suplente"):
   if n in self.fields and empresa:self.fields[n].queryset=get_user_model().objects.filter(Q(empresa_principal=empresa)|Q(membresias_workflow__empresa=empresa,membresias_workflow__activo=True),is_active=True).distinct()
class ReglaForm(ScopedForm):
 class Meta:model=ReglaAprobacion;exclude=("empresa","estado","version","activa","creado_por","actualizado_por","creado_en","actualizado_en")
class CondicionForm(ScopedForm):
 class Meta:model=CondicionReglaAprobacion;exclude=("empresa","regla","creado_en","actualizado_en")
class NivelForm(ScopedForm):
 class Meta:model=NivelAprobacion;exclude=("empresa","regla","creado_en","actualizado_en")
class AsignadorForm(ScopedForm):
 class Meta:model=AsignadorNivel;exclude=("empresa","nivel","creado_en","actualizado_en")
class SuplenciaForm(ScopedForm):
 class Meta:model=SuplenciaAprobador;exclude=("empresa","creada_por","aprobada_por","creado_en","actualizado_en")
class DecisionForm(forms.Form):
 comentario=forms.CharField(required=False,widget=forms.Textarea(attrs={"rows":3,"class":"form-control"}));idempotency_key=forms.CharField(widget=forms.HiddenInput())
class MotivoForm(forms.Form):
 motivo=forms.CharField(min_length=5,widget=forms.Textarea(attrs={"rows":3,"class":"form-control"}))
