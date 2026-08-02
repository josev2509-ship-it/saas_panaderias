# Matriz de certificación

| Requisito | Estado | Archivo / servicio | Prueba exacta | Observación |
|---|---|---|---|---|
| Configuración multiempresa | Implementado | `models.py`, `configuracion_views.py` | `test_dashboard_is_tenant_safe` | Empresa fuera del formulario |
| Catálogos y estructura | Implementado | `forms.py`, `configuracion.py` | `test_catalog_foreign_detail_is_404` | CRUD genérico tenant-safe |
| Políticas inmutables | Implementado | `configuracion_operativa.py` | `test_policy_snapshot_is_immutable` | SHA-256 y cadena anterior |
| 14 secuencias | Implementado | `configuracion_operativa.py` | `test_sequence_service_creates_all_types_idempotently` | Emisión reutiliza Core |
| Readiness 1.0 | Implementado | `api/configuracion.py` | `test_readiness_reports_blockers` | Persiste resumen y fecha |
| Documentos | Implementado | `documentos/services.py` | suite `documentos` | Allowlist explícita |
| Permisos y grupos | Implementado | `configurar_roles_comerciales.py` | `test_role_command_dry_run_does_not_write` | No retira permisos |
| CSV/XLSX/PDF/print | Implementado | `configuracion_views.exportar` | `test_export_requires_permission` | Tenant y auditoría |
| Seguridad HTTP | Implementado | `configuracion_views.py` | `test_state_change_requires_post` | POST/CSRF/403/404 |
| UI responsive | Implementado | `templates/comercial/configuracion` | render tests de dashboard | Sin scroll global |
| Admin | Implementado | `admin.py` | `manage.py check` | Snapshot solo lectura |
| PostgreSQL concurrente | Pendiente de entorno | `core/application/numbering.py` | `test_postgresql_concurrency` | Requiere PostgreSQL |
