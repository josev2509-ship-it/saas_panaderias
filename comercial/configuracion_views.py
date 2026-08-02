import csv
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.api.configuracion import validar_empresa_lista_para_vender
from comercial.application.configuracion import crear_catalogo, editar_catalogo, inactivar_catalogo, crear_politica, activar_politica
from comercial.application.configuracion_operativa import TIPOS_SECUENCIA, configurar_secuencia, validar_readiness, versionar_politica
from comercial.forms import ConfiguracionComercialForm, FiltroReporteComercialForm, SecuenciaComercialForm, catalogo_form_factory, politica_form_factory
from comercial.models import *
from conduces.services import obtener_empresa_usuario
from core.application.operation_context import OperationContext

CATALOGOS={m._meta.model_name:m for m in (CanalVenta,SegmentoCliente,ClasificacionCliente,TipoCliente,TipoEntrega,PrioridadComercial,MotivoComercial,FuenteProspecto,EquipoComercial,VendedorComercial,ZonaComercial,RutaComercial)}
POLITICAS={m._meta.model_name:m for m in (PoliticaCredito,PoliticaDescuento,PoliticaEntrega,PoliticaFacturacion,PoliticaDevolucion,PoliticaComision)}

def _empresa(request):
    empresa=obtener_empresa_usuario(request)
    if not empresa:raise PermissionDenied("El usuario no tiene empresa asociada.")
    return empresa

def _context(request,empresa):
    return OperationContext(empresa=empresa,usuario=request.user,request=request,clave_idempotente=request.headers.get("Idempotency-Key",""))

@login_required
def dashboard(request):
    empresa=_empresa(request);cfg=ConfiguracionComercialEmpresa.objects.filter(empresa=empresa).first();readiness=validar_empresa_lista_para_vender(empresa=empresa)
    conteos=[{"nombre":m._meta.verbose_name_plural.title(),"tipo":tipo,"total":m.objects.filter(empresa=empresa).count()} for tipo,m in CATALOGOS.items()]
    recientes=EventoAuditoria.objects.filter(empresa=empresa,modulo="comercial")[:8]
    return render(request,"comercial/configuracion/dashboard.html",{"empresa":empresa,"configuracion":cfg,"readiness":readiness,"conteos":conteos,"recientes":recientes,"secuencias":SecuenciaDocumento.objects.filter(empresa=empresa).count(),"politicas":sum(m.objects.filter(empresa=empresa).count() for m in POLITICAS.values())})

@login_required
@permission_required("comercial.change_configuracioncomercialempresa",raise_exception=True)
def configuracion_editar(request):
    empresa=_empresa(request);obj,_=ConfiguracionComercialEmpresa.objects.get_or_create(empresa=empresa,defaults={"creado_por":request.user});form=ConfiguracionComercialForm(request.POST or None,instance=obj,empresa=empresa)
    if request.method=="POST" and form.is_valid():
        item=form.save(commit=False);item.empresa=empresa;item.actualizado_por=request.user;item.version+=1;item.save();registrar_evento(empresa=empresa,usuario=request.user,request=request,objeto=item,modulo="comercial",accion=EventoAuditoria.Accion.EDITAR,descripcion="Configuración comercial actualizada.");messages.success(request,"Configuración guardada.");return redirect("comercial:configuracion_dashboard")
    return render(request,"comercial/configuracion/form.html",{"form":form,"titulo":"Configuración comercial"})

@login_required
def catalogo_lista(request,tipo):
    empresa=_empresa(request);model=CATALOGOS[tipo];qs=model.objects.filter(empresa=empresa)
    estado=request.GET.get("estado");qs=qs.filter(activo=estado=="activo") if estado in ("activo","inactivo") else qs
    return render(request,"comercial/configuracion/lista.html",{"objetos":Paginator(qs,25).get_page(request.GET.get("page")),"tipo":tipo,"titulo":model._meta.verbose_name_plural.title(),"es_politica":False})

