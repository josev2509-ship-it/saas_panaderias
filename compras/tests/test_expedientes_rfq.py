from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from catalogos.models import CentroCosto,Moneda,MonedaEmpresa,TipoCompra,UnidadMedida
from conduces.models import Empresa
from core.application.operation_context import OperationContext
from compras.application.expedientes_rfq import *
from compras.models import *
from core.models import EventoDominio
from auditoria.models import EventoAuditoria
from documentos.models import TipoDocumento
from documentos.services import crear_documento_asociado,reemplazar_documento,anular_documento

class ExpedienteRFQTest(TestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user("p2p",password="x");self.e=Empresa.objects.create(usuario=self.u,nombre="Empresa",modulo_compras=True);self.u.user_permissions.add(*Permission.objects.filter(content_type__app_label="compras"));self.ctx=OperationContext(empresa=self.e,usuario=self.u,clave_idempotente="p2p")
        self.cc=CentroCosto.objects.create(empresa=self.e,codigo="CC",nombre="Centro");self.tc=TipoCompra.objects.create(empresa=self.e,codigo="B",nombre="Bien",naturaleza="BIEN");m=Moneda.objects.create(codigo="DOP",nombre="Peso",simbolo="$" );self.mon=MonedaEmpresa.objects.create(empresa=self.e,moneda=m,es_base=True);self.um=UnidadMedida.objects.create(empresa=self.e,codigo="UND",nombre="Unidad",simbolo="u",magnitud="UNIDAD")
        self.s=SolicitudCompra.objects.create(empresa=self.e,numero="SC-1",titulo="Necesidad",solicitante=self.u,centro_costo=self.cc,tipo_compra=self.tc,naturaleza="BIEN",fecha_solicitud=timezone.localdate(),fecha_necesaria=timezone.localdate()+timedelta(days=5),moneda=self.mon,justificacion="Necesaria",impacto_no_compra="Impacto",estado="APROBADA",total_estimado=100,creado_por=self.u)
        DetalleSolicitudCompra.objects.create(empresa=self.e,solicitud=self.s,orden=1,tipo_linea="LIBRE",descripcion="Artículo",cantidad=1,unidad_medida=self.um,precio_unitario_estimado=100,subtotal=100,total=100)
    def test_expediente_is_idempotent_and_requires_approved(self):
        a=crear_expediente_desde_solicitud(context=self.ctx,solicitud_id=self.s.pk);b=crear_expediente_desde_solicitud(context=self.ctx,solicitud_id=self.s.pk);self.assertEqual(a.pk,b.pk);self.assertTrue(a.numero.startswith("EXP-"))
    def test_rfq_lines_validation_and_health(self):
        e=crear_expediente_desde_solicitud(context=self.ctx,solicitud_id=self.s.pk);abrir_expediente(context=self.ctx,expediente_id=e.pk);r=crear_rfq(context=self.ctx,expediente_id=e.pk,datos={"titulo":"RFQ","objeto":"Comprar","descripcion":"Proceso","fecha_inicio":timezone.now()+timedelta(hours=1),"fecha_limite":timezone.now()+timedelta(days=3),"entrega_requerida_desde":timezone.localdate()+timedelta(days=4),"entrega_requerida_hasta":timezone.localdate()+timedelta(days=8),"lugar_entrega":"Almacén","condiciones_comerciales":"Crédito"});self.assertTrue(r.numero.startswith("RFQ-"));self.assertEqual(generar_lineas_desde_solicitudes(context=self.ctx,rfq_id=r.pk),1);self.assertFalse(validar_rfq_para_publicacion(context=self.ctx,rfq=r).valido);self.assertIn("puntuacion",calcular_salud_expediente(expediente=e))
    def test_cross_tenant_is_rejected(self):
        other_u=get_user_model().objects.create_user("other");other=Empresa.objects.create(usuario=other_u,nombre="Otra");other_u.user_permissions.add(Permission.objects.get(content_type__app_label="compras",codename="add_expedientecompra"))
        with self.assertRaises(SolicitudCompra.DoesNotExist):crear_expediente_desde_solicitud(context=OperationContext(empresa=other,usuario=other_u),solicitud_id=self.s.pk)
    def test_event_and_audit_are_recorded(self):
        e=crear_expediente_desde_solicitud(context=self.ctx,solicitud_id=self.s.pk);self.assertTrue(EventoDominio.objects.filter(empresa=self.e,agregado_id=str(e.pk)).exists());self.assertTrue(EventoAuditoria.objects.filter(empresa=self.e,object_id=e.pk).exists())
    def test_dashboard_and_get_action_security(self):
        e=crear_expediente_desde_solicitud(context=self.ctx,solicitud_id=self.s.pk);self.client.force_login(self.u);self.assertContains(self.client.get(reverse("compras:p2p_dashboard")),"Expedientes y RFQ");self.assertEqual(self.client.get(reverse("compras:expediente_accion",args=[e.pk,"abrir"])).status_code,403)
    def test_config_command_is_idempotent(self):
        from django.core.management import call_command
        call_command("configurar_expedientes_rfq");call_command("configurar_expedientes_rfq")

    def _rfq(self):
        e=crear_expediente_desde_solicitud(context=self.ctx,solicitud_id=self.s.pk);abrir_expediente(context=self.ctx,expediente_id=e.pk)
        r=crear_rfq(context=self.ctx,expediente_id=e.pk,datos={"titulo":"RFQ","objeto":"Comprar","descripcion":"Proceso","fecha_inicio":timezone.now()+timedelta(hours=1),"fecha_limite":timezone.now()+timedelta(days=3),"entrega_requerida_desde":timezone.localdate()+timedelta(days=4),"entrega_requerida_hasta":timezone.localdate()+timedelta(days=8),"lugar_entrega":"Almacén","condiciones_comerciales":"Crédito","minimo_proveedores":1})
        return e,r

    def _proveedor(self,codigo="P1",estado="ACTIVO",bloqueado=False):
        p=Proveedor.objects.create(empresa=self.e,codigo=codigo,tipo_persona="JURIDICA",razon_social=codigo,estado=estado,bloqueado=bloqueado,motivo_bloqueo="Riesgo" if bloqueado else "",creado_por=self.u)
        c=ContactoProveedor.objects.create(empresa=self.e,proveedor=p,nombre="Contacto",correo=f"{codigo.lower()}@example.com",activo=True,creado_por=self.u)
        return p,c

    def _documento(self,r,nombre="rfq.pdf"):
        tipo=TipoDocumento.objects.get_or_create(empresa=self.e,codigo="RFQ",defaults={"nombre":"RFQ"})[0]
        return crear_documento_asociado(empresa=self.e,objeto=r,archivo=SimpleUploadedFile(nombre,b"%PDF-1.4\n%%EOF",content_type="application/pdf"),usuario=self.u,titulo="Anexo",tipo_documento=tipo)

    def test_publication_matrix_and_document_requirement(self):
        _,r=self._rfq();generar_lineas_desde_solicitudes(context=self.ctx,rfq_id=r.pk)
        self.assertIn("Faltan criterios.",validar_rfq_para_publicacion(context=self.ctx,rfq=r).errores)
        agregar_criterio(context=self.ctx,rfq_id=r.pk,datos={"codigo":"PRECIO","nombre":"Precio","categoria":"ECONOMICO","peso_porcentaje":90,"metodo_evaluacion":"MENOR_ES_MEJOR"})
        agregar_regla_participacion(context=self.ctx,rfq_id=r.pk,datos={"codigo":"DOC","nombre":"Documento","tipo":"DOCUMENTO_OBLIGATORIO"})
        p,c=self._proveedor();agregar_proveedor_a_rfq(context=self.ctx,rfq_id=r.pk,proveedor_id=p.pk,contacto_id=c.pk)
        v=validar_rfq_para_publicacion(context=self.ctx,rfq=r);self.assertIn("Los pesos deben sumar 100.",v.errores);self.assertIn("Falta documentación obligatoria de la RFQ.",v.errores)
        r.criterios.update(peso_porcentaje=100);self._documento(r);enviar_rfq_revision(context=self.ctx,rfq_id=r.pk);publicar_rfq(context=self.ctx,rfq_id=r.pk);r.refresh_from_db();self.assertEqual(r.estado,"PUBLICADA")
        with self.assertRaises(ValidationError):publicar_rfq(context=self.ctx,rfq_id=r.pk)
        self.assertTrue(r.historial.filter(estado_nuevo="PUBLICADA").exists());self.assertTrue(EventoDominio.objects.filter(empresa=self.e,tipo_evento="RFQPublicada").exists())

    def test_blocked_inactive_and_invalid_contacts_are_rejected(self):
        _,r=self._rfq();p,c=self._proveedor("PB",bloqueado=True)
        with self.assertRaises(Proveedor.DoesNotExist):agregar_proveedor_a_rfq(context=self.ctx,rfq_id=r.pk,proveedor_id=p.pk,contacto_id=c.pk)
        p2,c2=self._proveedor("PI",estado="INACTIVO")
        with self.assertRaises(Proveedor.DoesNotExist):agregar_proveedor_a_rfq(context=self.ctx,rfq_id=r.pk,proveedor_id=p2.pk,contacto_id=c2.pk)
        p3,c3=self._proveedor("PA");p4,c4=self._proveedor("PX")
        with self.assertRaises(ContactoProveedor.DoesNotExist):agregar_proveedor_a_rfq(context=self.ctx,rfq_id=r.pk,proveedor_id=p3.pk,contacto_id=c4.pk)

    def test_invitation_state_conflicts_contact_and_motives(self):
        _,r=self._rfq();p,c=self._proveedor();i=agregar_proveedor_a_rfq(context=self.ctx,rfq_id=r.pk,proveedor_id=p.pk,contacto_id=c.pk)
        marcar_invitacion_enviada(context=self.ctx,invitacion_id=i.pk)
        with self.assertRaises(ValidationError):marcar_invitacion_enviada(context=self.ctx,invitacion_id=i.pk)
        with self.assertRaises(ValidationError):cambiar_contacto_invitacion_rfq(context=self.ctx,invitacion_id=i.pk,contacto_id=c.pk)
        with self.assertRaises(ValidationError):declinar_participacion(context=self.ctx,invitacion_id=i.pk,motivo="")
        confirmar_participacion(context=self.ctx,invitacion_id=i.pk)
        with self.assertRaises(ValidationError):declinar_participacion(context=self.ctx,invitacion_id=i.pk,motivo="Contradicción")
        with self.assertRaises(ValidationError):retirar_proveedor_de_rfq(context=self.ctx,invitacion_id=i.pk,motivo="Retiro")

    def test_extension_close_cancel_and_pending_policy(self):
        _,r=self._rfq();r.estado="ABIERTA";r.save();old=r.fecha_limite
        with self.assertRaises(ValidationError):extender_plazo_rfq(context=self.ctx,rfq_id=r.pk,nueva_fecha=old,motivo="Motivo")
        extender_plazo_rfq(context=self.ctx,rfq_id=r.pk,nueva_fecha=old+timedelta(days=1),motivo="Ampliación solicitada")
        p,c=self._proveedor();i=agregar_proveedor_a_rfq(context=self.ctx,rfq_id=r.pk,proveedor_id=p.pk,contacto_id=c.pk)
        with self.assertRaises(ValidationError):cerrar_rfq(context=self.ctx,rfq_id=r.pk)
        marcar_invitacion_enviada(context=self.ctx,invitacion_id=i.pk);marcar_sin_respuesta(context=self.ctx,invitacion_id=i.pk);cerrar_rfq(context=self.ctx,rfq_id=r.pk)
        with self.assertRaises(ValidationError):cerrar_rfq(context=self.ctx,rfq_id=r.pk)
        r.estado="BORRADOR";r.save(update_fields=["estado"]);r2=r
        with self.assertRaises(ValidationError):cancelar_rfq(context=self.ctx,rfq_id=r2.pk,motivo="")
        cancelar_rfq(context=self.ctx,rfq_id=r2.pk,motivo="Proceso descontinuado");self.assertTrue(r2.lineas.count()==0)

    def test_document_event_is_single_and_payload_is_safe(self):
        _,r=self._rfq();d=self._documento(r);events=EventoDominio.objects.filter(empresa=self.e,tipo_evento="DocumentoRFQActualizado")
        self.assertEqual(events.count(),1);payload=events.get().payload["payload"]
        self.assertEqual(payload["documento_id"],d.pk);self.assertTrue({"rfq_id","accion","version_documento","actor_id","timestamp","schema_version"}<=payload.keys())
        self.assertFalse({"archivo","ruta","contenido","nombre_original"}&payload.keys())
        d2=reemplazar_documento(documento=d,archivo=SimpleUploadedFile("v2.pdf",b"%PDF-1.4\n%%EOF",content_type="application/pdf"),usuario=self.u);self.assertEqual(events.count(),2)
        anular_documento(documento=d2,usuario=self.u);self.assertEqual(events.count(),3)

    def test_csv_filters_tenant_headers_and_injection(self):
        e,_=self._rfq();e.titulo="=FORMULA";e.save();self.client.force_login(self.u)
        response=self.client.get(reverse("compras:p2p_exportar"),{"estado":"BORRADOR"});self.assertEqual(response.status_code,200);body=response.content.decode("utf-8")
        self.assertIn("Duraci",body);self.assertIn("'=FORMULA",body);self.assertNotIn("archivo",body.lower());self.assertTrue(EventoAuditoria.objects.filter(empresa=self.e,descripcion__contains="Exportaci").exists())
