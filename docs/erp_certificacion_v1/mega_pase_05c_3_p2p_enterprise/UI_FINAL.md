# UI final

Rutas enterprise: `/compras/p2p/wizard-enterprise/iniciar/compra/`, `recepcion/` y `factura-pago/`. Cada sesión usa UUID, exige permiso `compras.operar_wizard_p2p` y restringe empresa/usuario. La pantalla muestra paso activo, completados y estado terminal sin exponer payload sensible.
