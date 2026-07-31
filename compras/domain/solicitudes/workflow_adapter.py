from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from workflow.domain.adapters import WorkflowDocumentAdapter
from compras.models import HistorialEstadoSolicitudCompra, SolicitudCompra


class SolicitudCompraWorkflowAdapter(WorkflowDocumentAdapter):
    key="compras.solicitud_compra"
    allowed_context_fields=frozenset({"monto_total","moneda","centro_costo_id","tipo_compra","naturaleza","prioridad","es_urgente","compra_directa_propuesta","proveedor_exclusivo_declarado","requiere_contrato","requiere_activo_fijo","requiere_inspeccion","solicitante_id","area_codigo","disponibilidad_presupuestaria","cantidad_lineas"})
    def get_empresa(self,document): return document.empresa
    def get_solicitante(self,document): return document.solicitante
    def build_context(self,document):
        return {"monto_total":document.total_estimado,"moneda":document.moneda.moneda.codigo,"centro_costo_id":document.centro_costo_id,"tipo_compra":document.tipo_compra.codigo,"naturaleza":document.naturaleza,"prioridad":document.prioridad,"es_urgente":document.es_urgente,"compra_directa_propuesta":document.compra_directa_propuesta,"proveedor_exclusivo_declarado":document.proveedor_exclusivo_declarado,"requiere_contrato":document.requiere_contrato,"requiere_activo_fijo":document.requiere_activo_fijo,"requiere_inspeccion":document.requiere_inspeccion,"solicitante_id":document.solicitante_id,"area_codigo":document.area_solicitante,"disponibilidad_presupuestaria":document.disponibilidad_presupuestaria,"cantidad_lineas":document.lineas.filter(activo=True).count()}
    def can_start(self,document): return document.estado==SolicitudCompra.Estado.LISTA_PARA_ENVIO and document.lineas.filter(activo=True).exists()
    def snapshot(self,document):
        return {"referencia":document.numero,"version":document.version_documento,"titulo":document.titulo,"total":document.total_estimado,"moneda":document.moneda.moneda.codigo,"cantidad_lineas":document.lineas.filter(activo=True).count()}
    def document_url(self,document,user):
        if not user or not user.is_authenticated or not user.has_perm("compras.view_solicitudcompra"): return ""
        return reverse("compras:solicitud_detalle",kwargs={"pk":document.pk})
    def resolve_dynamic_assignees(self,document,parameter):
        if parameter in {"RESPONSABLE_CENTRO_COSTO","responsable_centro_costo"}:
            user=document.responsable_centro_costo or document.centro_costo.responsable
            return [user] if user else []
        return []
    @transaction.atomic
    def _sync(self,document,state):
        obj=SolicitudCompra.objects.select_for_update().get(pk=document.pk,empresa=document.empresa);old=obj.estado
        mapping={"EN_APROBACION":SolicitudCompra.Estado.EN_APROBACION,"APROBADA":SolicitudCompra.Estado.APROBADA,"RECHAZADA":SolicitudCompra.Estado.RECHAZADA,"DEVUELTA":SolicitudCompra.Estado.DEVUELTA,"CANCELADA":SolicitudCompra.Estado.CANCELADA}
        new=mapping.get(state)
        if not new or old==new:return obj
        if old in {SolicitudCompra.Estado.APROBADA,SolicitudCompra.Estado.RECHAZADA,SolicitudCompra.Estado.CANCELADA,SolicitudCompra.Estado.CERRADA}:return obj
        obj.estado=new;obj.estado_workflow_snapshot=state
        now=timezone.now()
        if new==SolicitudCompra.Estado.EN_APROBACION: obj.enviada_en=obj.enviada_en or now
        elif new==SolicitudCompra.Estado.APROBADA: obj.aprobada_en=now
        elif new==SolicitudCompra.Estado.RECHAZADA: obj.rechazada_en=now
        elif new==SolicitudCompra.Estado.DEVUELTA: obj.devuelta_en=now
        elif new==SolicitudCompra.Estado.CANCELADA: obj.cancelada_en=now
        obj.save();HistorialEstadoSolicitudCompra.objects.create(empresa=obj.empresa,solicitud=obj,estado_anterior=old,estado_nuevo=new,origen="WORKFLOW",workflow_instancia_id=obj.workflow_instancia_id,ronda=obj.ronda_workflow_actual)
        return obj
    def on_state_change(self,document,state): return self._sync(document,state)
    def on_final_result(self,document,result): return self._sync(document,result)
