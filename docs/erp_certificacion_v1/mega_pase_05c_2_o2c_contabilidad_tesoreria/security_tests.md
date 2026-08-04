# Validación de seguridad

Se comprobaron filtros por empresa en factura, cobro, banco, conciliación, factoring y documentos; permisos de contabilización, reversión, factoring y exportación; enmascaramiento bancario; payload seguro; CSV tenant-safe y rechazo de claves con traversal, controles CRLF o markup.

Defecto corregido: `normalize_idempotency_key` ahora rechaza caracteres de control antes de normalizar espacios.
# Extensión 5C-2F

Se añadió validación HTTP real con `Client(enforce_csrf_checks=True)`: ausencia de cookie, token de otra sesión y usuario autenticado sin permiso producen 403; GET produce 405 antes de ejecutar la operación.

5C-2G añade exportación autorizada con token real, sesión expirada y aserciones de ausencia de EventoDominio/EventoAuditoria en solicitudes bloqueadas.
