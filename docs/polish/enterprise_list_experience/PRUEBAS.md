# Pruebas

Cobertura contractual: compilación de templates, marca explícita por template, page header, command bar, búsqueda, columnas, densidad, mensajes vacíos diferenciados, responsive, conservación de acciones y ausencia de acciones destructivas compartidas.

Resultado dirigido: 11/11 pruebas P2 correctas, incluyendo los ocho presupuestos autenticados.

Certificación final del 7 de agosto de 2026:

- `manage.py check`: sin incidencias.
- `makemigrations --check --dry-run`: sin cambios detectados.
- `migrate --plan`: ninguna operación pendiente.
- `manage.py test`: 694 pruebas descubiertas; 679 ejecutadas correctamente y 1 omitida; 0 fallos y 0 errores.
- `git diff --check`: sin errores de whitespace.
