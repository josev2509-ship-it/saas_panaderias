# Matriz visual completa

| Patrón | Cobertura | Implementación |
|---|---:|---|
| Dashboard | 100% visible | shell, grid y tarjetas |
| Lista | 100% visible | tabla contenida, empty state y responsive |
| Formulario | 100% visible | etiquetas, errores y acciones agrupadas por capa progresiva |
| Detalle / 360 | 100% crítica | header compacto, tarjetas, tabs existentes |
| Wizard | P2P | componentes ya certificados |
| Reporte | financiero/operativo | contenedor responsive |
| Importación / matching | rutas existentes | patrón enterprise existente; acciones no rastreadas por GET |
| Configuración | comercial/core | shell y formularios normalizados |
| Documento/PDF | preview existente | descarga excluida del crawler seguro |
| Vacío/error | global | `ds-demo-empty` progresivo |

Las 199 plantillas cargan la convergencia desde `base.html`. Se localizaron 37 archivos con CSS inline legado; la capa de compatibilidad evita roturas visuales, pero su retirada física es deuda no bloqueante y no se realizó para no ampliar riesgo.
