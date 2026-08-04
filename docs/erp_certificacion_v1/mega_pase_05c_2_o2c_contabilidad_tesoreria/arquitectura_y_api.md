# Arquitectura y API

- `comercial.application.financial_integration`: orquestación atómica sin escritura directa en tablas ajenas.
- `contabilidad.api`: validación de periodo, reglas, balance, simulación, DTO, auditoría y eventos.
- `tesoreria.api`: ingresos y reversos idempotentes con cuentas enmascaradas.
- `tesoreria.services`: importación, deduplicación, matching, conciliación y desconciliación.
- `comercial.application.financial_exports`: CSV protegido contra fórmulas, XLSX en modo escritura y PDF limitado.

Los errores de configuración o estado usan `ValidationError`; autorización usa `PermissionDenied`. Ninguna API pública devuelve `QuerySet`.
