# Inventario de botones

Inventario fuente: 267 `<button>`, 472 enlaces y 215 formularios. El test renderizado analiza todas las páginas GET seguras y clasifica controles por destino/método.

| Acción | Permiso/método esperado | Resultado | Duplicado |
|---|---|---|---|
| Navegar, filtrar, buscar, limpiar | GET | rutas resuelven | No |
| Crear/editar/guardar | permiso add/change; POST con CSRF | contrato verificado | No |
| Aprobar/rechazar/anular/revertir/eliminar | permiso de dominio; POST | suites negativas y E2E | No visible |
| Exportar/descargar/imprimir | permiso; GET/POST según contrato | suites de exportación | Alias O2C documentado |
| Importar/conciliar/desconciliar/pagar/cobrar | permiso; POST con CSRF/idempotencia | suites P2P/O2C | No |

Resultado automatizado: enlaces locales resuelven, formularios POST incluyen CSRF, métodos son GET/POST y botones no usan CSS inline.
