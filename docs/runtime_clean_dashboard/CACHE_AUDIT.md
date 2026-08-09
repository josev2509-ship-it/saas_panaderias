# Auditoría de caché

- No existe configuración explícita de `CACHES`; Django usa caché local por proceso.
- No existe Redis ni caché compartida que invalidar.
- El runserver antiguo fue detenido y el puerto 8000 quedó libre.
- La limpieza final deja cero `__pycache__`, `.pyc` y `.pyo` fuera de `venv`.
- No se borraron sesiones funcionales, media ni bases reales.
- La validación anti-caché incluyó navegación nueva, URL única y reinicio del servidor.
