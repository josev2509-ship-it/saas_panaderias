# Migraciones

Aplicadas correctamente sobre la base local el 3 de agosto de 2026:

- `catalogos.0002_tasacambio`
- `comercial.0011_facturaventa_dimensiones_facturaventa_tasa_cambio_and_more`
- `comercial.0012_aplicacioncobro_diferencia_cambiaria_and_more`
- `contabilidad.0007_asientocontable_tasa_cambio_and_more`

`manage.py migrate` concluyó sin error y `makemigrations --check --dry-run` no detectó cambios pendientes en ese punto. Cada suite crea y migra además una base vacía.
