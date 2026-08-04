# O2C, Contabilidad y Tesorería v1

La integración conserva la propiedad de datos: Comercial administra factura, CxC, notas, cobros y factoring; Contabilidad recibe documentos mediante `contabilidad.api`; Tesorería registra ingresos mediante `tesoreria.api`. `OperationContext` transporta empresa, actor, request e idempotencia.

Flujos certificados: factura/CxC/asiento; notas crédito y débito; cobros parciales; banco; extractos CSV/XLSX; matching y conciliación; factoring; reversión de cobros; reportes y exportaciones.

No se integran bancos externos ni se envían declaraciones. PostgreSQL continúa pendiente de validación específica de concurrencia y planes de ejecución.
