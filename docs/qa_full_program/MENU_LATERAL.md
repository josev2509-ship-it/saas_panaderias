# Menú lateral

Defecto corregido: Compras, Inventario y Workflow perdían el tenant del contexto y ocultaban grupos habilitados. El context processor `empresa_activa` entrega una única empresa al shell en todas las vistas autenticadas.

Verificación: mismo tenant, orden y nueve grupos en 24 pantallas críticas; ancho 272 px; scroll independiente; permisos y módulos siguen gobernando visibilidad.
