# Pruebas

- Dashboard canónico: 4 ejecutadas, 4 aprobadas.
- Regresión `core conduces`: 123 ejecutadas, 122 aprobadas y 1 omitida tras adaptar contratos a hashes.
- Suite global final sobre checkout reproducible: 700 ejecutadas, 699 aprobadas, 1 omitida, 0 fallidas; 824.864 s.
- `manage.py check`: sin incidencias.
- `makemigrations --check --dry-run`: sin cambios.

Las pruebas de activos usan `django.templatetags.static.static()` para validar nombres manifestados sin hardcodear hashes.
