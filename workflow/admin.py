from django.contrib import admin
from .models import *
class ScopedAdmin(admin.ModelAdmin):
 def get_queryset(self,r):
  qs=super().get_queryset(r);e=getattr(r.user,"empresa_principal",None);return qs.filter(empresa=e) if e else qs.none()
 def has_delete_permission(self,r,obj=None):return False
@admin.register(ReglaAprobacion)
class ReglaAdmin(ScopedAdmin):
 list_display=("codigo","nombre","dominio","tipo_documento","version","estado");list_filter=("estado","dominio");search_fields=("codigo","nombre","tipo_documento")
 def get_readonly_fields(self,r,obj=None):return tuple(f.name for f in self.model._meta.fields) if obj and obj.estado=="ACTIVA" else ()
@admin.register(DecisionAprobacion)
class DecisionAdmin(ScopedAdmin):
 readonly_fields=tuple(f.name for f in DecisionAprobacion._meta.fields)
 def has_add_permission(self,r):return False
 def has_change_permission(self,r,obj=None):return False
for model in (MiembroWorkflowEmpresa,CondicionReglaAprobacion,NivelAprobacion,AsignadorNivel,SuplenciaAprobador,InstanciaWorkflow,RondaWorkflow,NivelInstanciaWorkflow,AsignacionAprobacion,SolicitudCorreccionWorkflow):admin.site.register(model,ScopedAdmin)
