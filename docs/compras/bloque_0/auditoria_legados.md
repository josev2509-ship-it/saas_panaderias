# Auditoría de legados

`contabilidad.Proveedor` no tiene empresa y es consumido por `Factura606`.
`inventario.OrdenCompra` tiene proveedor textual, numeración por último ID y
una recepción total. Productos y lotes también guardan proveedor textual.

Los comandos `auditar_proveedores_heredados` y
`auditar_ordenes_compra_heredadas` son de solo lectura. Los reportes deben
revisarse antes de cualquier migración.
