from django import forms
from django.conf import settings
from .models import AccionDisciplinaria, Capacitacion, CentroTrabajo, ContratoEmpleado, Departamento, DescripcionPuesto, Empleado, EntidadFinancieraRRHH, LicenciaEmpleado, ParticipacionCapacitacion, SalidaEmpleado, SolicitudDocumentoRRHH, SolicitudVacacion

class TenantForm(forms.ModelForm):
    def __init__(self,*args,empresa=None,**kwargs):
        self.empresa=empresa;super().__init__(*args,**kwargs)
        for field in self.fields.values():field.widget.attrs.setdefault("class","form-control")
        for name in ("puesto","departamento","centro","supervisor","empleado","renovacion_de"):
            field=self.fields.get(name)
            if field is not None and hasattr(field,"queryset"):field.queryset=field.queryset.filter(empresa=empresa)

class EmpleadoForm(TenantForm):
    eliminar_foto=forms.BooleanField(required=False,label="Eliminar fotografía actual")
    class Meta:model=Empleado;exclude=("empresa","creado_en","codigo");widgets={"fecha_ingreso":forms.DateInput(attrs={"type":"date"}),"fecha_nacimiento":forms.DateInput(attrs={"type":"date"}),"vence_licencia":forms.DateInput(attrs={"type":"date"}),"direccion":forms.Textarea(attrs={"rows":2}),"observaciones":forms.Textarea(attrs={"rows":2}),"foto":forms.FileInput(attrs={"accept":"image/jpeg,image/png,image/webp"})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.fields["centro"].label="Lugar de trabajo";self.fields["supervisor"].queryset=Empleado.objects.filter(empresa=self.empresa,estado="ACTIVO",es_supervisor=True).exclude(pk=self.instance.pk)
    def clean_identificacion(self):
        value=self.cleaned_data["identificacion"].strip()
        qs=Empleado.objects.filter(empresa=self.empresa,identificacion=value)
        if self.instance.pk:qs=qs.exclude(pk=self.instance.pk)
        if qs.exists():raise forms.ValidationError("Ya existe un empleado con esta identificación en la empresa.")
        return value
    def clean_foto(self):
        photo=self.cleaned_data.get("foto")
        if photo and getattr(photo,"size",0)>getattr(settings,"RRHH_FOTO_MAX_UPLOAD_SIZE",5*1024*1024):raise forms.ValidationError("La fotografía supera el máximo permitido de 5 MB.")
        if photo and getattr(photo,"content_type","") not in {"image/jpeg","image/png","image/webp"}:raise forms.ValidationError("Use una fotografía JPG, PNG o WEBP.")
        return photo
class ContratoForm(TenantForm):
    class Meta:model=ContratoEmpleado;exclude=("empresa","creado_en","numero");widgets={"inicio":forms.DateInput(attrs={"type":"date"}),"fin":forms.DateInput(attrs={"type":"date"}),"objeto":forms.Textarea(attrs={"rows":3}),"motivo_temporal":forms.Textarea(attrs={"rows":3}),"anexos":forms.Textarea(attrs={"rows":3})}
    def clean(self):
        data=super().clean();tipo=(data.get("tipo") or "").upper()
        if "TEMPOR" in tipo and (not data.get("fin") or not data.get("motivo_temporal")):raise forms.ValidationError("El contrato temporal requiere fecha de finalización y causa temporal documentada.")
        return data

class DepartamentoForm(TenantForm):
    class Meta:model=Departamento;exclude=("empresa","creado_en")
class LugarTrabajoForm(TenantForm):
    class Meta:model=CentroTrabajo;exclude=("empresa","creado_en");labels={"nombre":"Lugar de trabajo"}
class EntidadFinancieraForm(TenantForm):
    class Meta:model=EntidadFinancieraRRHH;exclude=("empresa","creado_en")
class SolicitudDocumentoForm(TenantForm):
    class Meta:model=SolicitudDocumentoRRHH;fields=("tipo","empleado","entidad_financiera","destinatario","pais_destino","proposito")
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.fields["entidad_financiera"].queryset=EntidadFinancieraRRHH.objects.filter(empresa=self.empresa,activo=True);self.fields["entidad_financiera"].required=False
    def clean(self):
        data=super().clean()
        if data.get("tipo")=="BANCARIA" and not data.get("entidad_financiera"):self.add_error("entidad_financiera","Seleccione la entidad financiera destinataria.")
        return data
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
class DescripcionPuestoForm(TenantForm):
    class Meta:model=DescripcionPuesto;exclude=("empresa","creado_en");widgets={"vigente_desde":forms.DateInput(attrs={"type":"date"})}
