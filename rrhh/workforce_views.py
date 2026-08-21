import csv
from datetime import datetime
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.db import models,transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST
from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from conduces.services import obtener_empresa_usuario
from .models import (AsignacionTurno,CierreAsistencia,ContratoEmpleado,Empleado,HistorialLaboral,
 HoraExtra,IncidenciaAsistencia,NovedadTSS,RegistroAsistencia,ReingresoEmpleado)
from .workforce_forms import HoraExtraForm,IncidenciaForm,PoncheForm,ReingresoForm,TSSForm

def _e(r):return obtener_empresa_usuario(r)
def _audit(r,obj,descripcion,antes=None,nuevos=None):return registrar_evento(empresa=_e(r),usuario=r.user,request=r,objeto=obj,modulo="rrhh",accion=EventoAuditoria.Accion.EDITAR if antes else EventoAuditoria.Accion.CREAR,descripcion=descripcion,datos_anteriores=antes,datos_nuevos=nuevos)
def _calcular(registro):
 if registro.entrada and registro.salida and registro.salida>=registro.entrada:registro.horas_trabajadas=Decimal(str(round((registro.salida-registro.entrada).total_seconds()/3600,2)))
 asignacion=AsignacionTurno.objects.filter(empresa=registro.empresa,empleado=registro.empleado,desde__lte=registro.fecha).filter(models.Q(hasta__isnull=True)|models.Q(hasta__gte=registro.fecha)).select_related("turno__horario").first()
 if asignacion and registro.entrada:
  esperado=timezone.make_aware(datetime.combine(registro.fecha,asignacion.turno.horario.hora_entrada));registro.minutos_tardanza=max(0,int((registro.entrada-esperado).total_seconds()/60))
 return registro

@login_required
@permission_required("rrhh.view_registroasistencia",raise_exception=True)
def ponches(request):
 qs=RegistroAsistencia.objects.filter(empresa=_e(request)).select_related("empleado").order_by("-fecha","-pk");return render(request,"rrhh/workforce_list.html",{"titulo":"Asistencia y ponches","objetos":qs,"tipo":"ponches"})
@login_required
@transaction.atomic
def ponche_form(request,pk=None):
 obj=get_object_or_404(RegistroAsistencia,empresa=_e(request),pk=pk) if pk else None;perm="rrhh.change_registroasistencia" if obj else "rrhh.add_registroasistencia"
 if not request.user.has_perm(perm):return HttpResponse(status=403)
 antes={"entrada":str(obj.entrada),"salida":str(obj.salida),"estado":obj.estado} if obj else None;form=PoncheForm(request.POST or None,instance=obj,empresa=_e(request))
 if request.method=="POST" and form.is_valid():
  obj=form.save(commit=False);obj.empresa=_e(request);obj.corregido=bool(antes);_calcular(obj);obj.save();_audit(request,obj,"Ponche corregido." if antes else "Ponche registrado.",antes,{"entrada":str(obj.entrada),"salida":str(obj.salida),"horas":str(obj.horas_trabajadas)});HistorialLaboral.objects.create(empleado=obj.empleado,accion="PONCHE_CORREGIDO" if antes else "PONCHE",snapshot={"registro":obj.pk});messages.success(request,"Ponche guardado.");return redirect("rrhh:ponches")
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Corregir ponche" if obj else "Registrar ponche"})
@login_required
@permission_required("rrhh.add_incidenciaasistencia",raise_exception=True)
@transaction.atomic
def incidencia_crear(request):
 form=IncidenciaForm(request.POST or None,empresa=_e(request))
 if request.method=="POST" and form.is_valid():obj=form.save(commit=False);obj.empresa=_e(request);obj.save();_audit(request,obj,"Incidencia de asistencia registrada.");HistorialLaboral.objects.create(empleado=obj.registro.empleado,accion="INCIDENCIA_ASISTENCIA",snapshot={"incidencia":obj.pk,"tipo":obj.tipo});return redirect("rrhh:ponches")
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Registrar tardanza, ausencia o permiso"})
@login_required
@require_POST
@permission_required("rrhh.add_cierreasistencia",raise_exception=True)
@transaction.atomic
def cerrar_asistencia(request):
 desde=request.POST.get("desde");hasta=request.POST.get("hasta")
 if not desde or not hasta or desde>hasta:return HttpResponse("Rango inválido.",status=400)
 obj,creado=CierreAsistencia.objects.get_or_create(empresa=_e(request),desde=desde,hasta=hasta,defaults={"estado":"CERRADO","cerrado_por":request.user,"cerrado_en":timezone.now()})
 if not creado:return HttpResponse("El período ya fue cerrado.",status=400)
 RegistroAsistencia.objects.filter(empresa=_e(request),fecha__range=(desde,hasta)).update(estado="CERRADO")
 _audit(request,obj,"Período de asistencia cerrado.",nuevos={"desde":desde,"hasta":hasta})
 messages.success(request,"Período de asistencia cerrado.");return redirect("rrhh:ponches")
