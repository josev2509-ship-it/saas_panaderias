# Railway pre-deployment

Servicio Django: `saas_panaderias`. Volumen persistente: montar en `/app/media`.

## Comandos

- Build: `python manage.py collectstatic --noinput`
- Pre-deploy: `python manage.py migrate --noinput`
- Start: `gunicorn panaderia_saas.wsgi:application --bind 0.0.0.0:$PORT`

## Variables requeridas

- `DEBUG=False`
- `SECRET_KEY=<valor seguro no versionado>`
- `DATABASE_URL=${{Postgres.DATABASE_URL}}`
- `ALLOWED_HOSTS=<dominio Railway>`
- `CSRF_TRUSTED_ORIGINS=https://<dominio Railway>`
- `MEDIA_ROOT=/app/media`
- `SEDL_CATALOG_ENABLED=False`

HSTS inicia en 3600 segundos. No habilitar `SECURE_HSTS_INCLUDE_SUBDOMAINS` ni
`SECURE_HSTS_PRELOAD` hasta confirmar que todos los subdominios operan solo con HTTPS.
Los archivos MEDIA se sirven mediante la vista Django protegida por autenticación,
tenant y permisos; WhiteNoise queda reservado para STATIC.
