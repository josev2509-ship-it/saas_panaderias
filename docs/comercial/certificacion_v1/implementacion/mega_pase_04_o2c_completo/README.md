# Mega Pase 04 — Order-to-Cash Enterprise

## Arquitectura

El ciclo enlaza Pedido aprobado → Reserva → Preparación → Picking → Packing → Despacho → Conduce canónico → Entrega → Factura → CxC → Cobro, con factoring opcional. Cada agregado pertenece a una empresa, usa numeración central, auditoría y eventos seguros. `InventoryEngine` continúa como única fachada capaz de reservar, liberar y confirmar salidas; Comercial no mantiene stock paralelo.

## Operación

- Reserva selecciona lotes FEFO/FIFO y admite resultado completo o parcial.
- Preparación, picking y packing conservan cantidades, diferencias, paquetes y trazabilidad.
- Despacho autoriza la salida mediante `InventoryEngine`; conduce y factura legacy permanecen intactos y se enlazan únicamente por adaptadores/identificadores opcionales.
- Entrega registra receptor, ubicación, evidencias e incidencias.
- Factura emitida crea automáticamente la CxC; cobros parciales o totales generan movimientos y actualizan ambos estados.
- Aging separa moneda y buckets corriente, 1–30, 31–60, 61–90, 91–120 y más de 120 días.
- Factoring se modela sin crear asientos contables.

## UI y API

El cockpit O2C y sus listas permiten ejecutar acciones críticas por POST/CSRF sin admin. Las ocho APIs internas retornan diccionarios/listas serializables, nunca QuerySets. Exportaciones disponibles en CSV, XLSX e impresión/PDF del navegador.

## Seguridad y rendimiento

Permisos granulares, tenant estricto, locks de fila e idempotencia protegen operaciones críticas. Selectores y listados se limitan por empresa. PostgreSQL queda recomendado para certificar concurrencia real, `select_for_update`, carga, almacenamiento privado de evidencias y observabilidad del EventBus.

## Coexistencia legacy

No se elimina ni sustituye `conduces.Conduce`, `conduces.Factura`, Contabilidad, Producción o P2P. `ConduceComercial` y `FacturaVenta` incluyen referencias opcionales de coexistencia. No se crean asientos contables.

## Manual de usuario

Abra Order-to-Cash, reserve un pedido aprobado y avance por preparación, picking, packing y despacho. Autorice la salida, emita el conduce, confirme la entrega, facture y aplique uno o varios cobros hasta cerrar el saldo.

## Manual de administración

Configure permisos, monedas, NCF y secuencias. Ejecute primero los comandos con `--dry-run`, supervise reservas expiradas, NCF, aging, promesas y conciliación de cobros. Nunca ajuste stock desde Comercial.

## Riesgos y deuda técnica

- PostgreSQL pendiente para validar contención real y planes de consulta.
- Firma/QR fiscal y e-CF requieren proveedor y normativa externa.
- Asientos, bancos y conciliación contable pertenecen a un pase posterior.
- La evidencia móvil necesita almacenamiento privado y políticas de retención en producción.

Véase la [matriz de certificación](matriz_certificacion.md).
