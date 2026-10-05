from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import models,transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from conduces.tenant_context import obtener_empresa_requerida
from documentos.forms import DocumentoForm
from documentos.models import Documento
from documentos.services import crear_documento_asociado
from nomina.models import DetalleNominaEmpleado,LiquidacionLaboral,Nomina,PrestamoEmpleado
from .forms import CapacitacionForm,ContratoForm,DepartamentoForm,DescripcionPuestoForm,DisciplinaForm,EmpleadoForm,EntidadFinancieraForm,LicenciaForm,LugarTrabajoForm,ParticipacionForm,PuestoForm,SalidaForm,SolicitudDocumentoForm,VacacionForm
from .models import AccionDisciplinaria,AusenciaEmpleado,Capacitacion,CentroTrabajo,ContratoEmpleado,Departamento,DescripcionPuesto,Empleado,EntidadFinancieraRRHH,HistorialLaboral,HoraExtra,IncidenciaAsistencia,LicenciaEmpleado,NovedadTSS,ParticipacionCapacitacion,Puesto,RegistroAsistencia,SaldoVacacion,SalidaEmpleado,SolicitudDocumentoRRHH,SolicitudVacacion
from .access import gestion_humana_requerida, tiene_autorizacion_gestion_humana

def _empresa(r):return getattr(r,"empresa_operativa",None) or obtener_empresa_requerida(r,permitir_soporte=True)
def _empleado(r,pk):return get_object_or_404(Empleado.objects.select_related("puesto","departamento","centro","supervisor"),pk=pk,empresa=_empresa(r))
def _audit(r,obj,accion,descripcion,antes=None,nuevos=None):return registrar_evento(empresa=_empresa(r),usuario=r.user,request=r,objeto=obj,modulo="rrhh",accion=accion,descripcion=descripcion,datos_anteriores=antes,datos_nuevos=nuevos)

@login_required
@gestion_humana_requerida("rrhh.view_empleado")
def dashboard(request):
 e=_empresa(request);h=timezone.localdate();lim=h+timedelta(days=45);empleados=Empleado.objects.filter(empresa=e)
 ultima_nomina=Nomina.objects.filter(empresa=e).order_by("-periodo__hasta").first()
 return render(request,"rrhh/dashboard.html",{"activos":empleados.filter(estado="ACTIVO").count(),"nomina_actual":ultima_nomina,"ausencias_hoy":AusenciaEmpleado.objects.filter(empresa=e,fecha=h).count(),"prestamos_activos":PrestamoEmpleado.objects.filter(empresa=e,estado="ACTIVO",saldo__gt=0).count(),"ingresos":empleados.filter(fecha_ingreso__year=h.year,fecha_ingreso__month=h.month).count(),"salidas":SalidaEmpleado.objects.filter(empresa=e,fecha_salida__year=h.year,fecha_salida__month=h.month).count(),"vacaciones":SolicitudVacacion.objects.filter(empresa=e,desde__range=(h,lim)).count(),"contratos":ContratoEmpleado.objects.filter(empresa=e,fin__range=(h,lim)).select_related("empleado"),"documentos":Documento.objects.filter(empresa=e,fecha_vencimiento__range=(h,lim),estado="ACTIVO"),"licencias":empleados.filter(vence_licencia__range=(h,lim)),"incidencias":AccionDisciplinaria.objects.filter(empresa=e,estado="ABIERTA").count(),"cursos":Capacitacion.objects.filter(empresa=e,inicio__range=(h,lim)).count()})

@login_required
@gestion_humana_requerida("rrhh.view_empleado")
def empleados(request):
 qs=Empleado.objects.filter(empresa=_empresa(request)).select_related("puesto","departamento","centro").order_by("apellidos","nombres");q=request.GET.get("q","").strip()
 if q:qs=qs.filter(models.Q(codigo__icontains=q)|models.Q(nombres__icontains=q)|models.Q(apellidos__icontains=q)|models.Q(identificacion__icontains=q)|models.Q(puesto__nombre__icontains=q)|models.Q(departamento__nombre__icontains=q)|models.Q(correo__icontains=q)|models.Q(telefono__icontains=q))
 return render(request,"rrhh/lista.html",{"titulo":"Empleados","objetos":qs,"tipo":"empleados","q":q})

