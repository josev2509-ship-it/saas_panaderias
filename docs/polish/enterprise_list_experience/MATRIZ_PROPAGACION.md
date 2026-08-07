# Matriz de propagación

Leyenda: `✓` aplicado/validado; `N/A` sin ruta canónica de lista; `Legacy` pantalla de navegación o reporte, no tabla.

| Pantalla | Ruta | Template | Tipo | Header | Bar | Tabla | Filtros | Vacío | Resp. | Prueba | Evidencia | Estado | Observación |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Prospectos | `/comercial/crm/prospectos/` | `crm/lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Template compartido CRM |
| Oportunidades | `/comercial/crm/oportunidades/` | `crm/lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Template compartido CRM |
| Clientes | `/comercial/clientes/` | `clientes_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Migrada | Evidencia completa |
| Cotizaciones | `/comercial/cotizaciones/` | `o2c/lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Template compartido O2C |
| Pedidos | `/comercial/pedidos/` | `pedidos_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Migrada | Evidencia completa |
| Programación | `/comercial/programacion-comercial/` | `o2c/programacion.html` | Canónica | ✓ | ✓ | Tarjetas | ✓ | ✓ | ✓ | ✓ | — | Migrada | Vista temporal existente |
| Facturas Venta | `/comercial/o2c/facturas/` | `o2c_full/lista.html` | Canónica | ✓ | ✓ | ✓ | Local | ✓ | ✓ | ✓ | ✓ | Migrada | Evidencia completa |
| CxC | `/comercial/o2c/cxc/` | `o2c_full/lista.html` | Canónica | ✓ | ✓ | ✓ | Local | ✓ | ✓ | ✓ | ✓ | Migrada | Evidencia completa |
| Cobros | `/comercial/o2c/cobros/` | `o2c_full/lista.html` | Canónica | ✓ | ✓ | ✓ | Local | ✓ | ✓ | ✓ | — | Migrada | Acciones preservadas |
| Proveedores | `/compras/proveedores/` | `compras/lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Migrada | Evidencia completa |
| Solicitudes | `/compras/solicitudes/` | `solicitudes/lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Permisos preservados |
| Expedientes | `/compras/expedientes/` | `expedientes/lista.html` | Canónica | ✓ | ✓ | ✓ | Local | ✓ | ✓ | ✓ | — | Migrada | Exportación P2P existente |
| RFQ | `/compras/rfq/` | `rfq/lista.html` | Canónica | ✓ | ✓ | ✓ | Local | ✓ | ✓ | ✓ | — | Migrada | Sin acciones nuevas |
| Ofertas | `/compras/p2p/ofertas/` | `p2p/recurso_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Recurso compartido |
| Comparativos | `/compras/p2p/comparativos/` | `p2p/recurso_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Recurso compartido |
| Adjudicaciones | `/compras/p2p/adjudicaciones/` | `p2p/recurso_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Recurso compartido |
| Órdenes Compra | `/compras/p2p/ordenes/` | `p2p/recurso_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Migrada | Evidencia completa |
| Recepciones | `/compras/p2p/recepciones/` | `p2p/recurso_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Migrada | Evidencia completa |
| Facturas Proveedor | `/compras/p2p/facturas/` | `p2p/recurso_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Recurso compartido |
| CxP | `/compras/p2p/cxp/` | `p2p/recurso_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Migrada | Evidencia completa |
| Pagos | `/compras/p2p/pagos/` | `p2p/recurso_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Recurso compartido |
| Conduces | `/buscar-conduces/` | `buscar_conduces.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Acciones existentes |
| Despachos | `/comercial/o2c/despachos/` | `o2c_full/lista.html` | Canónica | ✓ | ✓ | ✓ | Local | ✓ | ✓ | ✓ | — | Migrada | Acción emitir conduce preservada |
| Entregas | `/comercial/o2c/entregas/` | `o2c_full/lista.html` | Canónica | ✓ | ✓ | ✓ | Local | ✓ | ✓ | ✓ | — | Migrada | Acción facturar preservada |
| Incidencias | — | — | N/A | N/A | N/A | N/A | N/A | N/A | N/A | ✓ | — | NO APLICA | Sin ruta canónica |
| Productos | `/inventario/productos/` | `inventario/productos.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Migrada | Evidencia completa |
| Materias primas | `/inventario/productos/` | `inventario/productos.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Misma entidad con categoría |
| Movimientos | `/inventario/movimientos/` | `inventario/movimientos.html` | Canónica | ✓ | ✓ | ✓ | Local | ✓ | ✓ | ✓ | — | Migrada | Queryset ya optimizado |
| Lotes | — | — | N/A | N/A | N/A | N/A | N/A | N/A | N/A | ✓ | — | NO APLICA | Sin lista independiente |
| Vencimientos | — | — | N/A | N/A | N/A | N/A | N/A | N/A | N/A | ✓ | — | NO APLICA | Sin lista independiente |
| Planificación producción | `/inventario/produccion/planes/` | `planes_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Acciones existentes |
| Órdenes producción | `/inventario/produccion/ordenes/` | `ordenes_lista.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Migrada | Acciones existentes |
| Necesidades | `/inventario/produccion/necesidades/` | `necesidades.html` | Canónica | ✓ | ✓ | ✓ | Local | ✓ | ✓ | ✓ | — | Migrada | Sólo lectura |
| Control calidad | — | — | N/A | N/A | N/A | N/A | N/A | N/A | N/A | ✓ | — | NO APLICA | Sin ruta canónica |
| Tesorería | — | — | N/A | N/A | N/A | N/A | N/A | N/A | N/A | ✓ | — | NO APLICA | Sin lista independiente |
| Bancos/cajas | — | — | N/A | N/A | N/A | N/A | N/A | N/A | N/A | ✓ | — | NO APLICA | Sin lista independiente |
| Conciliaciones | `/compras/p2p/cierre/conciliaciones/` | `p2p/finance_list.html` | Canónica | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Migrada | Evidencia completa |
| Asientos | — | — | N/A | N/A | N/A | N/A | N/A | N/A | N/A | ✓ | — | NO APLICA | Sin lista independiente |
| Estados financieros | `/contabilidad/reportes/` | `reportes_financieros.html` | Legacy | N/A | N/A | N/A | propios | propios | ✓ | ✓ | — | Fuera | Selector de reportes, no lista |
| Reportes principales | `/contabilidad/reportes/` | `reportes_financieros.html` | Legacy | N/A | N/A | N/A | propios | propios | ✓ | ✓ | — | Fuera | No sustituido por tabla ficticia |
