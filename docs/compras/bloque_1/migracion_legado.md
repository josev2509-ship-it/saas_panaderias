# Migración legado

`migrar_proveedores_heredados` simula por defecto, requiere empresa explícita y
`--confirmar` para escribir. Es idempotente por correspondencia, no modifica
`Factura606`, no borra legado y no crea dual-write.