@login_required
@gestion_humana_requerida("rrhh.view_empleado")
def reporte_empleados(request):
 import csv
 response=HttpResponse(content_type="text/csv; charset=utf-8");response["Content-Disposition"]='attachment; filename="empleados_rrhh.csv"';response.write("\ufeff");writer=csv.writer(response);writer.writerow(["Código","Nombre","Identificación","Departamento","Puesto","Ingreso","Estado"])
 def safe(value):
  value=str(value or "");return "'"+value if value[:1] in "=+-@" else value
 for x in Empleado.objects.filter(empresa=_empresa(request)).select_related("departamento","puesto").order_by("codigo"):writer.writerow([safe(x.codigo),safe(f"{x.nombres} {x.apellidos}"),safe(x.identificacion),safe(x.departamento.nombre),safe(x.puesto.nombre),x.fecha_ingreso,x.estado])
 return response

@login_required
@gestion_humana_requerida()
@transaction.atomic
def empleado_form(request,pk=None):
 obj=_empleado(request,pk) if pk else None;perm="rrhh.change_empleado" if obj else "rrhh.add_empleado"
 if not tiene_autorizacion_gestion_humana(request,perm):return HttpResponse(status=403)
 antes={"puesto":obj.puesto_id,"departamento":obj.departamento_id,"salario":str(obj.salario),"estado":obj.estado} if obj else None
 form=EmpleadoForm(request.POST or None,request.FILES or None,instance=obj,empresa=_empresa(request))
 if request.method=="POST" and form.is_valid():
  obj=form.save(commit=False);obj.empresa=_empresa(request)
  if not obj.pk:obj.codigo=Empleado.siguiente_codigo(obj.empresa)
  if form.cleaned_data.get("eliminar_foto") and obj.foto:obj.foto.delete(save=False);obj.foto=""
  obj.save();nuevos={"codigo":obj.codigo,"puesto":obj.puesto_id,"departamento":obj.departamento_id,"salario":str(obj.salario),"estado":obj.estado};HistorialLaboral.objects.create(empleado=obj,accion="ACTUALIZACION" if antes else "INGRESO",snapshot={"antes":antes,"despues":nuevos});_audit(request,obj,EventoAuditoria.Accion.EDITAR if antes else EventoAuditoria.Accion.CREAR,"Empleado actualizado." if antes else "Empleado creado.",antes,nuevos);messages.success(request,"Empleado guardado correctamente.");return redirect("rrhh:empleado_360",obj.pk)
 groups=[("Datos personales",("foto","nombres","apellidos","identificacion","fecha_nacimiento","sexo","estado_civil","nacionalidad","eliminar_foto")),("Contacto",("telefono","correo","direccion","contacto_emergencia")),("Datos laborales",("fecha_ingreso","departamento","puesto","supervisor","centro","tipo_contrato","salario","frecuencia_salario","frecuencia_pago","forma_pago","estado")),("Información bancaria",("banco","tipo_cuenta_bancaria","cuenta_bancaria_cifrada")),("Información adicional",("licencia_conducir","categoria_licencia","vence_licencia","observaciones"))]
 sections=[(title,[form[name] for name in names if name in form.fields]) for title,names in groups]
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Editar empleado" if obj else "Ingreso de empleado","objeto":obj,"form_sections":sections,"codigo_automatico":not obj})

@login_required
@gestion_humana_requerida("rrhh.view_empleado")
def empleado_360(request,pk):
 emp=_empleado(request,pk);e=_empresa(request);h=timezone.localdate();inicio=h.replace(day=1);ct=ContentType.objects.get_for_model(Empleado);saldo=SaldoVacacion.objects.filter(empleado=emp).first()
 from nomina.models import PrestamoEmpleado
 return render(request,"rrhh/empleado_360.html",{"empleado":emp,"antiguedad_dias":(h-emp.fecha_ingreso).days,"saldo":saldo,"horas_extra":HoraExtra.objects.filter(empresa=e,empleado=emp,fecha__gte=inicio).aggregate(v=Sum("horas"))["v"] or 0,"ausencias":AusenciaEmpleado.objects.filter(empresa=e,empleado=emp,fecha__gte=inicio).count(),"tardanzas":RegistroAsistencia.objects.filter(empresa=e,empleado=emp,fecha__gte=inicio,minutos_tardanza__gt=0).count(),"contratos":emp.contratos.order_by("-inicio"),"vacaciones":SolicitudVacacion.objects.filter(empresa=e,empleado=emp).order_by("-desde"),"licencias":LicenciaEmpleado.objects.filter(empresa=e,empleado=emp).order_by("-desde"),"ponches":RegistroAsistencia.objects.filter(empresa=e,empleado=emp).order_by("-fecha")[:30],"extras":HoraExtra.objects.filter(empresa=e,empleado=emp).order_by("-fecha"),"disciplinas":emp.acciones_disciplinarias.order_by("-fecha"),"cursos":emp.capacitaciones.select_related("capacitacion"),"documentos":Documento.objects.filter(empresa=e,content_type=ct,object_id=emp.pk),"prestamos":PrestamoEmpleado.objects.filter(empresa=e,empleado=emp).order_by("-fecha"),"prestaciones":LiquidacionLaboral.objects.filter(empresa=e,empleado=emp),"tss":NovedadTSS.objects.filter(empresa=e,empleado=emp),"historial":emp.historial.order_by("-fecha"),"auditoria":EventoAuditoria.objects.filter(empresa=e,content_type=ct,object_id=emp.pk)[:50],"nominas":DetalleNominaEmpleado.objects.filter(empleado=emp,nomina__empresa=e).select_related("nomina")[:24],"salida":SalidaEmpleado.objects.filter(empleado=emp).first()})

