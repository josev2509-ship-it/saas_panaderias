# Manual operativo P2P 5C-3B

## Formularios y wizards

El endpoint `/compras/p2p/operar/<tipo>/` ofrece formularios tenant-safe para oferta, comparativo, adjudicación, orden, recepción, factura, solicitud de pago, pago y nota. Cada formulario limita sus relaciones a la empresa activa. Los formularios muestran el flujo por pasos y envían por POST con CSRF.

Wizard de compra: RFQ/proveedor → oferta → comparativo/escenario → adjudicación → orden. Wizard logístico: orden → recepción → cantidades/lotes/series → confirmación → InventoryEngine → asiento de recibido no facturado. Wizard financiero: orden/recepción → factura → CxP → solicitud → aprobación → pago → tesorería → contabilidad.

## Acciones

Las transiciones usan `/compras/p2p/accion/<recurso>/<id>/<accion>/` y solo aceptan POST. Incluyen envío/retiro/evaluación de oferta, recálculo/congelación, aprobación de adjudicación, aprobación/envío/aceptación/cancelación de orden, cierre de recepción, validación de factura, aprobación y reversión de pago. GET devuelve 405; permisos y empresa se validan antes de invocar servicios.

## Pagos y notas

Se soportan pagos parciales, totales y masivos; transferencia, cheque, depósito y compensación como método; banco o caja; referencia, retención, reversión, conciliación y desconciliación. Las salidas y reversiones usan exclusivamente `tesoreria.api`; los asientos y reversiones usan `contabilidad.api`.

Notas de crédito reducen CxP y crean asiento; notas de débito incrementan saldo y monto original. Anticipos se crean, contabilizan y aplican al saldo de una CxP compatible en proveedor y moneda.

## Recepción y devolución

Toda cantidad aceptada entra por `InventoryEngine.apply_movement`. La recepción se contabiliza por cantidad aceptada × precio de orden. La devolución sale por InventoryEngine, reduce la cantidad recibida y genera reversión contable por el valor de orden. Las claves idempotentes deben diferenciar cada recepción lógica.

## Exportaciones

POST `/compras/p2p/exportacion/` genera CSV sanitizado, XLSX válido, PDF o vista de impresión para RFQ, ofertas, comparativos, adjudicaciones, órdenes, recepciones, devoluciones, facturas, CxP, aging, pagos, conciliación, proveedores, ahorro y cumplimiento. Toda exportación se audita y las cuentas aparecen enmascaradas.

## Demo

`python manage.py generar_datos_demo_p2p --empresa ID --dry-run` muestra faltantes. Sin `--dry-run` completa exactamente los objetivos usando prefijo `DMP2P-`. Una segunda ejecución no duplica registros.

## E2E y recuperación

`python manage.py test compras.tests_p2p_operational.P2PTransactionalE2E.test_e2e_transaccional_48_pasos` ejecuta el ciclo sin admin. Ante un error, la transacción revierte inventario, CxP, tesorería y contabilidad. Un reintento debe conservar `Idempotency-Key`; un acto nuevo debe usar una clave nueva.
