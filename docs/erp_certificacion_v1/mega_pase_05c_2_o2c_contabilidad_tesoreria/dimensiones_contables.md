# Dimensiones contables

Las líneas aceptan un mapa `CODIGO_DIMENSION: valor_id`. La API resuelve cada valor dentro de la empresa activa, comprueba dimensión activa y correspondencia de código. Las cuentas pueden exigir `CENTRO_COSTO` o `PROYECTO`. El mapa se propaga al asiento, eventos y auditoría; cualquier error revierte la transacción.

Cobertura: pruebas 09–14 de `MulticurrencyDimensionsTest`.

Notas y factoring heredan exactamente moneda, tasa y dimensiones de la factura. Cobros conservan dimensiones propias; asiento de cobro, diferencia y factoring las propagan. La reversión replica las líneas originales. Los filtros `centro`, `proyecto` y `sucursal` se resuelven en la API de reportes.