@login_required
def catalogo_detalle(request,tipo,pk):
    obj=get_object_or_404(CATALOGOS[tipo],pk=pk,empresa=_empresa(request));return render(request,"comercial/configuracion/detalle.html",{"objeto":obj,"tipo":tipo,"titulo":obj.nombre})

@login_required
def catalogo_editar(request,tipo,pk=None):
    empresa=_empresa(request);model=CATALOGOS[tipo];obj=get_object_or_404(model,pk=pk,empresa=empresa) if pk else None;perm=f"comercial.{'change' if obj else 'add'}_{model._meta.model_name}"
    if not request.user.has_perm(perm):raise PermissionDenied
    form=catalogo_form_factory(model)(request.POST or None,instance=obj,empresa=empresa)
    if request.method=="POST" and form.is_valid():
        datos=form.cleaned_data;context=_context(request,empresa);guardado=editar_catalogo(context=context,tipo=model.__name__,pk=obj.pk,datos=datos) if obj else crear_catalogo(context=context,tipo=model.__name__,datos=datos);messages.success(request,"Registro guardado.");return redirect("comercial:catalogo_detalle",tipo=tipo,pk=guardado.pk)
    return render(request,"comercial/configuracion/form.html",{"form":form,"titulo":model._meta.verbose_name.title()})

@require_POST
@login_required
def catalogo_estado(request,tipo,pk):
    empresa=_empresa(request);model=CATALOGOS[tipo];obj=get_object_or_404(model,pk=pk,empresa=empresa)
    if not request.user.has_perm(f"comercial.change_{model._meta.model_name}"):raise PermissionDenied
    if obj.activo:inactivar_catalogo(context=_context(request,empresa),tipo=model.__name__,pk=pk)
    else:obj.activo=True;obj.full_clean();obj.save(update_fields=["activo"])
    return redirect("comercial:catalogo_detalle",tipo=tipo,pk=pk)

@login_required
def politica_lista(request,tipo):
    model=POLITICAS[tipo];qs=model.objects.filter(empresa=_empresa(request));return render(request,"comercial/configuracion/lista.html",{"objetos":Paginator(qs,25).get_page(request.GET.get("page")),"tipo":tipo,"titulo":model._meta.verbose_name_plural.title(),"es_politica":True})

@login_required
def politica_detalle(request,tipo,pk):
    empresa=_empresa(request);obj=get_object_or_404(POLITICAS[tipo],pk=pk,empresa=empresa);versiones=VersionPoliticaComercial.objects.filter(empresa=empresa,tipo_politica=obj.__class__.__name__,codigo=obj.codigo);return render(request,"comercial/configuracion/detalle.html",{"objeto":obj,"tipo":tipo,"titulo":obj.nombre,"versiones":versiones,"es_politica":True})

@login_required
def politica_editar(request,tipo,pk=None):
    empresa=_empresa(request);model=POLITICAS[tipo];obj=get_object_or_404(model,pk=pk,empresa=empresa) if pk else None
    if obj and obj.estado!="BORRADOR":raise PermissionDenied("Solo se editan borradores; use versionar.")
    form=politica_form_factory(model)(request.POST or None,instance=obj,empresa=empresa)
    if request.method=="POST" and form.is_valid():
        if obj:
            item=form.save(commit=False);item.empresa=empresa;item.full_clean();item.save()
        else:item=crear_politica(context=_context(request,empresa),tipo=model.__name__,datos=form.cleaned_data)
        return redirect("comercial:politica_detalle",tipo=tipo,pk=item.pk)
    return render(request,"comercial/configuracion/form.html",{"form":form,"titulo":"Política comercial"})

