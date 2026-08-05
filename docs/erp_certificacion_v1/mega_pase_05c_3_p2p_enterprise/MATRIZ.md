# Matriz de certificación

| Área | Evidencia | Estado |
|---|---|---|
| Ofertas | modelo, servicio, API, eventos, versiones | Implementado |
| Comparativo | scores, escenarios, snapshot | Implementado |
| Adjudicación | tipos, detalle, Workflow | Implementado |
| Orden | estados, detalle, versión, timeline | Implementado |
| Recepción | parciales, diferencias, lote, devolución | Implementado |
| Inventario | solo InventoryEngine | Implementado |
| Factura/CxP | match orden-recepción, aging | Implementado |
| Pago | solicitud, orden, aplicación | Implementado |
| Tesorería/Contabilidad | APIs exclusivas | Implementado |
| Documentos/Seguridad | allowlist y tenant | Implementado |
| UI | listas y 360 documental | Implementado con deuda visual |
| Demo masivo | 50/150/300/100/80/120/180/150/200, doble ejecución | Implementado |
| Operación HTTP | formularios, wizards, POST, CSRF, IDOR | Implementado |
| Exportaciones | CSV, XLSX, PDF e impresión | Implementado |
| E2E | 48 pasos transaccionales sin admin | Implementado |

La matriz automática conserva 200 contratos distribuidos 25/20/20/25/30/20/20/15/15/10 y agrega 8 pruebas funcionales: E2E, demo, HTTP/exportación, notas/anticipos, pago masivo/reversión, devolución, wizards/rendimiento y archivos exportados. Total nuevo P2P: 208.
