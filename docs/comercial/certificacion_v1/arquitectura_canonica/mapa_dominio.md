# Mapa de dominio
| Subdominio | Raíces | Dependencias permitidas | Prohibido |
|---|---|---|---|
| CRM | Prospecto, Oportunidad | Cliente, Documentos, Workflow | Facturar/reservar |
| Maestro | Cliente, Vendedor, Ruta | Catálogos, RRHH API | Stock/asientos |
| Pricing | ProductoComercial, ListaPrecio, Promoción | ProductoInventario lectura, Catálogos | Costos/stock |
| Preventa | CotizacionVenta | CRM, Pricing, Workflow | CxC directa |
| Ventas | Pedido, Programacion, ReservaComercial | Pricing, Inventory API, Producción API | Stock directo |
| Entrega | Despacho, ConduceCanónico, Entrega, Devolución | Pedido, Activos API, Inventory API | Factura legacy |
| Facturación | FacturaVenta, Notas, NCF | Entrega/Pedido, Catálogos | Asientos directos |
| CxC | CuentaPorCobrar, Recibo, Promesa, Cesión | Factura, Contabilidad por eventos | CxC legacy |
| Compensación | ComisionVenta | Ventas/Cobros, RRHH lectura | Nómina directa |
| INABIE | PerfilCentro, Menú, RelaciónPeriodo | Núcleo mediante IDs/API | Duplicar cliente/factura |