@require_POST
@login_required
def politica_accion(request,tipo,pk,accion):
    empresa=_empresa(request);model=POLITICAS[tipo];obj=get_object_or_404(model,pk=pk,empresa=empresa);context=_context(request,empresa)
    if accion=="activar":activar_politica(context=context,tipo=model.__name__,pk=pk)
    elif accion=="inactivar":obj.estado="INACTIVA";obj.save(update_fields=["estado"])
    elif accion=="versionar":versionar_politica(context=context,tipo=model.__name__,pk=pk,datos={},motivo=request.POST.get("motivo","Actualización operativa"))
    else:raise PermissionDenied
    return redirect("comercial:politica_detalle",tipo=tipo,pk=pk)

@login_required
def secuencias(request):
    empresa=_empresa(request)
    if request.method=="POST":
        tipo=request.POST.get("tipo");form=SecuenciaComercialForm(request.POST,empresa=empresa)
        if form.is_valid():configurar_secuencia(context=_context(request,empresa),tipo=tipo,**form.cleaned_data);messages.success(request,"Secuencia configurada.");return redirect("comercial:secuencias")
    else:form=SecuenciaComercialForm(empresa=empresa)
    existentes={o.tipo:o for o in SecuenciaDocumento.objects.filter(empresa=empresa,periodo=timezone.localdate().year)}
    return render(request,"comercial/configuracion/secuencias.html",{"tipos":TIPOS_SECUENCIA,"existentes":existentes,"form":form})

@require_POST
@login_required
def readiness_ejecutar(request):
    validar_readiness(context=_context(request,_empresa(request)));messages.success(request,"Validación de preparación completada.");return redirect("comercial:configuracion_dashboard")

def _filas(empresa):
    for tipo,model in CATALOGOS.items():
        for obj in model.objects.filter(empresa=empresa):yield [tipo,obj.codigo,obj.nombre,"Activo" if obj.activo else "Inactivo"]

@login_required
@permission_required("comercial.exportar_configuracion_comercial",raise_exception=True)
def exportar(request,formato):
    empresa=_empresa(request);filas=list(_filas(empresa));registrar_evento(empresa=empresa,usuario=request.user,request=request,modulo="comercial",accion=EventoAuditoria.Accion.OTRO,descripcion=f"Exportación comercial {formato.upper()} generada.",datos_nuevos={"formato":formato,"filas":len(filas)})
    if formato=="csv":
        response=HttpResponse(content_type="text/csv; charset=utf-8");response["Content-Disposition"]='attachment; filename="configuracion-comercial.csv"';writer=csv.writer(response);writer.writerow(["Tipo","Código","Nombre","Estado"])
        for row in filas:writer.writerow([("'"+v) if isinstance(v,str) and v[:1] in "=+-@" else v for v in row])
        return response
    if formato=="xlsx":
        from openpyxl import Workbook
        wb=Workbook();ws=wb.active;ws.title="Configuración";ws.append(["Tipo","Código","Nombre","Estado"])
        for row in filas:ws.append(row)
        stream=BytesIO();wb.save(stream);response=HttpResponse(stream.getvalue(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");response["Content-Disposition"]='attachment; filename="configuracion-comercial.xlsx"';return response
    if formato=="pdf":
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen.canvas import Canvas
        stream=BytesIO();pdf=Canvas(stream,pagesize=letter);y=750;pdf.setTitle("Configuración comercial");pdf.drawString(50,y,f"Configuración comercial - {empresa}");y-=25
        for row in filas:
            pdf.drawString(50,y," | ".join(str(x)[:35] for x in row));y-=16
            if y<50:pdf.showPage();y=750
        pdf.save();response=HttpResponse(stream.getvalue(),content_type="application/pdf");response["Content-Disposition"]='attachment; filename="configuracion-comercial.pdf"';return response
    return render(request,"comercial/configuracion/impresion.html",{"filas":filas,"empresa":empresa})

@login_required
def reportes(request):
    empresa=_empresa(request);form=FiltroReporteComercialForm(request.GET or None);return render(request,"comercial/configuracion/reportes.html",{"form":form,"filas":list(_filas(empresa)),"readiness":validar_empresa_lista_para_vender(empresa=empresa)})