@login_required
@gestion_humana_requerida("rrhh.view_empleado")
def reportes(request):return render(request,"rrhh/reportes.html")

@login_required
@gestion_humana_requerida("rrhh.view_departamento")
def configuracion(request):return render(request,"rrhh/configuracion.html")

@login_required
@gestion_humana_requerida("rrhh.view_puesto")
def puestos_funciones(request):
 empresa=_empresa(request)
 return render(request,"rrhh/puestos_funciones.html",{"puestos":Puesto.objects.filter(empresa=empresa).count(),"funciones":DescripcionPuesto.objects.filter(empresa=empresa).count()})

@login_required
@gestion_humana_requerida("rrhh.view_puesto")
def puestos(request):
 return render(request,"rrhh/puestos_lista.html",{"objetos":Puesto.objects.filter(empresa=_empresa(request)).order_by("codigo","nombre")})

@login_required
@gestion_humana_requerida("rrhh.add_puesto")
@transaction.atomic
def puesto_crear(request):
 empresa=_empresa(request);form=PuestoForm(request.POST or None,empresa=empresa)
 if request.method=="POST" and form.is_valid():
  obj=form.save(commit=False);obj.empresa=empresa;obj.save();_audit(request,obj,EventoAuditoria.Accion.CREAR,"Puesto creado.",nuevos={"codigo":obj.codigo,"nombre":obj.nombre});messages.success(request,"Puesto creado correctamente.");return redirect("rrhh:puestos")
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Nuevo puesto","volver_url":reverse("rrhh:puestos")})

@login_required
@gestion_humana_requerida("rrhh.change_puesto")
@transaction.atomic
def puesto_editar(request,pk):
 empresa=_empresa(request);obj=get_object_or_404(Puesto,pk=pk,empresa=empresa);antes={"codigo":obj.codigo,"nombre":obj.nombre};form=PuestoForm(request.POST or None,instance=obj,empresa=empresa)
 if request.method=="POST" and form.is_valid():
  obj=form.save();_audit(request,obj,EventoAuditoria.Accion.EDITAR,"Puesto actualizado.",antes,{"codigo":obj.codigo,"nombre":obj.nombre});messages.success(request,"Puesto actualizado correctamente.");return redirect("rrhh:puestos")
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Editar puesto","volver_url":reverse("rrhh:puestos")})

@login_required
@gestion_humana_requerida("rrhh.change_puesto")
@require_POST
@transaction.atomic
def puesto_estado(request,pk):
 obj=get_object_or_404(Puesto,pk=pk,empresa=_empresa(request));anterior=obj.activo;obj.activo=not obj.activo;obj.save(update_fields=["activo"]);_audit(request,obj,EventoAuditoria.Accion.CAMBIAR_ESTADO,"Estado del puesto actualizado.",{"activo":anterior},{"activo":obj.activo});messages.success(request,"Estado del puesto actualizado.");return redirect("rrhh:puestos")

@login_required
@gestion_humana_requerida("rrhh.view_descripcionpuesto")
def funciones(request):
 objetos=DescripcionPuesto.objects.filter(empresa=_empresa(request)).select_related("puesto").order_by("puesto__codigo","-version")
 return render(request,"rrhh/funciones_lista.html",{"objetos":objetos})

