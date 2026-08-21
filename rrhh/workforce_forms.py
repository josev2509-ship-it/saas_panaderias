from django import forms
from .forms import TenantForm
from .models import HoraExtra,IncidenciaAsistencia,NovedadTSS,RegistroAsistencia,ReingresoEmpleado

class PoncheForm(TenantForm):
 class Meta:model=RegistroAsistencia;exclude=("empresa","creado_en","horas_trabajadas","minutos_tardanza","corregido");widgets={"fecha":forms.DateInput(attrs={"type":"date"}),"entrada":forms.DateTimeInput(attrs={"type":"datetime-local"}),"salida":forms.DateTimeInput(attrs={"type":"datetime-local"})}
class IncidenciaForm(TenantForm):
 class Meta:model=IncidenciaAsistencia;exclude=("empresa","creado_en","aprobador","aprobada");
 def __init__(self,*args,empresa=None,**kwargs):
  super().__init__(*args,empresa=empresa,**kwargs);self.fields["registro"].queryset=self.fields["registro"].queryset.filter(empresa=empresa)
class HoraExtraForm(TenantForm):
 class Meta:model=HoraExtra;exclude=("empresa","creado_en","aprobador","nomina_id");widgets={"fecha":forms.DateInput(attrs={"type":"date"})}
class TSSForm(TenantForm):
 class Meta:model=NovedadTSS;exclude=("empresa","creado_en")
class ReingresoForm(TenantForm):
 class Meta:model=ReingresoEmpleado;exclude=("empresa","creado_en");widgets={"fecha_reingreso":forms.DateInput(attrs={"type":"date"})}
