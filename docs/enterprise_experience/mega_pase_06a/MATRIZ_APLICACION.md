# Matriz de aplicación

| Componente | Archivo | Template/módulo | Estado | Prueba | Observación |
|---|---|---|---|---|---|
| Enterprise Shell | `panaderia_saas/templates/base.html` | Global | Aplicado | `test_experience_foundation` | Mantiene permisos y rutas |
| Navegación | `base.html`, `components.js` | Global | Aplicado | Menú/permisos/estado | Persistencia local |
| Dashboard | `conduces/templates/inicio.html` | Inicio | Aplicado | Dashboard/drill-down/vacío | Sin consultas nuevas |
| KPI Card | `components/kpi_card.html` | Dashboard | Disponible | Catálogo de componentes | Variante semántica |
| Enterprise Table | `components/enterprise_table.html` | Listados piloto | Base global | Tabla/responsive | Compatibilidad por selectores |
| Filter Bar | `components/filter_bar.html` | Listados piloto | Disponible | Catálogo de componentes | GET, sin lógica propia |
| Form Section | `components/form_section.html` | Formularios piloto | Base global | Formulario/responsive | Una columna móvil |
| Sticky Actions | `components/sticky_form_actions.html` | Formularios | Disponible | Catálogo de componentes | Respeta acciones de flujo |
| Empty State | `components/empty_state.html` | Dashboard/listados | Aplicado | Estado vacío | Evita gráficos gigantes |
| Iconografía | Sprite SVG en `base.html` | Global | Aplicado | Shell | Sin emojis permanentes |
