# Compras — Bloque 1

Esta aplicación contiene el maestro canónico multiempresa de proveedores. El
proveedor fiscal de `contabilidad` permanece intacto y solo se relaciona por
`ProveedorLegadoMap`; no existe dual-write.

Las transiciones operativas, principales, verificación bancaria e importación
se ejecutan mediante servicios. El número bancario nunca aparece en listados,
eventos ni exportaciones.
