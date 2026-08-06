# Arquitectura

- Vista: `conduces.views.inicio`, agregados tenant-scoped y de solo lectura.
- Template: `conduces/templates/inicio.html`.
- Estilos: `dashboard_premium.css`, cargado sólo por el Dashboard.
- Interacción: `dashboard_premium.js`, responsable de tabs y carga diferida de gráficos secundarios.
- Contratos: rutas y estados certificados; sin persistencia nueva.
