# Bloque 2B: Solicitud de compra enterprise

Primer documento de negocio de Compras integrado con Workflow. Registra una necesidad interna multiempresa, sus líneas, presupuesto estimado, documentos e historial. La aprobación autoriza continuar abastecimiento; no crea cotizaciones, órdenes, recepciones, cuentas por pagar ni movimientos de inventario.

La aplicación concentra reglas en servicios transaccionales, usa `OperationContext`, numeración `SC`, auditoría, EventBus y el registro explícito de adaptadores de Workflow.
