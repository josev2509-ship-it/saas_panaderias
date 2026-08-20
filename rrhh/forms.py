from django import forms
from .models import AccionDisciplinaria, Capacitacion, ContratoEmpleado, Empleado, LicenciaEmpleado, ParticipacionCapacitacion, SalidaEmpleado, SolicitudVacacion

class TenantForm(forms.ModelForm):
    def __init__(self,*args,empresa=None,**kwargs):
        self.empresa=empresa;super().__init__(*args,**kwargs)
        for field in self.fields.values():field.widget.attrs.setdefault("class","form-control")
        for name in ("puesto","departamento","centro","supervisor","empleado","renovacion_de"):
            field=self.fields.get(name)
            if field is not None and hasattr(field,"queryset"):field.queryset=field.queryset.filter(empresa=empresa)

class EmpleadoForm(TenantForm):
    class Meta:model=Empleado;exclude=("empresa","creado_en");widgets={"fecha_ingreso":forms.DateInput(attrs={"type":"date"}),"fecha_nacimiento":forms.DateInput(attrs={"type":"date"}),"vence_licencia":forms.DateInput(attrs={"type":"date"})}
class ContratoForm(TenantForm):
    class Meta:model=ContratoEmpleado;exclude=("empresa","creado_en");widgets={"inicio":forms.DateInput(attrs={"type":"date"}),"fin":forms.DateInput(attrs={"type":"date"})}
class VacacionForm(TenantForm):
    class Meta:model=SolicitudVacacion;exclude=("empresa","creado_en");widgets={"desde":forms.DateInput(attrs={"type":"date"}),"hasta":forms.DateInput(attrs={"type":"date"})}
class LicenciaForm(TenantForm):
    class Meta:model=LicenciaEmpleado;exclude=("empresa","creado_en");widgets={"desde":forms.DateInput(attrs={"type":"date"}),"hasta":forms.DateInput(attrs={"type":"date"})}
class DisciplinaForm(TenantForm):
    class Meta:model=AccionDisciplinaria;exclude=("empresa","creado_en");widgets={"fecha":forms.DateInput(attrs={"type":"date"})}
class CapacitacionForm(TenantForm):
    class Meta:model=Capacitacion;exclude=("empresa","creado_en");widgets={"inicio":forms.DateInput(attrs={"type":"date"}),"fin":forms.DateInput(attrs={"type":"date"}),"vence_el":forms.DateInput(attrs={"type":"date"})}
class ParticipacionForm(TenantForm):
    class Meta:model=ParticipacionCapacitacion;fields=("capacitacion","resultado")
    def __init__(self,*args,empresa=None,**kwargs):
        super().__init__(*args,empresa=empresa,**kwargs);self.fields["capacitacion"].queryset=Capacitacion.objects.filter(empresa=empresa)
class SalidaForm(TenantForm):
    class Meta:model=SalidaEmpleado;exclude=("empresa","creado_en");widgets={"fecha_salida":forms.DateInput(attrs={"type":"date"}),"ultima_fecha_laborada":forms.DateInput(attrs={"type":"date"})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.fields["checklist"].required=False
