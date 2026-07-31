# Matriz de cumplimiento final P2P-03

| Requisito | Estado | Archivo / servicio / vista | Prueba exacta | Observación |
|---|---|---|---|---|
| Modelos, restricciones, numeración e historial | IMPLEMENTADO Y PROBADO | `compras/models.py`, `expedientes_rfq.py` | `test_expediente_is_idempotent_and_requires_approved`, `test_rfq_lines_validation_and_health` | Migraciones 0003/0004 inmutables. |
| Vínculo de solicitudes y snapshots | IMPLEMENTADO Y PROBADO | `crear_expediente_desde_solicitud`, `agregar_solicitud_a_expediente` | `test_expediente_is_idempotent_and_requires_approved` | Restricción por empresa y solicitud activa. |
| Transiciones, permisos, auditoría, eventos e historial | IMPLEMENTADO Y PROBADO | `compras/application/expedientes_rfq.py` | `test_event_and_audit_are_recorded`, `test_extension_close_cancel_and_pending_policy` | Estados terminales impiden repetición. |
| Publicación y validaciones previas | IMPLEMENTADO Y PROBADO | `validar_rfq_para_publicacion`, `publicar_rfq` | `test_publication_matrix_and_document_requirement`, `test_blocked_inactive_and_invalid_contacts_are_rejected` | Exige líneas, criterios 100%, reglas, competencia, condiciones y documento activo. |
| Evento y auditoría documental | IMPLEMENTADO Y PROBADO | `documentos/services.py`, `registrar_operacion_documental_p2p` | `test_document_event_is_single_and_payload_is_safe` | Carga, reemplazo/versión y anulación; descarga se audita sin evento de cambio. Payload sin archivo/ruta/contenido. |
| Invitaciones y cambio de contacto | IMPLEMENTADO Y PROBADO | servicios de invitación, `invitacion_accion`, `invitacion_contacto` | `test_invitation_state_conflicts_contact_and_motives` | Bloquea doble envío y resultados contradictorios. |
| Extensión, cierre y cancelación | IMPLEMENTADO Y PROBADO | servicios RFQ y vistas POST | `test_extension_close_cancel_and_pending_policy` | Cierre rechaza invitaciones pendientes; motivos y fechas validados. |
| Dashboard y reportes operativos | IMPLEMENTADO Y PROBADO | `_p2p_querysets`, `p2p_dashboard`, `p2p_dashboard.html` | `test_dashboard_and_get_action_security`, `test_csv_filters_tenant_headers_and_injection` | Filtros por responsable, centro, tipo, fechas y estado; KPIs de salud, riesgo, competencia, invitaciones y moneda. |
| CSV seguro y multiempresa | IMPLEMENTADO Y PROBADO | `p2p_exportar` | `test_csv_filters_tenant_headers_and_injection` | Permiso explícito, filtros, auditoría y neutralización de fórmulas. |
| Edición de borradores y líneas | IMPLEMENTADO Y PROBADO | formularios, `actualizar_expediente_borrador`, `actualizar_rfq_borrador`, `actualizar_linea_rfq` | suite `compras` y `manage.py check` | Empresa, número y estado no forman parte de formularios. |
| UI, enlaces, documentos e historial | IMPLEMENTADO Y PROBADO | templates `expedientes/`, `rfq/`, `compras/urls.py` | `test_dashboard_and_get_action_security`; resolución por `manage.py check` | Acciones mutables son POST+CSRF y se muestran por estado. |
| Ocho comandos operativos | IMPLEMENTADO Y PROBADO | `compras/management/commands/` | `test_config_command_is_idempotent` y suite `compras` | Configuración idempotente. |
| Concurrencia lógica e idempotencia | IMPLEMENTADO Y PROBADO | bloqueos `select_for_update`, constraints y EventBus | pruebas de doble creación, publicación, envío, cierre y evento documental | No equivale a certificación PostgreSQL. |
| PostgreSQL real | NO APLICA | — | — | Certificación explícitamente diferida; no se declara en esta épica. |
| Ofertas, comparativo, evaluación, adjudicación, orden, recepción y CxP | NO APLICA | — | — | Fuera del alcance P2P-03. |
