# Auditoría static

| Elemento | Resultado |
|---|---|
| `STATIC_ROOT` | `staticfiles/` |
| Fuentes | `conduces/static/` y `design_system/static/` |
| Backend local/tests | `django.contrib.staticfiles.storage.StaticFilesStorage` |
| Backend producción | `whitenoise.storage.CompressedManifestStaticFilesStorage` mediante `STORAGES.staticfiles` |
| Primera recolección CL-1R | 167 copiados, 501 postprocesados |
| Segunda recolección | 167 sin cambios, 470 postprocesados |
| Manifiesto | `staticfiles/staticfiles.json`, versión 1.1 |

`STATIC_ROOT` fue comprobado como distinto de los directorios fuente antes de ejecutar `collectstatic --clear`.

`staticfiles/` se trata como salida reproducible: el manifiesto y los hashes se verificaron con `DEBUG=False` durante CL-1R y las salidas no versionadas se retiraron en la limpieza final. El despliegue debe ejecutar `collectstatic` con configuración de producción para reconstruirlos.
