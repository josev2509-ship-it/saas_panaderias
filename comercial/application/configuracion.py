from dataclasses import replace
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.utils import timezone
from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from core.application.event_bus import event_bus
from comercial.domain.configuracion_events import *
from comercial.models import *

CATALOGOS={m.__name__:m for m in (CanalVenta,SegmentoCliente,ClasificacionCliente,TipoCliente,TipoEntrega,PrioridadComercial,MotivoComercial,FuenteProspecto,ZonaComercial,RutaComercial,EquipoComercial,VendedorComercial)}
POLITICAS={m.__name__:m for m in (PoliticaCredito,PoliticaDescuento,PoliticaEntrega,PoliticaFacturacion,PoliticaDevolucion,PoliticaComision)}
def _perm(c,p):
    if not c.usuario or not c.usuario.has_perm(f"comercial.{p}"):raise PermissionDenied
def _audit(c,o,text,before=None,after=None):registrar_evento(empresa=c.empresa,usuario=c.usuario,request=c.request,objeto=o,modulo="comercial",accion=EventoAuditoria.Accion.OTRO,descripcion=text,datos_anteriores=before,datos_nuevos=after)
def _emit(c,cls,o,suffix,extra=None):
    p={"empresa_id":c.empresa.pk,"aggregate_id":o.pk,"aggregate_type":o.__class__.__name__,"reference":getattr(o,"codigo",str(o.pk)),"actor_id":getattr(c.usuario,"pk",None),"occurred_at":timezone.now().isoformat(),"schema_version":1,**(extra or {})}
    return event_bus.publish(cls(empresa_id=c.empresa.pk,usuario_id=getattr(c.usuario,"pk",None),agregado_tipo=f"comercial.{o.__class__.__name__}",agregado_id=str(o.pk),referencia=p["reference"],clave_idempotente=f"{c.clave_idempotente or c.identificador_solicitud}:{suffix}:{o.pk}"[:180],payload=p))
@transaction.atomic
def crear_configuracion(*,context,datos=None):
    _perm(context,"add_configuracioncomercialempresa");o,created=ConfiguracionComercialEmpresa.objects.select_for_update().get_or_create(empresa=context.empresa,defaults={"creado_por":context.usuario,**(datos or {})})
    if created:_audit(context,o,"Configuración comercial creada.");_emit(context,ConfiguracionComercialCreada,o,"creada")
    return o
@transaction.atomic
def actualizar_configuracion(*,context,datos):
    _perm(context,"change_configuracioncomercialempresa");o=ConfiguracionComercialEmpresa.objects.select_for_update().get(empresa=context.empresa);before={k:str(getattr(o,k)) for k in datos}
    for k,v in datos.items():setattr(o,k,v)
    o.version+=1;o.actualizado_por=context.usuario;o.full_clean();o.save();_audit(context,o,"Configuración comercial actualizada.",before,{k:str(v) for k,v in datos.items()});_emit(context,ConfiguracionComercialActualizada,o,f"actualizada-v{o.version}");return o
@transaction.atomic
def crear_catalogo(*,context,tipo,datos):
    model=CATALOGOS[tipo];_perm(context,f"add_{model._meta.model_name}");o=model(empresa=context.empresa,**datos);o.full_clean();o.save();_audit(context,o,"Catálogo comercial creado.");_emit(context,CatalogoComercialCreado,o,"creado");return o
@transaction.atomic
def editar_catalogo(*,context,tipo,pk,datos):
    model=CATALOGOS[tipo];_perm(context,f"change_{model._meta.model_name}");o=model.objects.select_for_update().get(pk=pk,empresa=context.empresa)
    for k,v in datos.items():setattr(o,k,v)
    o.full_clean();o.save();_audit(context,o,"Catálogo comercial actualizado.");_emit(context,CatalogoComercialActualizado,o,"actualizado");return o
@transaction.atomic
def inactivar_catalogo(*,context,tipo,pk):
    model=CATALOGOS[tipo];_perm(context,f"change_{model._meta.model_name}");o=model.objects.select_for_update().get(pk=pk,empresa=context.empresa);o.activo=False;o.save(update_fields=["activo"]);_audit(context,o,"Catálogo comercial inactivado.");_emit(context,CatalogoComercialInactivado,o,"inactivado");return o
@transaction.atomic
def crear_politica(*,context,tipo,datos):
    model=POLITICAS[tipo];_perm(context,f"add_{model._meta.model_name}");o=model(empresa=context.empresa,creado_por=context.usuario,**datos);o.full_clean();o.save();_audit(context,o,"Política creada.");_emit(context,PoliticaComercialCreada,o,"creada");return o
@transaction.atomic
def activar_politica(*,context,tipo,pk):
    model=POLITICAS[tipo];o=model.objects.select_for_update().get(pk=pk,empresa=context.empresa);_perm(context,f"change_{model._meta.model_name}");amb=model.objects.filter(empresa=context.empresa,estado="ACTIVA",prioridad=o.prioridad,ambito=o.ambito).exclude(pk=o.pk)
    if amb.exists():raise ValidationError("Existe una política activa ambigua.")
    o.estado="ACTIVA";o.save(update_fields=["estado"]);_audit(context,o,"Política activada.");_emit(context,PoliticaComercialActivada,o,"activada");return o
