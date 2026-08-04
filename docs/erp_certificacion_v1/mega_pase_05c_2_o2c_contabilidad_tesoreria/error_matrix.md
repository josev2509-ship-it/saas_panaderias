# Matriz de errores

| Error | Resultado |
|---|---|
| Asiento desbalanceado, periodo/cuenta/diario/regla inválidos | Rechazado sin persistencia |
| Payload diferente bajo origen idempotente | Rechazado; defecto corregido |
| Sobreaplicación y nota excesiva | Rechazadas |
| Archivo/fila duplicados | Archivo idempotente; fila repetida rechazada |
| Tenant/IDOR/permisos | No encontrado o 403 de dominio |
