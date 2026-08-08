# Permisos y seguridad

La regresión existente cubre usuario autorizado, sin permiso, otro tenant, objetos ajenos, IDOR, GET sobre POST, CSRF ausente/inválido e idempotencia. QA1 no modifica permisos.

El nuevo context processor sólo expone la empresa ya asociada al usuario autenticado mediante `obtener_empresa_usuario`; para anónimos devuelve `None`.
