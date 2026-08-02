# Matriz de certificación CRM

| Requisito | Estado | Archivo / servicio | Prueba exacta | Observación |
|---|---|---|---|---|
| Prospecto y duplicados | Implementado | `models.py`, `crear_prospecto` | `test_active_duplicate_is_rejected` | Normalización y PROS |
| Conversión idempotente | Implementado | `convertir_prospecto_a_cliente` | `test_conversion_is_qualified_and_idempotent` | Reutiliza Cliente |
| Oportunidad/pipeline | Implementado | `OportunidadComercial`, `pipeline` | `test_opportunity_weight_and_transition` | Separado por moneda |
| Actividades/agenda | Implementado | `ActividadComercial`, `agenda` | `test_mark_overdue` | Día/semana/mes |
| Historial inmutable | Implementado | tres historiales CRM | suite CRM | Admin solo lectura |
| Tenant e IDOR | Implementado | selectores/vistas | `test_cross_tenant_detail_is_404` | Filtro empresa obligatorio |
| Acciones POST | Implementado | `crm_views.py` | `test_actions_require_post` | CSRF de Django |
| Documentos | Implementado | `documentos/services.py` | `test_document_allowlist_is_tenant_safe` | Evento documental |
| API sin QuerySets | Implementado | `api/crm.py` | `test_api_returns_plain_contracts` | DTO/tuple/dict |
| UI/pipeline/agenda | Implementado | templates CRM | `test_detail_pipeline_agenda_and_reports_render` | Responsive |
| CSV/XLSX/PDF/print | Implementado | `crm_views.exportar` | `test_exports_csv_xlsx_pdf_print` | Sanitización CSV |
| Comandos | Implementado | `management/commands` | `test_commands_are_dry_run_and_idempotent` | `--empresa` y dry-run |
| Demo sin efectos en dry-run | Implementado | `generar_datos_demo_crm` | `test_demo_command_dry_run_does_not_write` | 30/15/40 planificados |
| Presupuesto dashboard | Implementado | `selectors_crm.py` | `test_dashboard_query_budget` | Máximo 20 consultas |
| PostgreSQL concurrente | Pendiente de entorno | numeración Core | suite PostgreSQL condicionada | No bloquea SQLite funcional |
