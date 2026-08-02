from dataclasses import dataclass
from decimal import Decimal
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction, models
from django.utils import timezone
from comercial.models import *
from comercial.models import SecuenciaDocumento
from catalogos.models import Impuesto,CondicionPago

@dataclass(frozen=True)
class ConfiguracionDTO:id:int;empresa_id:int;estado:str;version:int;ready:bool;percentage:Decimal
@dataclass(frozen=True)
class ReadinessDTO:ready:bool;percentage:Decimal;blockers:tuple;warnings:tuple;recommendations:tuple;sections:dict
def _dto(o):return ConfiguracionDTO(o.pk,o.empresa_id,o.estado,o.version,o.lista_para_vender,o.porcentaje_preparacion)
def obtener_configuracion_comercial(*,empresa):return _dto(ConfiguracionComercialEmpresa.objects.get(empresa=empresa))
@transaction.atomic
def actualizar_configuracion_comercial(*,context,datos):
    if not context.usuario.has_perm("comercial.change_configuracioncomercialempresa"):raise PermissionDenied
    o,_=ConfiguracionComercialEmpresa.objects.select_for_update().get_or_create(empresa=context.empresa,defaults={"creado_por":context.usuario});
    for k,v in datos.items():setattr(o,k,v)
    o.version+=1;o.actualizado_por=context.usuario;o.full_clean();o.save();return _dto(o)
def validar_empresa_lista_para_vender(*,empresa,persistir=False):
    from django.contrib.auth.models import Group, Permission
    from documentos.models import TipoDocumento
    from workflow.models import ReglaAprobacion
    tipos=("COT","PED","PRG","DSP","CON","ENT","FAC","NCR","NDB","COB","DEV","COM","PROS","OPO")
    blockers=[];warnings=[];sections={};cfg=ConfiguracionComercialEmpresa.objects.filter(empresa=empresa).first()
    sections["empresa_activa"]=getattr(empresa,"activa",getattr(empresa,"activo",True));sections["configuracion"]=bool(cfg);sections["moneda_base"]=bool(cfg and cfg.moneda_base_id)
    sections["impuestos"]=Impuesto.objects.filter(empresa=empresa,activo=True).exists();sections["condiciones_pago"]=CondicionPago.objects.filter(empresa=empresa,activo=True).exists()
    sections["catalogos"]=all(m.objects.filter(empresa=empresa,activo=True).exists() for m in (CanalVenta,SegmentoCliente,ClasificacionCliente,TipoCliente,TipoEntrega,PrioridadComercial,MotivoComercial))
    sections["vendedores_equipos"]=VendedorComercial.objects.filter(empresa=empresa,activo=True).exists() and EquipoComercial.objects.filter(empresa=empresa,activo=True).exists();sections["zonas_rutas"]=ZonaComercial.objects.filter(empresa=empresa,activo=True).exists() and RutaComercial.objects.filter(empresa=empresa,activo=True).exists()
    politicas=(PoliticaCredito,PoliticaDescuento,PoliticaEntrega,PoliticaFacturacion,PoliticaDevolucion,PoliticaComision);sections["politicas"]=all(m.objects.filter(empresa=empresa,estado="ACTIVA").exists() for m in politicas)
    sections["politicas_sin_ambiguedad"]=not any(m.objects.filter(empresa=empresa,estado="ACTIVA").values("prioridad","ambito").annotate(n=models.Count("id")).filter(n__gt=1).exists() for m in politicas)
    sections["secuencias_14"]=all(SecuenciaDocumento.objects.filter(empresa=empresa,tipo=t,activo=True).exists() for t in tipos);sections["workflow"]=ReglaAprobacion.objects.filter(empresa=empresa,activa=True).exists();sections["documentos"]=TipoDocumento.objects.filter(empresa=empresa,activo=True).exists()
    sections["permisos"]=Permission.objects.filter(content_type__app_label="comercial").exists();sections["grupos"]=Group.objects.filter(name__in=("Administrador Comercial","Gerente Comercial","Vendedor","Auditor Comercial")).count()==4;sections["inabie"]=not getattr(empresa,"modulo_inabie",False) or bool(cfg and cfg.usa_inabie)
    for k,v in sections.items():
        if not v:blockers.append(k)
    pct=(Decimal(sum(sections.values()))/Decimal(len(sections))*100).quantize(Decimal("0.01"));ready=not blockers
    if empresa.modulo_inabie and not (cfg and cfg.usa_inabie):warnings.append("INABIE habilitado sin configuración comercial.")
    r=ReadinessDTO(ready,pct,tuple(blockers),tuple(warnings),tuple(f"Completar {x}" for x in blockers),sections)
    if persistir and cfg:cfg.lista_para_vender=ready;cfg.porcentaje_preparacion=pct;cfg.ultima_validacion=timezone.now();cfg.resultado_validacion={"formula_version":"1.0","blockers":blockers,"warnings":warnings,"recommendations":list(r.recommendations),"sections":sections};cfg.save()
    return r
def _get(model,empresa,pk):
    o=model.objects.get(pk=pk,empresa=empresa);return {"id":o.pk,"codigo":o.codigo,"nombre":o.nombre,"activo":o.activo}
def obtener_canal(*,empresa,pk):return _get(CanalVenta,empresa,pk)
def obtener_segmento(*,empresa,pk):return _get(SegmentoCliente,empresa,pk)
def obtener_zona(*,empresa,pk):return _get(ZonaComercial,empresa,pk)
def obtener_ruta(*,empresa,pk):return _get(RutaComercial,empresa,pk)
def obtener_vendedor(*,empresa,pk):return _get(VendedorComercial,empresa,pk)
def _politica(model,empresa,fecha=None):return model.objects.filter(empresa=empresa,estado="ACTIVA",vigencia_desde__lte=fecha or timezone.localdate()).order_by("prioridad","-version").values("id","codigo","version","reglas").first()
def obtener_politica_credito(*,empresa,fecha=None):return _politica(PoliticaCredito,empresa,fecha)
def obtener_politica_entrega(*,empresa,fecha=None):return _politica(PoliticaEntrega,empresa,fecha)
def obtener_politica_facturacion(*,empresa,fecha=None):return _politica(PoliticaFacturacion,empresa,fecha)
def obtener_politica_devolucion(*,empresa,fecha=None):return _politica(PoliticaDevolucion,empresa,fecha)
def obtener_politica_comision(*,empresa,fecha=None):return _politica(PoliticaComision,empresa,fecha)
def obtener_secuencia_comercial(*,empresa,tipo):return SecuenciaDocumento.objects.filter(empresa=empresa,tipo=tipo,activo=True).values("tipo","prefijo","longitud","periodo").first()
