# Arquitectura visual

`base.html` es el shell único. Los tokens se cargan antes de base, layout, componentes, utilidades y responsive. Los templates de `templates/components/` son la API visual. `components.js` aporta comportamiento progresivo sin depender de reglas de negocio.

La jerarquía es: Enterprise Shell → encabezado de página → toolbar/filtros → contenido → acciones. Las páginas heredadas continúan funcionando por compatibilidad de selectores.
