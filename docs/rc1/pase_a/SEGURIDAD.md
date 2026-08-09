# Seguridad

La auditoría reutiliza y ejecuta los contratos de seguridad existentes por dominio:

- autenticación y permisos;
- aislamiento de tenant e IDOR;
- rechazo de GET sobre acciones POST;
- CSRF en formularios mutables;
- documentos y recursos ajenos;
- acciones P2P/O2C y operaciones INABIE.

El crawler de formularios verifica que toda acción visible resuelva y que cada POST incluya token CSRF. La auditoría no cambió permisos ni relajó pruebas.
