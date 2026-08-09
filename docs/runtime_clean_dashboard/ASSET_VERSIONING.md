# Versionado de assets

Django 6 usa `StaticFilesStorage` en desarrollo/tests y `CompressedManifestStaticFilesStorage` cuando `DEBUG=False`. Se retiraron los querystrings manuales `?v=qa1`; en producción, `{% static %}` resuelve los hashes desde `staticfiles.json` sin hardcodearlos.

Activos verificados:

- `dashboard_premium.css` → `dashboard_premium.dce5ae50a049.css`
- `dashboard_premium.js` → `dashboard_premium.0c37640f5b44.js`
- `demo_unified.css` → `demo_unified.1f256c6a9ac6.css`
- `demo_unified.js` → `demo_unified.25f617201f7c.js`
- `enterprise_list.css` → `enterprise_list.d00b778a6620.css`
- `enterprise_list.js` → `enterprise_list.93bc7766b38c.js`
