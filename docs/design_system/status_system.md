# Sistema visual de estados

El filtro `status_tone` está en `core.templatetags.design_system`.

- `neutral`: borrador, inactivo, archivado o estado desconocido.
- `progress`: pendiente, revisión, preparación, procesando.
- `success`: aprobado, completado, entregado, cobrado.
- `warning`: parcial, retrasado, diferencia, intervención.
- `danger`: rechazado, vencido, cancelado, fallido, bloqueado.
- `info`: activo e información contextual.

Los estados futuros reciben `neutral`; la plantilla nunca se rompe. Para
clasificar uno nuevo, actualice el mapa central y sus pruebas.

Workflow reutiliza tonos centrales para `EN_APROBACION`, `APROBADA`,
`RECHAZADA`, `DEVUELTA`, `CANCELADA` y `RETIRADA`.
