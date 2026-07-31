# Design tokens

Los tokens viven en `design_system/css/tokens.css`.

- `--ds-primary-*`: navegación, foco y acciones.
- `--ds-bg`, `--ds-surface`, `--ds-border`: niveles de superficie.
- `--ds-text`, `--ds-text-muted`: jerarquía tipográfica.
- `--ds-success`, `--ds-warning`, `--ds-danger`, `--ds-info`: semántica.
- `--ds-space-*`: espaciado.
- `--ds-radius-*`, `--ds-shadow-*`: forma y elevación.
- `--ds-sidebar`, `--ds-content`, `--ds-z-*`: layout.

No agregue hexadecimales en plantillas. Un color nuevo requiere una necesidad
semántica transversal, contraste suficiente y actualización de esta guía.
Los nombres permiten sustituir valores futuros para modo oscuro sin cambiar
componentes.
