import csv
from datetime import timedelta
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.paginator import Paginator
from django.db.models import Q,Sum,Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.utils import timezone
from django.views.decorators.http import require_POST

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.application.crm import *
from comercial.domain.crm_events import ExportacionCRMGenerada
from comercial.forms import ProspectoForm,OportunidadForm,ActividadComercialForm
from comercial.models import Prospecto,OportunidadComercial,ActividadComercial,VendedorComercial
from comercial.selectors_crm import *
from conduces.services import obtener_empresa_usuario
from core.application.event_bus import event_bus
from core.application.operation_context import OperationContext

def _empresa(request):
    e=obtener_empresa_usuario(request)
    if not e:raise PermissionDenied
    return e
def _context(request,e):return OperationContext(empresa=e,usuario=request.user,request=request,clave_idempotente=request.headers.get("Idempotency-Key",""))
def _filtros(qs,request,campos):
    for campo in campos:
        valor=request.GET.get(campo,"")
        if valor:qs=qs.filter(**{campo:valor})
    q=request.GET.get("q","").strip()
    if q:
        if qs.model is Prospecto:qs=qs.filter(Q(numero__icontains=q)|Q(nombre__icontains=q)|Q(nombre_comercial__icontains=q)|Q(correo__icontains=q))
        elif qs.model is OportunidadComercial:qs=qs.filter(Q(numero__icontains=q)|Q(titulo__icontains=q)|Q(descripcion__icontains=q))
        else:qs=qs.filter(Q(asunto__icontains=q)|Q(descripcion__icontains=q))
    return qs

@login_required
def dashboard(request):
    e=_empresa(request);resumen=resumen_crm(e);pipe=list(pipeline(e));proximas=actividades_pendientes(e).filter(fecha_inicio__gte=timezone.now())[:8];vencidas=actividades_vencidas(e)[:8];estancadas=oportunidades_estancadas(e)[:8]
    return render(request,"comercial/crm/dashboard.html",{"empresa":e,"resumen":resumen,"pipeline":pipe,"proximas":proximas,"vencidas":vencidas,"estancadas":estancadas})

@login_required
def prospectos_lista(request):
    e=_empresa(request);qs=_filtros(prospectos(e),request,("estado","fuente","vendedor","equipo","zona"));return render(request,"comercial/crm/lista.html",{"empresa":e,"pagina":Paginator(qs,25).get_page(request.GET.get("page")),"titulo":"Prospectos","tipo":"prospecto","tipo_plural":"prospectos","estados":Prospecto.Estado.choices,"vendedores":VendedorComercial.objects.filter(empresa=e,activo=True)})
@login_required
def prospecto_detalle(request,pk):
    e=_empresa(request);obj=get_object_or_404(prospectos(e),pk=pk);return render(request,"comercial/crm/detalle.html",{"empresa":e,"objeto":obj,"tipo":"prospecto","actividades":obj.actividades.select_related("responsable")[:12],"historial":obj.historial_estados.select_related("usuario")[:15],"oportunidades":obj.oportunidades.all()[:10]})
