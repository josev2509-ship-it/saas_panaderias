# Exportaciones

CSV/XLSX/PDF se mantienen bajo permisos y tenant. QA1 corrigió el dispatcher O2C: tipos full (`facturas`, `cxc`, `cobros`, `entregas`, `despachos`) usan la implementación full; tipos legacy se delegan al exportador certificado existente.

Prueba dirigida: CSV de `clientes` y `facturas` responde 200 con `text/csv`. La suite valida neutralización de fórmulas para exportaciones que la soportan. Los temporales de pruebas se eliminan antes del commit.
