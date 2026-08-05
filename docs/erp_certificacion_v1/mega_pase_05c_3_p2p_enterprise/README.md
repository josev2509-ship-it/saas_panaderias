# Purchase to Pay Enterprise v1

## Alcance

El flujo certificado enlaza Solicitud, Expediente, RFQ, Invitación, Oferta, Comparativo, Adjudicación, Orden, Recepción, Inventario, Factura, CxP, Pago, Tesorería y Contabilidad. Todos los agregados operativos llevan `empresa`; los selectores y APIs exigen la empresa y devuelven objetos o listas materializadas, nunca `QuerySet` público.

## Arquitectura e integraciones

- `compras.application.p2p`: ofertas, comparativos, adjudicación, orden, recepción y devolución.
- `compras.application.financial`: factura, aging, solicitud/orden de pago y pago.
- `InventoryEngine.apply_movement`: única escritura de entradas y salidas de inventario.
- `tesoreria.api.registrar_egreso`: única fachada para la salida bancaria del pago.
- `contabilidad.api`: factura, nota, anticipo, pago y movimientos de inventario.
- `workflow`: adaptadores registrados desde Compras; Workflow no importa Compras.
- `EventBus` y auditoría: eventos versionados con empresa, agregado y clave idempotente; no incluyen archivos, credenciales ni datos bancarios completos.

## Dominios

Ofertas conservan líneas, aclaraciones, versiones e historial. El comparativo calcula scores económicos/técnicos deterministas, escenarios, recomendación explicable y snapshot congelado. La adjudicación soporta total, parcial, múltiple, desierta y cancelada. Las órdenes conservan detalle, versión, timeline y estados de recepción/facturación. La recepción registra aceptados, rechazados, lote, serie, vencimiento, inspección y devolución.

Facturas validan proveedor, orden, recepción, duplicado y cantidades recibidas. CxP conserva saldo, movimiento, aging, moneda y bloqueo. Los pagos pasan por solicitud, orden, aplicación, tesorería y asiento contable.

## Seguridad, documentos y UI

El allowlist documental incluye Oferta, Comparativo, Adjudicación, Orden, Recepción y Devolución; Factura, CxP y Orden de Pago ya están incluidos por Contabilidad. Las vistas filtran por empresa y los cambios de estado se realizan mediante servicios/POST. Los roles se crean con `configurar_p2p`. La navegación P2P expone Dashboard, Ofertas, Comparativos, Adjudicaciones, Órdenes, Recepciones, Devoluciones, Facturas, CxP y Pagos.

## Dashboard, reportes y exportaciones

El dashboard existente concentra expediente/RFQ y la capa P2P añade vistas operativas materializadas. Los reportes se apoyan en APIs tenant-safe y exportaciones con neutralización de fórmulas. Los KPIs previstos son compras del mes, órdenes abiertas, recepciones/facturas pendientes, saldo y aging CxP, riesgo de proveedor, tardanza y flujo de pagos.

## APIs y comandos

APIs: `ofertas`, `comparativos`, `adjudicaciones`, `ordenes`, `recepciones`, `facturas`, `cxp`, `pagos`. Comandos: `configurar_p2p`, `verificar_ofertas`, `recalcular_comparativos`, `vencer_ofertas`, verificadores de adjudicación/orden/recepción/factura/pago, `recalcular_cxp`, `actualizar_aging_cxp` y `generar_datos_demo_p2p`. Los modificadores admiten `--dry-run`; todos requieren `--empresa`.

## Migraciones y PostgreSQL

`compras.0005` crea los agregados P2P y permisos. `contabilidad.0008` amplía factura y CxP. La suite usa SQLite en desarrollo; antes de producción se debe repetir concurrencia, bloqueos `select_for_update`, índices y planes de consulta en PostgreSQL.

## Manual operativo

Configure roles, valide catálogos/moneda y ejecute el flujo desde Solicitud. No edite existencias, movimientos bancarios o asientos desde Compras. Ante un fallo, conserve la misma clave idempotente para reintentar. Las diferencias de recepción y facturas observadas deben recorrer Workflow.

## Deuda técnica

CSV, XLSX, PDF e impresión están cubiertos por la capa de exportación P2P. El comando demo mantiene `--dry-run`, genera el universo masivo y añade los escenarios narrativos de notas, anticipos, retenciones, certificados, compensaciones, matching y wizards. La certificación se ejecuta sobre SQLite; la validación PostgreSQL se registra como riesgo de entorno, no como funcionalidad ausente.
