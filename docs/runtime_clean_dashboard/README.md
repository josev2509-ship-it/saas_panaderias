# Runtime limpio y dashboard canónico

CL-1R recuperó el cierre interrumpido de CL-1 sin descartar cambios fuente. Se restauraron exclusivamente los artefactos parciales de `staticfiles/admin/`, se regeneró `STATIC_ROOT` y se validó `/` (`inicio`) como ruta única del Dashboard Enterprise Premium v2.

Login, marca, Panel principal, breadcrumbs y Workspace convergen en `/`. No se modificó lógica de negocio ni se inició otro módulo.
