import csv
from uuid import uuid4
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.paginator import Paginator
from django.db.models import Avg,Count,F,ExpressionWrapper,DurationField
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from conduces.decorators import modulo_requerido
from conduces.services import obtener_empresa_usuario
from core.application.operation_context import OperationContext
from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from .application.services import activar_regla,agregar_condicion,agregar_nivel,aprobar,abstenerse,cancelar_workflow,configurar_asignador,crear_suplencia,devolver,rechazar,retirar_regla,validar_regla,versionar_regla
from .forms import AsignadorForm,CondicionForm,DecisionForm,MotivoForm,NivelForm,ReglaForm,SuplenciaForm
from .models import DecisionAprobacion,InstanciaWorkflow,NivelInstanciaWorkflow,ReglaAprobacion,SuplenciaAprobador
from .selectors import instancias_empresa,reglas_empresa,tareas_usuario
def _empresa(r):return obtener_empresa_usuario(r)
def _ctx(r,key=""):return OperationContext(empresa=_empresa(r),usuario=r.user,request=r,referencia=r.path,clave_idempotente=key)
@login_required
@modulo_requerido("modulo_workflow","workflow.view_instanciaworkflow")
def dashboard(request):
 qs=instancias_empresa(empresa=_empresa(request));rules=ReglaAprobacion.objects.filter(empresa=_empresa(request));subs=SuplenciaAprobador.objects.filter(empresa=_empresa(request),activa=True,vigente_desde__lte=timezone.now(),vigente_hasta__gte=timezone.now())
 return render(request,"workflow/dashboard.html",{"total":qs.count(),"states":qs.values("estado").annotate(total=Count("id")),"pendientes_nivel":qs.filter(estado="EN_APROBACION").values("nivel_actual").annotate(total=Count("id")),"pendientes_dominio":qs.filter(estado="EN_APROBACION").values("dominio").annotate(total=Count("id")),"reglas_activas":rules.filter(estado="ACTIVA").count(),"reglas_error":sum(bool(validar_regla(context=_ctx(request),regla_id=x.pk)) for x in rules) if request.user.has_perm("workflow.validar_regla_aprobacion") else 0,"suplencias":subs.count()})
@login_required
@modulo_requerido("modulo_workflow","workflow.view_reglaaprobacion")
def reglas(request):
 qs=reglas_empresa(empresa=_empresa(request),q=request.GET.get("q",""),estado=request.GET.get("estado",""));return render(request,"workflow/reglas.html",{"reglas":Paginator(qs,25).get_page(request.GET.get("page")),"estados":ReglaAprobacion.ESTADOS})
@login_required
@modulo_requerido("modulo_workflow")
def regla_editar(request,pk=None):
 perm="change_reglaaprobacion" if pk else "add_reglaaprobacion"
 if not request.user.has_perm(f"workflow.{perm}"):raise PermissionDenied
 obj=get_object_or_404(ReglaAprobacion,pk=pk,empresa=_empresa(request)) if pk else None
 if obj and obj.estado!="BORRADOR":raise PermissionDenied("Una regla activa no se edita.")
 form=ReglaForm(request.POST or None,instance=obj,empresa=_empresa(request))
 if request.method=="POST" and form.is_valid():
  if obj:
   saved=form.save(commit=False);saved.empresa=_empresa(request);saved.actualizado_por=request.user;saved.full_clean();saved.save()
  else:
   from .application.services import crear_regla;saved=crear_regla(context=_ctx(request),datos=form.cleaned_data)
  return redirect("workflow:regla_detalle",pk=saved.pk)
 return render(request,"workflow/form.html",{"form":form,"title":"Regla de aprobación"})
@login_required
@modulo_requerido("modulo_workflow","workflow.view_reglaaprobacion")
def regla_detalle(request,pk):
 r=get_object_or_404(ReglaAprobacion.objects.prefetch_related("condiciones","niveles__asignadores"),pk=pk,empresa=_empresa(request));errors=validar_regla(context=_ctx(request),regla_id=r.pk) if request.user.has_perm("workflow.validar_regla_aprobacion") else []
 return render(request,"workflow/regla_detalle.html",{"regla":r,"errores":errors,"condicion_form":CondicionForm(empresa=_empresa(request)),"nivel_form":NivelForm(empresa=_empresa(request)),"asignador_form":AsignadorForm(empresa=_empresa(request)),"motivo_form":MotivoForm()})
@login_required
@modulo_requerido("modulo_workflow")
def regla_accion(request,pk,accion):
 if request.method!="POST":raise PermissionDenied
 try:
  if accion=="activar":activar_regla(context=_ctx(request),regla_id=pk)
  elif accion=="retirar":retirar_regla(context=_ctx(request),regla_id=pk)
  elif accion=="versionar":return redirect("workflow:regla_detalle",pk=versionar_regla(context=_ctx(request),regla_id=pk).pk)
  else:raise PermissionDenied
  messages.success(request,"Acción aplicada.")
 except ValidationError as e:messages.error(request,str(e))
 return redirect("workflow:regla_detalle",pk=pk)