def _funcion_form(request,obj=None):
 empresa=_empresa(request);form=DescripcionPuestoForm(request.POST or None,instance=obj,empresa=empresa);sin_puestos=obj is None and not Puesto.objects.filter(empresa=empresa,activo=True).exists()
 if request.method=="POST" and form.is_valid():
  registro=form.save(commit=False);registro.empresa=empresa;registro.save();_audit(request,registro,EventoAuditoria.Accion.EDITAR if obj else EventoAuditoria.Accion.CREAR,"Descripción de puesto actualizada." if obj else "Descripción de puesto creada.");messages.success(request,"Descripción de funciones guardada correctamente.");return redirect("rrhh:funciones")
 return render(request,"rrhh/funcion_form.html",{"form":form,"titulo":"Editar descripción de funciones" if obj else "Nueva descripción de funciones","sin_puestos":sin_puestos})

@login_required
@gestion_humana_requerida("rrhh.add_descripcionpuesto")
@transaction.atomic
def funcion_crear(request):return _funcion_form(request)

@login_required
@gestion_humana_requerida("rrhh.change_descripcionpuesto")
@transaction.atomic
def funcion_editar(request,pk):return _funcion_form(request,get_object_or_404(DescripcionPuesto,pk=pk,empresa=_empresa(request)))

@login_required
@gestion_humana_requerida("rrhh.change_descripcionpuesto")
@require_POST
@transaction.atomic
def funcion_estado(request,pk):
 obj=get_object_or_404(DescripcionPuesto,pk=pk,empresa=_empresa(request));anterior=obj.activa;obj.activa=not obj.activa;obj.save(update_fields=["activa"]);_audit(request,obj,EventoAuditoria.Accion.CAMBIAR_ESTADO,"Estado de la descripción de puesto actualizado.",{"activa":anterior},{"activa":obj.activa});messages.success(request,"Estado de la descripción actualizado.");return redirect("rrhh:funciones")

@login_required
@gestion_humana_requerida("rrhh.view_empleado")
def documentos_centro(request):
 e=_empresa(request);form=SolicitudDocumentoForm(request.POST or None,empresa=e)
 if request.method=="POST" and form.is_valid():
  obj=form.save(commit=False);obj.empresa=e;obj.version=SolicitudDocumentoRRHH.objects.filter(empresa=e,empleado=obj.empleado,tipo=obj.tipo).count()+1;obj.numero=f"RRHH-{obj.tipo}-{obj.empleado.codigo}-V{obj.version:02d}";obj.snapshot={"empleado":str(obj.empleado),"puesto":obj.empleado.puesto.nombre,"departamento":obj.empleado.departamento.nombre,"lugar_trabajo":obj.empleado.centro.nombre,"entidad":obj.entidad_financiera.nombre if obj.entidad_financiera else "","destinatario":obj.destinatario,"pais":obj.pais_destino,"proposito":obj.proposito};obj.save();_audit(request,obj,EventoAuditoria.Accion.CREAR,"Solicitud documental RRHH creada.",nuevos=obj.snapshot);return redirect(f"{request.path}?solicitud={obj.pk}")
 solicitud=None
 if request.GET.get("solicitud"):solicitud=get_object_or_404(SolicitudDocumentoRRHH.objects.select_related("empleado","entidad_financiera"),pk=request.GET["solicitud"],empresa=e)
 return render(request,"rrhh/documentos.html",{"form":form,"solicitud":solicitud,"recientes":SolicitudDocumentoRRHH.objects.filter(empresa=e).select_related("empleado").order_by("-pk")[:12]})

MAPPING={"departamentos":(Departamento,DepartamentoForm),"lugares-trabajo":(CentroTrabajo,LugarTrabajoForm),"entidades-financieras":(EntidadFinancieraRRHH,EntidadFinancieraForm),"contratos":(ContratoEmpleado,ContratoForm),"funciones":(DescripcionPuesto,DescripcionPuestoForm),"vacaciones":(SolicitudVacacion,VacacionForm),"licencias":(LicenciaEmpleado,LicenciaForm),"amonestaciones":(AccionDisciplinaria,DisciplinaForm),"cursos":(Capacitacion,CapacitacionForm),"salidas":(SalidaEmpleado,SalidaForm)}
@login_required
@gestion_humana_requerida()
def recurso_lista(request,recurso):
 if recurso not in MAPPING:return HttpResponse(status=404)
 model,_=MAPPING[recurso]
 if not tiene_autorizacion_gestion_humana(request,f"rrhh.view_{model._meta.model_name}"):return HttpResponse(status=403)
 return render(request,"rrhh/lista.html",{"titulo":recurso.title(),"objetos":model.objects.filter(empresa=_empresa(request)).order_by("-pk")[:200],"tipo":recurso})
