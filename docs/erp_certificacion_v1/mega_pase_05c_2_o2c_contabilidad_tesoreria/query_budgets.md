# Presupuestos de consultas

| Operación | Máximo |
|---|---:|
| Dashboard financiero O2C | 18 |
| Paquete de estados contables | 6 |
| Matching de 30 líneas de tesorería | 6 |
| Facturas con filtros y notas (30 filas) | 4 |
| Cobros con aplicaciones (30 filas) | 4 |
| CxC con aging/exposición/moneda (30 filas) | 4 |

El matching ejecuta dos lecturas de datos y cuatro sentencias de control transaccional; el total no crece con las líneas. Listas usan `select_related`, `prefetch_related`, límite/paginación y agregados SQL. Los límites se verifican con `CaptureQueriesContext` en `comercial.tests_o2c_query_budgets` y `tesoreria.tests_o2c_query_budgets`.
