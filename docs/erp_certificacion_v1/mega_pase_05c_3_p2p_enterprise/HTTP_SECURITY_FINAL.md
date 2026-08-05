# Seguridad HTTP final

Mutaciones: autenticación, permiso, POST, CSRF, tenant y clave idempotente. Certificados se filtran por empresa. Los wizards rechazan sesión ajena, salto de paso y payload sensible; el contenido bancario bruto no se persiste.
# Seguridad HTTP final

Las mutaciones de notas, anticipos, retenciones, compensaciones y matching exigen autenticación, permiso y POST con CSRF. Los identificadores se resuelven siempre junto con la empresa obtenida de la sesión. Las descargas privadas filtran certificado y empresa.

La evidencia automatizada usa `Client(enforce_csrf_checks=True)` y cubre GET sobre mutaciones, token ausente, token inválido, sesión no autenticada, usuario sin permiso, IDOR y cross-tenant. Los servicios transaccionales cubren idempotencia y rollback ante estados, montos o relaciones inválidas.