@login_required
@modulo_requerido("modulo_workflow")
def regla_agregar(request,pk,tipo,nivel_id=None):
 if request.method!="POST":raise PermissionDenied
 forms={"condicion":(CondicionForm,lambda d:agregar_condicion(context=_ctx(request),regla_id=pk,datos=d)),"nivel":(NivelForm,lambda d:agregar_nivel(context=_ctx(request),regla_id=pk,datos=d)),"asignador":(AsignadorForm,lambda d:configurar_asignador(context=_ctx(request),nivel_id=nivel_id,datos=d))};fc,service=forms[tipo];form=fc(request.POST,empresa=_empresa(request))
 if form.is_valid():service(form.cleaned_data);messages.success(request,"Configuración agregada.")
 else:messages.error(request,str(form.errors))
 return redirect("workflow:regla_detalle",pk=pk)
@login_required
@modulo_requerido("modulo_workflow","workflow.gestionar_suplencias_workflow")
def suplencias(request):
 form=SuplenciaForm(request.POST or None,empresa=_empresa(request))
 if request.method=="POST" and form.is_valid():
  crear_suplencia(context=_ctx(request),datos=form.cleaned_data);return redirect("workflow:suplencias")
 return render(request,"workflow/suplencias.html",{"form":form,"suplencias":SuplenciaAprobador.objects.filter(empresa=_empresa(request)).select_related("titular","suplente")})
@login_required
@modulo_requerido("modulo_workflow","workflow.view_tareas_workflow")
def bandeja(request):return render(request,"workflow/bandeja.html",{"tareas":tareas_usuario(empresa=_empresa(request),usuario=request.user),"completadas":DecisionAprobacion.objects.filter(empresa=_empresa(request),usuario_efectivo=request.user).order_by("-creada_en")[:50]})
@login_required
@modulo_requerido("modulo_workflow","workflow.view_instanciaworkflow")
def instancia_detalle(request,pk):
 obj=get_object_or_404(InstanciaWorkflow.objects.select_related("regla","solicitante"),pk=pk,empresa=_empresa(request));return render(request,"workflow/instancia.html",{"instancia":obj,"decisiones":obj.decisiones.select_related("usuario_efectivo","nivel_instancia").order_by("creada_en"),"decision_form":DecisionForm(initial={"idempotency_key":uuid4().hex}),"motivo_form":MotivoForm()})
@login_required
@modulo_requerido("modulo_workflow")
def decidir(request,pk,accion):
 if request.method!="POST":raise PermissionDenied
 form=DecisionForm(request.POST)
 if form.is_valid():
  try:{"aprobar":aprobar,"rechazar":rechazar,"devolver":devolver,"abstenerse":abstenerse}[accion](context=_ctx(request,form.cleaned_data["idempotency_key"]),instancia_id=pk,comentario=form.cleaned_data["comentario"],idempotency_key=form.cleaned_data["idempotency_key"]);messages.success(request,"Decisión registrada.")
  except ValidationError as e:messages.error(request,str(e))
 return redirect("workflow:instancia",pk=pk)
@login_required
@modulo_requerido("modulo_workflow","workflow.exportar_workflow")
def exportar(request):
 qs=instancias_empresa(empresa=_empresa(request));state=request.GET.get("estado");qs=qs.filter(estado=state) if state else qs;response=HttpResponse(content_type="text/csv; charset=utf-8");response["Content-Disposition"]='attachment; filename="workflow.csv"';w=csv.writer(response);w.writerow(["Referencia","Dominio","Tipo","Estado","Regla","Nivel","Inicio"])
 for x in qs:w.writerow([x.referencia_externa,x.dominio,x.tipo_documento,x.estado,x.regla.codigo,x.nivel_actual,x.iniciada_en])
 registrar_evento(empresa=_empresa(request),usuario=request.user,request=request,modulo="workflow",accion=EventoAuditoria.Accion.OTRO,descripcion="Exportación segura de workflow.",datos_nuevos={"filas":qs.count()});return response
@login_required
@modulo_requerido("modulo_workflow","workflow.view_instanciaworkflow")
def reportes(request):
 empresa=_empresa(request);instances=instancias_empresa(empresa=empresa);decisions=DecisionAprobacion.objects.filter(empresa=empresa);levels=NivelInstanciaWorkflow.objects.filter(empresa=empresa)
 return render(request,"workflow/reportes.html",{"por_estado":instances.values("estado").annotate(total=Count("id")),"por_regla":instances.values("regla__codigo").annotate(total=Count("id")).order_by("-total"),"decisiones_usuario":decisions.values("usuario_efectivo__username","decision").annotate(total=Count("id")).order_by("usuario_efectivo__username"),"rechazos":decisions.filter(decision="RECHAZAR").select_related("instancia","usuario_efectivo")[:50],"devoluciones":decisions.filter(decision="DEVOLVER").select_related("instancia","usuario_efectivo")[:50],"tiempos_nivel":levels.filter(completado_en__isnull=False,activado_en__isnull=False).annotate(duracion=ExpressionWrapper(F("completado_en")-F("activado_en"),output_field=DurationField())).values("numero").annotate(promedio=Avg("duracion")),"suplencias":SuplenciaAprobador.objects.filter(empresa=empresa).select_related("titular","suplente"),"bloqueadas":instances.filter(estado="EN_APROBACION").exclude(asignaciones__activa=True).distinct()})
