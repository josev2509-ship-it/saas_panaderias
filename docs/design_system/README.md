# SASTRE ERP Enterprise Design System v1.0

Sistema visual para plantillas Django. Su objetivo es mantener confianza,
control y consistencia sin alterar lógica de negocio.

## Capas

1. `tokens.css`: decisiones visuales centrales.
2. `base.css`: tipografía, reset y foco.
3. `layout.css`: sidebar, topbar y estructura de página.
4. `components.css`: botones, tarjetas, tablas, formularios y estados.
5. `utilities.css`: composición mínima.
6. `responsive.css` y `print.css`: adaptaciones por medio.
7. `components.js`: navegación, menús, modales y doble envío.

La referencia viva está en `/core/design-system/` y requiere
`core.view_transaction_engine`.

## Auditoría inicial

Se encontraron 14 bloques de estilos, 37 atributos inline, 36 tablas y 93
formularios. Comercial tenía una hoja embebida; Centro Técnico e Inventario
definían variantes propias; la navegación mezclaba grupos, iconos y enlaces.
La estrategia elegida fue una capa compatible cargada después de los estilos
existentes y una migración gradual de ocho pantallas piloto.

Consulte los demás documentos de esta carpeta antes de crear una pantalla.