@login_required
@gestion_humana_requerida()
@transaction.atomic
def recurso_crear(request,recurso):
 if recurso not in MAPPING:return HttpResponse(status=404)
 model,form_class=MAPPING[recurso]
 if not tiene_autorizacion_gestion_humana(request,f"rrhh.add_{model._meta.model_name}"):return HttpResponse(status=403)
 empresa=_empresa(request)
 form=form_class(request.POST or None,empresa=empresa,initial={"empleado":request.GET.get("empleado")})
 if request.method=="POST" and form.is_valid():
  obj=form.save(commit=False);obj.empresa=empresa;obj.save();emp=getattr(obj,"empleado",None)
  if isinstance(obj,SalidaEmpleado):emp.estado="INACTIVO";emp.save(update_fields=["estado"])
  if emp:HistorialLaboral.objects.create(empleado=emp,accion=recurso.upper(),snapshot={"id":obj.pk,"estado":getattr(obj,"estado","")})
  _audit(request,obj,EventoAuditoria.Accion.CREAR,f"Registro RRHH creado: {recurso}.");messages.success(request,"Registro creado correctamente.");return redirect("rrhh:empleado_360",emp.pk) if emp else redirect("rrhh:recurso_lista",recurso)
 return render(request,"rrhh/form.html",{"form":form,"titulo":f"Nuevo registro: {recurso}"})

@login_required
@gestion_humana_requerida()
@require_POST
@transaction.atomic
def recurso_estado(request,recurso,pk):
 if recurso not in MAPPING:return HttpResponse(status=404)
 model,_=MAPPING[recurso]
 if not tiene_autorizacion_gestion_humana(request,f"rrhh.change_{model._meta.model_name}"):return HttpResponse(status=403)
 obj=get_object_or_404(model,pk=pk,empresa=_empresa(request));nuevo=request.POST.get("estado","").strip().upper()
 permitidos={"BORRADOR","ENVIADA","APROBADA","RECHAZADA","ACTIVO","VENCIDO","CERRADA","ANULADA","FINALIZADA"}
 if nuevo not in permitidos:return HttpResponse("Estado no permitido.",status=400)
 anterior=getattr(obj,"estado","");obj.estado=nuevo;obj.save(update_fields=["estado"]);emp=getattr(obj,"empleado",None)
 if emp:HistorialLaboral.objects.create(empleado=emp,accion=f"ESTADO_{recurso.upper()}",snapshot={"antes":anterior,"despues":nuevo})
 _audit(request,obj,EventoAuditoria.Accion.CAMBIAR_ESTADO,f"Estado de {recurso}: {anterior} → {nuevo}.",{"estado":anterior},{"estado":nuevo});messages.success(request,"Estado actualizado.");return redirect("rrhh:empleado_360",emp.pk) if emp else redirect("rrhh:recurso_lista",recurso)

@login_required
@gestion_humana_requerida("documentos.add_documento")
@transaction.atomic
def documento_cargar(request,pk):
 emp=_empleado(request,pk);form=DocumentoForm(request.POST or None,request.FILES or None,empresa=_empresa(request))
 if request.method=="POST" and form.is_valid():
  data=form.cleaned_data.copy();archivo=data.pop("archivo");crear_documento_asociado(empresa=_empresa(request),objeto=emp,archivo=archivo,usuario=request.user,request=request,**data);HistorialLaboral.objects.create(empleado=emp,accion="DOCUMENTO",snapshot={"titulo":data["titulo"]});messages.success(request,"Documento cargado y auditado.");return redirect("rrhh:empleado_360",emp.pk)
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Cargar documento","objeto":emp})

@login_required
@gestion_humana_requerida("rrhh.add_participacioncapacitacion")
@transaction.atomic
def curso_asignar(request,pk):
 emp=_empleado(request,pk);form=ParticipacionForm(request.POST or None,empresa=_empresa(request))
 if request.method=="POST" and form.is_valid():
  obj=form.save(commit=False);obj.empleado=emp;obj.save();HistorialLaboral.objects.create(empleado=emp,accion="CURSO",snapshot={"capacitacion":obj.capacitacion_id,"resultado":obj.resultado});_audit(request,emp,EventoAuditoria.Accion.EDITAR,"Curso asignado al empleado.",nuevos={"capacitacion":obj.capacitacion_id});messages.success(request,"Curso asignado.");return redirect("rrhh:empleado_360",emp.pk)
 return render(request,"rrhh/form.html",{"form":form,"titulo":"Asignar curso","objeto":emp})
