import hashlib
import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from comercial.api.configuracion import validar_empresa_lista_para_vender
from comercial.domain.configuracion_events import (
    ConfiguracionComercialValidada, EmpresaListaParaVender, EmpresaNoListaParaVender,
    PoliticaComercialVersionada, SecuenciaComercialConfigurada,
)
from comercial.models import (
    ConfiguracionComercialEmpresa, SecuenciaDocumento, VersionPoliticaComercial,
    PoliticaCredito, PoliticaDescuento, PoliticaEntrega, PoliticaFacturacion,
    PoliticaDevolucion, PoliticaComision,
)
from core.application.event_bus import event_bus

TIPOS_SECUENCIA=("COT","PED","PRG","DSP","CON","ENT","FAC","NCR","NDB","COB","DEV","COM","PROS","OPO")
POLITICAS={m.__name__:m for m in (PoliticaCredito,PoliticaDescuento,PoliticaEntrega,PoliticaFacturacion,PoliticaDevolucion,PoliticaComision)}

def _perm(context, codename):
    if not context.usuario.has_perm(f"comercial.{codename}"):raise PermissionDenied

def _registrar(context,objeto,descripcion,evento,sufijo,payload):
    registrar_evento(empresa=context.empresa,usuario=context.usuario,request=context.request,objeto=objeto,modulo="comercial",accion=EventoAuditoria.Accion.OTRO,descripcion=descripcion,datos_nuevos=payload)
    event_bus.publish(evento(empresa_id=context.empresa.pk,usuario_id=context.usuario.pk,agregado_tipo=f"comercial.{objeto.__class__.__name__}",agregado_id=str(objeto.pk),referencia=getattr(objeto,"codigo",str(objeto.pk)),clave_idempotente=f"{context.identificador_solicitud}:{sufijo}:{objeto.pk}"[:180],payload={"schema_version":1,"empresa_id":context.empresa.pk,**payload}))

@transaction.atomic
def configurar_secuencia(*,context,tipo,prefijo=None,longitud=6,activo=True):
    if tipo not in TIPOS_SECUENCIA:raise ValidationError("Tipo de secuencia comercial no permitido.")
    _perm(context,"change_secuenciadocumento");periodo=timezone.localdate().year
    obj,_=SecuenciaDocumento.objects.select_for_update().get_or_create(empresa=context.empresa,tipo=tipo,periodo=periodo,defaults={"creado_por":context.usuario})
    obj.prefijo=prefijo or tipo;obj.longitud=longitud;obj.activo=activo;obj.actualizado_por=context.usuario;obj.full_clean();obj.save()
    _registrar(context,obj,f"Secuencia comercial {tipo} configurada.",SecuenciaComercialConfigurada,f"secuencia-{tipo}",{"tipo":tipo,"prefijo":obj.prefijo,"longitud":obj.longitud})
    return obj

def _contenido(obj):
    return {"codigo":obj.codigo,"nombre":obj.nombre,"version":obj.version,"estado":obj.estado,"vigencia_desde":obj.vigencia_desde.isoformat(),"vigencia_hasta":obj.vigencia_hasta.isoformat() if obj.vigencia_hasta else None,"prioridad":obj.prioridad,"ambito":obj.ambito,"reglas":obj.reglas}

@transaction.atomic
def versionar_politica(*,context,tipo,pk,datos,motivo):
    model=POLITICAS[tipo];anterior=model.objects.select_for_update().get(pk=pk,empresa=context.empresa);_perm(context,"versionar_politica_comercial");contenido=_contenido(anterior)
    snapshot=VersionPoliticaComercial.objects.create(empresa=context.empresa,tipo_politica=tipo,objeto_id=anterior.pk,codigo=anterior.codigo,version=anterior.version,estado=anterior.estado,vigencia_desde=anterior.vigencia_desde,vigencia_hasta=anterior.vigencia_hasta,prioridad=anterior.prioridad,contenido=contenido,hash_contenido=hashlib.sha256(json.dumps(contenido,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest(),motivo=motivo,version_anterior=VersionPoliticaComercial.objects.filter(empresa=context.empresa,tipo_politica=tipo,codigo=anterior.codigo).first(),creado_por=context.usuario)
    nuevo=model(empresa=context.empresa,codigo=anterior.codigo,nombre=datos.get("nombre",anterior.nombre),version=anterior.version+1,estado="BORRADOR",vigencia_desde=datos.get("vigencia_desde",anterior.vigencia_desde),vigencia_hasta=datos.get("vigencia_hasta",anterior.vigencia_hasta),prioridad=datos.get("prioridad",anterior.prioridad),ambito=datos.get("ambito",anterior.ambito),reglas=datos.get("reglas",anterior.reglas),creado_por=context.usuario)
    nuevo.full_clean();nuevo.save();_registrar(context,nuevo,"Política comercial versionada.",PoliticaComercialVersionada,f"version-{nuevo.version}",{"snapshot_id":snapshot.pk,"version":nuevo.version});return nuevo

@transaction.atomic
def validar_readiness(*,context):
    _perm(context,"validar_configuracion_comercial");resultado=validar_empresa_lista_para_vender(empresa=context.empresa,persistir=True);cfg=ConfiguracionComercialEmpresa.objects.get(empresa=context.empresa);payload={"percentage":str(resultado.percentage),"ready":resultado.ready}
    _registrar(context,cfg,"Readiness comercial validado.",ConfiguracionComercialValidada,"readiness",payload);_registrar(context,cfg,"Estado de preparación comercial actualizado.",EmpresaListaParaVender if resultado.ready else EmpresaNoListaParaVender,"ready-state",payload);return resultado
