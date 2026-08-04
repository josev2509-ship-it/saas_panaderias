# Multimoneda y tasas

`TasaCambio` registra por empresa, moneda y vigencia una tasa Decimal positiva. La contabilización exige tasa 1 para moneda base y una tasa activa vigente para moneda extranjera. `FacturaVenta`, `ReciboCobro` y `AsientoContable` conservan el snapshot; la idempotencia compara también moneda y tasa. Los eventos y auditoría incluyen esos datos.

Cobertura: `contabilidad.tests_o2c_multicurrency_dimensions.MulticurrencyDimensionsTest`.

5C-2G añade `comercial.tests_o2c_multicurrency_flows.O2CMulticurrencyFlowsTest`: cobros USD→USD, USD→DOP y DOP→USD; diferencias positivas/negativas; cobro parcial; segunda tasa; contabilización y reversión de diferencia; snapshots de notas y factoring. Las cuentas de ganancia, pérdida y contrapartida se resuelven desde la regla `DIFERENCIA_CAMBIARIA`.
