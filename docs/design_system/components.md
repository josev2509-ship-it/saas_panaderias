# Componentes

## Uso

- Botones: `.ds-btn` con variantes `--secondary`, `--tertiary`, `--danger`,
  `--success`, `--sm` y `--block`.
- Tarjetas: `.ds-card`; KPI con `.ds-kpi`.
- Estado: `{% include "components/status_badge.html" %}`.
- Tablas: `.table-responsive`; agregue `.ds-responsive-table` para tarjetas
  móviles y `data-label` en cada celda.
- Formularios: `.ds-form-grid`, ayudas `.ds-help` y errores `.ds-field-error`.
- Filtros: `.ds-filter`.
- Alertas: `.ds-alert` y variante semántica.
- Vacíos: `components/empty_state.html`.
- Paginación: `components/pagination.html`.
- Tabs, timeline, progreso, modal y menús están demostrados en la guía viva.

No use un botón peligro para navegación ni un modal cuando una pantalla de
confirmación necesita contexto extenso.
