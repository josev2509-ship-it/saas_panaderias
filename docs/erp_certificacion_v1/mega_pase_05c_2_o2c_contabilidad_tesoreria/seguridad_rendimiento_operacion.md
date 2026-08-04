# Seguridad, rendimiento y manual operativo

Todas las búsquedas mutables incluyen empresa y usan bloqueo de fila. Exportar exige `comercial.exportar_cxc`; revertir exige `comercial.revertir_cobro`. Los payloads contienen identificadores, referencias y montos, nunca números bancarios completos.

Presupuesto: dashboard y reportes ejecutan agregaciones acotadas; Mayor/Diario usan `select_related`; XLSX usa escritura incremental; listados masivos deben paginarse en la vista. PDF se limita a 500 filas.

Operación: configure plan, cuentas, diario, periodo y reglas `FACTURA_VENTA`, `NOTA_CREDITO_VENTA`, `NOTA_DEBITO_VENTA`, `COBRO` y `FACTORING`. Desconcilie antes de revertir un cobro. Toda reversión exige motivo y conserva originales.