@login_required
def prospecto_form(request,pk=None):
    e=_empresa(request);obj=get_object_or_404(Prospecto,empresa=e,pk=pk) if pk else None;perm=f"comercial.{'change' if obj else 'add'}_prospecto"
    if not request.user.has_perm(perm):raise PermissionDenied
    form=ProspectoForm(request.POST or None,instance=obj,empresa=e)
    if request.method=="POST" and form.is_valid():
        try:item=actualizar_prospecto(context=_context(request,e),pk=obj.pk,datos=form.cleaned_data) if obj else crear_prospecto(context=_context(request,e),datos=form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:return redirect("comercial:prospecto_detalle",pk=item.pk)
    return render(request,"comercial/crm/form.html",{"empresa":e,"form":form,"titulo":"Prospecto"})
@require_POST
@login_required
def prospecto_accion(request,pk,accion):
    c=_context(request,_empresa(request));motivo=request.POST.get("motivo","")
    if accion=="contactar":contactar_prospecto(context=c,pk=pk)
    elif accion=="calificar":calificar_prospecto(context=c,pk=pk)
    elif accion=="no-calificar":no_calificar_prospecto(context=c,pk=pk,motivo=motivo)
    elif accion=="descartar":descartar_prospecto(context=c,pk=pk,motivo=motivo)
    elif accion=="convertir":convertir_prospecto_a_cliente(context=c,pk=pk)
    else:raise PermissionDenied
    messages.success(request,"Acción aplicada.");return redirect("comercial:prospecto_detalle",pk=pk)

@login_required
def oportunidades_lista(request):
    e=_empresa(request);qs=_filtros(oportunidades(e),request,("etapa","vendedor","equipo","segmento","moneda"));return render(request,"comercial/crm/lista.html",{"empresa":e,"pagina":Paginator(qs,25).get_page(request.GET.get("page")),"titulo":"Oportunidades","tipo":"oportunidad","tipo_plural":"oportunidades","estados":OportunidadComercial.Etapa.choices,"vendedores":VendedorComercial.objects.filter(empresa=e,activo=True)})
@login_required
def oportunidad_detalle(request,pk):
    e=_empresa(request);obj=get_object_or_404(oportunidades(e),pk=pk);return render(request,"comercial/crm/detalle.html",{"empresa":e,"objeto":obj,"tipo":"oportunidad","etapas":OportunidadComercial.Etapa.choices,"actividades":obj.actividades.select_related("responsable")[:12],"historial":obj.historial_etapas.select_related("usuario")[:15]})
@login_required
def oportunidad_form(request,pk=None):
    e=_empresa(request);obj=get_object_or_404(OportunidadComercial,empresa=e,pk=pk) if pk else None;perm=f"comercial.{'change' if obj else 'add'}_oportunidadcomercial"
    if not request.user.has_perm(perm):raise PermissionDenied
    form=OportunidadForm(request.POST or None,instance=obj,empresa=e)
    if request.method=="POST" and form.is_valid():
        try:item=actualizar_oportunidad(context=_context(request,e),pk=obj.pk,datos=form.cleaned_data) if obj else crear_oportunidad(context=_context(request,e),datos=form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:return redirect("comercial:oportunidad_detalle",pk=item.pk)
    return render(request,"comercial/crm/form.html",{"empresa":e,"form":form,"titulo":"Oportunidad"})
@require_POST
@login_required
def oportunidad_accion(request,pk,accion):
    c=_context(request,_empresa(request));motivo=request.POST.get("motivo","")
    if accion=="etapa":cambiar_etapa_oportunidad(context=c,pk=pk,etapa=request.POST.get("etapa"),motivo=motivo)
    elif accion=="ganar":marcar_oportunidad_ganada(context=c,pk=pk)
    elif accion=="perder":marcar_oportunidad_perdida(context=c,pk=pk,motivo=motivo)
    elif accion=="cancelar":cancelar_oportunidad(context=c,pk=pk,motivo=motivo)
    else:raise PermissionDenied
    messages.success(request,"Etapa actualizada.");return redirect("comercial:oportunidad_detalle",pk=pk)
@login_required
def pipeline_view(request):
    e=_empresa(request);qs=_filtros(oportunidades(e),request,("vendedor","equipo","moneda"));columnas=[(etapa,label,qs.filter(etapa=etapa),qs.filter(etapa=etapa).aggregate(total=Sum("monto_estimado"),ponderado=Sum("monto_ponderado"))) for etapa,label in OportunidadComercial.Etapa.choices];return render(request,"comercial/crm/pipeline.html",{"empresa":e,"columnas":columnas})

@login_required
def actividades_lista(request):
    e=_empresa(request);qs=_filtros(actividades(e),request,("estado","tipo","responsable","prioridad"));return render(request,"comercial/crm/lista.html",{"empresa":e,"pagina":Paginator(qs,25).get_page(request.GET.get("page")),"titulo":"Actividades","tipo":"actividad","tipo_plural":"actividades","estados":ActividadComercial.ESTADOS})
@login_required
def actividad_detalle(request,pk):
    e=_empresa(request);obj=get_object_or_404(actividades(e),pk=pk);return render(request,"comercial/crm/detalle.html",{"empresa":e,"objeto":obj,"tipo":"actividad","historial":obj.historial.select_related("usuario")[:15]})
@login_required
def actividad_form(request,pk=None):
    e=_empresa(request);obj=get_object_or_404(ActividadComercial,empresa=e,pk=pk) if pk else None;perm=f"comercial.{'change' if obj else 'add'}_actividadcomercial"
    if not request.user.has_perm(perm):raise PermissionDenied
    form=ActividadComercialForm(request.POST or None,instance=obj,empresa=e)
    if request.method=="POST" and form.is_valid():
        try:item=actualizar_actividad(context=_context(request,e),pk=obj.pk,datos=form.cleaned_data) if obj else crear_actividad(context=_context(request,e),datos=form.cleaned_data)
        except ValidationError as exc:form.add_error(None,exc)
        else:return redirect("comercial:actividad_detalle",pk=item.pk)
    return render(request,"comercial/crm/form.html",{"empresa":e,"form":form,"titulo":"Actividad comercial"})
@require_POST
@login_required
def actividad_accion(request,pk,accion):
    c=_context(request,_empresa(request))
    if accion=="iniciar":iniciar_actividad(context=c,pk=pk)
    elif accion=="completar":completar_actividad(context=c,pk=pk,resultado=request.POST.get("resultado",""))
    elif accion=="cancelar":cancelar_actividad(context=c,pk=pk)
    elif accion=="reprogramar":
        from django.utils.dateparse import parse_datetime
        reprogramar_actividad(context=c,pk=pk,fecha_inicio=parse_datetime(request.POST.get("fecha_inicio","")),fecha_fin=parse_datetime(request.POST.get("fecha_fin","")) if request.POST.get("fecha_fin") else None)
    else:raise PermissionDenied
    return redirect("comercial:actividad_detalle",pk=pk)
@login_required
def agenda_view(request,vista="semana"):
    e=_empresa(request);hoy=timezone.localdate();desde=hoy if vista=="dia" else hoy-timedelta(days=hoy.weekday()) if vista=="semana" else hoy.replace(day=1);hasta=desde if vista=="dia" else desde+timedelta(days=6) if vista=="semana" else (desde+timedelta(days=32)).replace(day=1)-timedelta(days=1);items=agenda(e,desde,hasta,request.user if request.GET.get("mias") else None);return render(request,"comercial/crm/agenda.html",{"empresa":e,"actividades":items,"desde":desde,"hasta":hasta,"vista":vista})

@require_POST
@login_required
def accion_masiva(request,tipo,accion):
    e=_empresa(request);ids=[int(x) for x in request.POST.getlist("seleccion") if x.isdigit()];c=_context(request,e)
    if len(ids)>200:raise ValidationError("Máximo 200 registros por operación.")
    if accion=="reasignar" and tipo in ("prospectos","oportunidades"):
        vendedor=get_object_or_404(VendedorComercial,empresa=e,pk=request.POST.get("vendedor"))
        for pk in ids:(reasignar_prospecto if tipo=="prospectos" else reasignar_oportunidad)(context=c,pk=pk,vendedor=vendedor)
    elif accion=="completar" and tipo=="actividades":
        for pk in ids:completar_actividad(context=c,pk=pk,resultado=request.POST.get("resultado","Completada en acción masiva"))
    elif accion=="prioridad" and tipo=="actividades":
        prioridad=request.POST.get("prioridad")
        if prioridad not in dict(ActividadComercial.PRIORIDADES):raise ValidationError("Prioridad inválida.")
        for pk in ids:actualizar_actividad(context=c,pk=pk,datos={"prioridad":prioridad})
    elif accion=="seguimiento" and tipo in ("prospectos","oportunidades"):
        for pk in ids:
            datos={"tipo":"SEGUIMIENTO","asunto":request.POST.get("asunto","Seguimiento comercial"),"responsable":request.user,"fecha_inicio":timezone.now()+timedelta(days=1)}
            if tipo=="prospectos":datos["prospecto"]=get_object_or_404(Prospecto,empresa=e,pk=pk)
            else:datos["oportunidad"]=get_object_or_404(OportunidadComercial,empresa=e,pk=pk)
            crear_actividad(context=c,datos=datos)
    elif accion=="exportar":
        model={"prospectos":Prospecto,"oportunidades":OportunidadComercial,"actividades":ActividadComercial}[tipo];qs=model.objects.filter(empresa=e,pk__in=ids);r=HttpResponse(content_type="text/csv; charset=utf-8");r["Content-Disposition"]='attachment; filename="crm-seleccion.csv"';w=csv.writer(r);w.writerow(["ID","Referencia","Estado"])
        for obj in qs:w.writerow([obj.pk,getattr(obj,"numero",getattr(obj,"asunto","")),getattr(obj,"estado",getattr(obj,"etapa",""))])
        registrar_evento(empresa=e,usuario=request.user,request=request,modulo="crm",accion=EventoAuditoria.Accion.OTRO,descripcion="Selección CRM exportada.",datos_nuevos={"tipo":tipo,"cantidad":qs.count()});return r
    else:raise PermissionDenied
    registrar_evento(empresa=e,usuario=request.user,request=request,modulo="crm",accion=EventoAuditoria.Accion.OTRO,descripcion=f"Acción masiva CRM {accion}.",datos_nuevos={"tipo":tipo,"cantidad":len(ids)});return redirect("comercial:crm_dashboard")

def _rows(e,tipo):
    if tipo=="prospectos":return ([o.numero,o.nombre_comercial or o.nombre,o.estado,o.correo] for o in prospectos(e))
    if tipo=="oportunidades":return ([o.numero,o.titulo,o.etapa,str(o.monto_estimado),str(o.monto_ponderado)] for o in oportunidades(e))
    return ([str(o.pk),o.asunto,o.tipo,o.estado,o.fecha_inicio.isoformat()] for o in actividades(e))
@login_required
def reportes(request):
    e=_empresa(request);p=prospectos(e);o=oportunidades(e);a=actividades(e);grupos={"Prospectos por estado":p.values("estado").annotate(cantidad=Count("id")),"Prospectos por fuente":p.values("fuente__nombre").annotate(cantidad=Count("id")),"Prospectos por vendedor":p.values("vendedor__nombre").annotate(cantidad=Count("id")),"Oportunidades por etapa":o.values("etapa").annotate(cantidad=Count("id"),monto=Sum("monto_estimado")),"Oportunidades por vendedor":o.values("vendedor__nombre").annotate(cantidad=Count("id"),monto=Sum("monto_estimado")),"Oportunidades por segmento":o.values("segmento__nombre").annotate(cantidad=Count("id"),monto=Sum("monto_estimado")),"Actividades por tipo":a.values("tipo").annotate(cantidad=Count("id")),"Actividades por responsable":a.values("responsable__username").annotate(cantidad=Count("id")),"Motivos de pérdida":o.filter(etapa="PERDIDA").values("motivo_perdida").annotate(cantidad=Count("id"))};return render(request,"comercial/crm/reportes.html",{"empresa":e,"resumen":resumen_crm(e),"pipeline":pipeline(e),"grupos":grupos})
@login_required
def exportar(request,tipo,formato):
    e=_empresa(request);perm={"prospectos":"exportar_prospecto","oportunidades":"exportar_oportunidad"}.get(tipo,"view_actividadcomercial")
    if not request.user.has_perm(f"comercial.{perm}"):raise PermissionDenied
    rows=list(_rows(e,tipo));headers={"prospectos":["Número","Nombre","Estado","Correo"],"oportunidades":["Número","Título","Etapa","Monto","Ponderado"],"actividades":["ID","Asunto","Tipo","Estado","Inicio"]}[tipo]
    registrar_evento(empresa=e,usuario=request.user,request=request,modulo="crm",accion=EventoAuditoria.Accion.OTRO,descripcion=f"Exportación CRM {tipo} {formato}.",datos_nuevos={"formato":formato,"cantidad":len(rows)})
    event_bus.publish(ExportacionCRMGenerada(empresa_id=e.pk,usuario_id=request.user.pk,agregado_tipo="comercial.CRM",agregado_id=tipo,referencia=formato.upper(),clave_idempotente=f"crm-export:{e.pk}:{tipo}:{formato}:{request.headers.get('X-Request-ID','request')}"[:180],payload={"schema_version":1,"empresa_id":e.pk,"tipo":tipo,"formato":formato,"cantidad":len(rows)}))
    if formato=="csv":
        r=HttpResponse(content_type="text/csv; charset=utf-8");r["Content-Disposition"]=f'attachment; filename="crm-{tipo}.csv"';w=csv.writer(r);w.writerow(headers)
        for row in rows:w.writerow([("'"+v) if isinstance(v,str) and v[:1] in "=+-@" else v for v in row])
        return r
    if formato=="xlsx":
        from openpyxl import Workbook
        wb=Workbook();ws=wb.active;ws.title="CRM";ws.append(headers)
        for row in rows:ws.append(row)
        b=BytesIO();wb.save(b);r=HttpResponse(b.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");r["Content-Disposition"]=f'attachment; filename="crm-{tipo}.xlsx"';return r
    if formato=="pdf":
        from reportlab.pdfgen.canvas import Canvas
        b=BytesIO();pdf=Canvas(b);y=800;pdf.drawString(40,y,f"CRM - {tipo} - {e}");y-=25
        for row in rows:
            pdf.drawString(40,y," | ".join(str(v)[:35] for v in row));y-=16
            if y<50:pdf.showPage();y=800
        pdf.save();r=HttpResponse(b.getvalue(),content_type="application/pdf");r["Content-Disposition"]=f'attachment; filename="crm-{tipo}.pdf"';return r
    return render(request,"comercial/crm/impresion.html",{"empresa":e,"headers":headers,"rows":rows,"titulo":tipo.title()})