@login_required
@permission_required("rrhh.view_horaextra",raise_exception=True)
def horas_extra(request):return render(request,"rrhh/workforce_list.html",{"titulo":"Horas extra","objetos":HoraExtra.objects.filter(empresa=_e(request)).select_related("empleado").order_by("-fecha"),"tipo":"horas-extra"})
@login_required
@permission_required("rrhh.add_horaextra",raise_exception=True)
@transaction.atomic
def hora_extra_crear(request):
 form=HoraExtraForm(request.POST or None,empresa=_e(request))
 if request.method=="POST" and form.is_valid():obj=form.save(commit=False);obj.empresa=_e(request);obj.estado="PENDIENTE";obj.save();_audit(request,obj,"Horas extra registradas.");HistorialLaboral.objects.create(empleado=obj.empleado,accion="HORA_EXTRA",snapshot={"horas":str(obj.horas),"estado":obj.estado});return redirect("rrhh:horas_extra")
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Registrar horas extra"})
@login_required
@require_POST
@permission_required("rrhh.change_horaextra",raise_exception=True)
@transaction.atomic
def hora_extra_estado(request,pk):
 obj=get_object_or_404(HoraExtra,empresa=_e(request),pk=pk);nuevo=request.POST.get("estado","").upper()
 if nuevo not in {"APROBADA","RECHAZADA"} or obj.estado!="PENDIENTE":return HttpResponse("Transición no permitida.",status=400)
 anterior=obj.estado;obj.estado=nuevo;obj.aprobador=request.user;obj.save(update_fields=["estado","aprobador"]);_audit(request,obj,"Horas extra decididas.",{"estado":anterior},{"estado":nuevo});HistorialLaboral.objects.create(empleado=obj.empleado,accion="ESTADO_HORA_EXTRA",snapshot={"antes":anterior,"despues":nuevo});return redirect("rrhh:horas_extra")
@login_required
@permission_required("rrhh.view_novedadtss",raise_exception=True)
def tss(request):return render(request,"rrhh/workforce_list.html",{"titulo":"Novedades TSS","objetos":NovedadTSS.objects.filter(empresa=_e(request)).select_related("empleado").order_by("-fecha_efectiva"),"tipo":"tss"})
@login_required
@permission_required("rrhh.add_novedadtss",raise_exception=True)
@transaction.atomic
def tss_crear(request):
 form=TSSForm(request.POST or None,empresa=_e(request))
 if request.method=="POST" and form.is_valid():obj=form.save(commit=False);obj.empresa=_e(request);obj.save();_audit(request,obj,"Novedad TSS registrada.");HistorialLaboral.objects.create(empleado=obj.empleado,accion="NOVEDAD_TSS",snapshot={"tipo":obj.tipo,"periodo":obj.periodo});return redirect("rrhh:tss")
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Registrar novedad TSS"})
@login_required
@permission_required("rrhh.view_novedadtss",raise_exception=True)
def tss_exportar(request):
 response=HttpResponse(content_type="text/csv; charset=utf-8");response["Content-Disposition"]='attachment; filename="novedades_tss.csv"';response.write("\ufeff");w=csv.writer(response);w.writerow(["Período","Empleado","Tipo","Fecha efectiva","Salario reportable","Estado"])
 for x in NovedadTSS.objects.filter(empresa=_e(request)).select_related("empleado"):w.writerow([x.periodo,x.empleado.codigo,x.tipo,x.fecha_efectiva,x.salario_reportable,x.estado])
 return response
@login_required
@permission_required("rrhh.add_reingresoempleado",raise_exception=True)
@transaction.atomic
def reingresar(request,pk):
 emp=get_object_or_404(Empleado,empresa=_e(request),pk=pk);form=ReingresoForm(request.POST or None,empresa=_e(request),initial={"empleado":emp})
 if request.method=="POST" and form.is_valid():
  obj=form.save(commit=False);obj.empresa=_e(request);obj.empleado=emp;obj.save();emp.fecha_ingreso=obj.fecha_reingreso;emp.puesto=obj.puesto;emp.departamento=obj.departamento;emp.centro=obj.centro;emp.salario=obj.salario;emp.tipo_contrato=obj.tipo_contrato;emp.estado="ACTIVO";emp.save();ContratoEmpleado.objects.create(empresa=_e(request),empleado=emp,tipo=obj.tipo_contrato,inicio=obj.fecha_reingreso,salario=obj.salario,puesto=obj.puesto,estado="ACTIVO");HistorialLaboral.objects.create(empleado=emp,accion="REINGRESO",snapshot={"fecha":str(obj.fecha_reingreso),"salario":str(obj.salario)});_audit(request,emp,"Empleado reingresado.",nuevos={"fecha":str(obj.fecha_reingreso)});return redirect("rrhh:empleado_360",emp.pk)
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Reingreso de empleado","objeto":emp})
