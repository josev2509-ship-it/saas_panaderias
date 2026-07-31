# Migraciones

`compras.0002_solicitudes_compra_enterprise` crea encabezado, detalle, historial, permisos, índices y constraints sin modificar tablas legacy. Debe validarse con `migrate --plan`, base existente, base de pruebas vacía y `makemigrations --check --dry-run`.
