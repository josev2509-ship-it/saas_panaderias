import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from conduces.services import obtener_empresa_usuario
from rrhh.models import HistorialLaboral,HoraExtra,SalidaEmpleado
from .forms import ConceptoForm,LiquidacionForm,PeriodoForm
from .models import ConceptoNomina,DetalleNominaEmpleado,LiquidacionLaboral,Nomina,PeriodoNomina,PrestacionLaboral
from .services import procesar_nomina

def _e(r):return obtener_empresa_usuario(r)
def _audit(r,obj,descripcion,antes=None,nuevos=None):return registrar_evento(empresa=_e(r),usuario=r.user,request=r,objeto=obj,modulo="nomina",accion=EventoAuditoria.Accion.EDITAR if antes else EventoAuditoria.Accion.CREAR,descripcion=descripcion,datos_anteriores=antes,datos_nuevos=nuevos)
@login_required
@permission_required("nomina.view_nomina",raise_exception=True)
def dashboard(request):
 periodos=PeriodoNomina.objects.filter(empresa=_e(request)).select_related("tipo").order_by("-desde");nominas=Nomina.objects.filter(empresa=_e(request)).select_related("periodo__tipo").order_by("-periodo__desde");return render(request,"nomina/dashboard.html",{"periodos":periodos,"nominas":nominas})
@login_required
@permission_required("nomina.add_periodonomina",raise_exception=True)
@transaction.atomic
def periodo_crear(request):
 form=PeriodoForm(request.POST or None,empresa=_e(request))
 if request.method=="POST" and form.is_valid():obj=form.save(commit=False);obj.empresa=_e(request);obj.save();_audit(request,obj,"Período de nómina creado.");return redirect("nomina:dashboard")
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Crear período de nómina"})
@login_required
@require_POST
@permission_required("nomina.add_nomina",raise_exception=True)
@transaction.atomic
def calcular(request,periodo_id):
 periodo=get_object_or_404(PeriodoNomina,empresa=_e(request),pk=periodo_id);nomina=procesar_nomina(empresa=_e(request),periodo=periodo,usuario=request.user);_audit(request,nomina,"Nómina calculada o recalculada.",nuevos={"total_neto":str(nomina.total_neto)});messages.success(request,"Nómina calculada.");return redirect("nomina:detalle",nomina.pk)
@login_required
@permission_required("nomina.view_nomina",raise_exception=True)
def detalle(request,pk):
 obj=get_object_or_404(Nomina.objects.select_related("periodo__tipo"),empresa=_e(request),pk=pk);return render(request,"nomina/detalle.html",{"nomina":obj,"detalles":obj.detalles.select_related("empleado").order_by("empleado__apellidos")})
@login_required
@require_POST
@permission_required("nomina.change_nomina",raise_exception=True)
@transaction.atomic
def estado(request,pk):
 obj=get_object_or_404(Nomina,empresa=_e(request),pk=pk);nuevo=request.POST.get("estado","").upper();trans={"CALCULADA":{"APROBADA"},"APROBADA":{"CERRADA","PAGADA"}}
 if nuevo not in trans.get(obj.estado,set()):return HttpResponse("Transición no permitida.",status=400)
 anterior=obj.estado;obj.estado=nuevo;obj.save(update_fields=["estado"]);_audit(request,obj,"Estado de nómina actualizado.",{"estado":anterior},{"estado":nuevo});return redirect("nomina:detalle",obj.pk)
@login_required
@permission_required("nomina.view_conceptonomina",raise_exception=True)
def conceptos(request):return render(request,"rrhh/workforce_list.html",{"titulo":"Conceptos de nómina","objetos":ConceptoNomina.objects.filter(empresa=_e(request)).order_by("codigo"),"tipo":"conceptos"})
@login_required
@permission_required("nomina.add_conceptonomina",raise_exception=True)
def concepto_crear(request):
 form=ConceptoForm(request.POST or None,empresa=_e(request))
 if request.method=="POST" and form.is_valid():obj=form.save(commit=False);obj.empresa=_e(request);obj.save();_audit(request,obj,"Concepto de nómina creado.");return redirect("nomina:conceptos")
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Crear concepto de nómina"})
@login_required
@permission_required("nomina.view_liquidacionlaboral",raise_exception=True)
def prestaciones(request):return render(request,"rrhh/workforce_list.html",{"titulo":"Prestaciones","objetos":LiquidacionLaboral.objects.filter(empresa=_e(request)).select_related("empleado").order_by("-fecha"),"tipo":"prestaciones"})
@login_required
@permission_required("nomina.add_liquidacionlaboral",raise_exception=True)
@transaction.atomic
def prestacion_crear(request):
 form=LiquidacionForm(request.POST or None,empresa=_e(request))
 if request.method=="POST" and form.is_valid():obj=form.save(commit=False);obj.empresa=_e(request);obj.save();HistorialLaboral.objects.create(empleado=obj.empleado,accion="PRESTACIONES",snapshot={"liquidacion":obj.pk,"total":str(obj.total)});_audit(request,obj,"Prestaciones registradas sin cálculo legal automático.");return redirect("nomina:prestacion_detalle",obj.pk)
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Registrar prestaciones"})
@login_required
@permission_required("nomina.view_liquidacionlaboral",raise_exception=True)
def prestacion_detalle(request,pk):
 obj=get_object_or_404(LiquidacionLaboral.objects.select_related("empleado"),empresa=_e(request),pk=pk);salida=SalidaEmpleado.objects.filter(empleado=obj.empleado).first();return render(request,"nomina/prestacion_detalle.html",{"obj":obj,"salida":salida,"desglose":obj.prestaciones.all()})
@login_required
@permission_required("nomina.view_nomina",raise_exception=True)
def exportar(request,pk):
 obj=get_object_or_404(Nomina,empresa=_e(request),pk=pk);response=HttpResponse(content_type="text/csv; charset=utf-8");response["Content-Disposition"]=f'attachment; filename="{obj.numero}.csv"';response.write("\ufeff");w=csv.writer(response);w.writerow(["Empleado","Ingresos","Deducciones","Aportes","Neto"])
 for d in obj.detalles.select_related("empleado"):w.writerow([d.empleado.codigo,d.ingresos,d.deducciones,d.aportes,d.neto])
 return response
