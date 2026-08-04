# POST y CSRF

Las rutas financieras críticas bajo `o2c/finanzas/` usan `require_POST`, autenticación y permisos Django. La empresa se obtiene de la sesión; nunca del cuerpo. CSRF se valida mediante middleware real y `Client(enforce_csrf_checks=True)`.

Cobertura: `comercial.tests_o2c_http_security.O2CHttpSecurityTest`.

Incluye aprobación/desembolso de factoring, conciliación/desconciliación, exportación auditada, reintento, reversión, anulación y notas. Se prueba GET=405, ausencia/token cruzado, sesión expirada, permiso denegado, operación válida con token y ausencia de eventos/auditoría en bloqueos.
