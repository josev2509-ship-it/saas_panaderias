# Riesgos
| Riesgo | Nivel | Mitigación/dueño/aceptación |
|---|---|---|
| Doble factura/NCF/cobro | Crítico | Locks+constraints+idempotencia; Facturación; carrera PostgreSQL verde |
| Migración CxC/Factura | Crítico | conciliación y conmutación reversible; Comercial+Finanzas; diferencia cero |
| Stock directo | Crítico | solo InventoryEngine; Inventario; prueba sin escrituras ajenas |
| Conduce/INABIE coexistente | Alto | adaptador y dual-read temporal; Operaciones; paridad validada |
| Crédito/descuentos/moneda | Alto | snapshots+Workflow+separación moneda; Comercial; invariantes verdes |
| Factoring/datos personales | Alto | saldo bajo lock, permisos y retención; Finanzas/DPO |
| Rendimiento/pruebas/PostgreSQL | Alto | presupuestos, suite y bloqueo productivo hasta certificación; Arquitectura/QA |
