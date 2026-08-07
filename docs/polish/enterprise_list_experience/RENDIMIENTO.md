# Rendimiento y presupuestos

| Lista | Medido | Límite | Estrategia existente |
|---|---:|---:|---|
| Clientes | 8 | 20 | paginación y filtros tenant |
| Pedidos | 10 | 24 | `select_related` de cliente/moneda y paginación |
| Órdenes compra | 5 | 18 | recurso P2P paginado a 50 |
| Facturas venta | 4 | 18 | queryset tenant limitado a 100 |
| CxC | 4 | 18 | queryset tenant limitado a 100 |
| CxP | 5 | 18 | recurso P2P paginado a 50 |
| Productos | 5 | 20 | relaciones de categoría/unidad y filtros tenant |
| Conciliaciones | 5 | 16 | queryset tenant y filtro de estado |

Mediciones realizadas con render autenticado sobre tenant aislado. El patrón visual no realiza solicitudes adicionales ni consultas: búsqueda, columnas y densidad operan en el DOM. No introduce N+1. Los querysets existentes conservan `select_related`/paginación.
