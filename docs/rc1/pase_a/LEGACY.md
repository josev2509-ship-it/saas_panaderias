# Legacy

## Visible corregido

- `editar_conduce.html`
- `editar_factura.html`
- `editar_menu.html`
- `editar_producto_facturacion.html`

Los cuatro editores preservan campos, nombres POST, choices, CSRF, rutas y reglas existentes; ahora extienden `base.html` y usan componentes visuales del shell.

## Compatible/no visible

Las plantillas de impresión, documentos, correo, parciales y catálogo interno se mantienen separadas del shell por contrato. No se eliminó legacy sin evidencia.

Resultado: no queda legacy visible identificado por el clasificador en el recorrido demo estático.
