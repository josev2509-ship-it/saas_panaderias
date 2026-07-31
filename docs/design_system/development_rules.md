# Reglas de desarrollo

Todo módulo nuevo debe reutilizar layout, encabezado, breadcrumbs, botones,
tarjetas, KPIs, filtros, tablas, formularios, estados, modales, mensajes, tabs,
auditoría y responsive.

Queda prohibido:

- crear colores o botones locales sin justificación;
- duplicar tablas o filtros;
- incluir estilos inline salvo un valor dinámico imposible de expresar de otra
  forma;
- diseñar dashboards aislados;
- usar Django Admin como UI final;
- agregar dependencias visuales pesadas;
- crear enlaces a funcionalidades inexistentes.

Un componente nuevo exige necesidad transversal, API documentada, ejemplo en
la guía visual, accesibilidad y prueba de render.
