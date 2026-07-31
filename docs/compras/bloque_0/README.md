# Compras · Bloque 0

Prepara seguridad modular, catálogos compartidos y convergencia de legados.
No incorpora solicitudes, cotizaciones, órdenes enterprise ni CxP.

Dependencias: `conduces.Empresa` → `catalogos`; Compras consumirá catálogos en
un bloque posterior. Inventario y Contabilidad conservan temporalmente sus
modelos heredados, sin dual-write.
