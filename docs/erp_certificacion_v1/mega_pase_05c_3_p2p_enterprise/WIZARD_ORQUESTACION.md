# Orquestación de wizards

`orquestar_paso` ejecuta servicios productivos dentro de una transacción, persiste los IDs en `WizardSession.datos.agregados` y reutiliza la referencia ante reintentos. Compra cubre expediente→orden; Recepción consolida líneas y usa exclusivamente InventoryEngine al cerrar; Factura/Pago cubre factura→movimiento de tesorería.
