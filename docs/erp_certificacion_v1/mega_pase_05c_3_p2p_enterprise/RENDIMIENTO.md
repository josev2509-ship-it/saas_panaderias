# Rendimiento y presupuestos

Las APIs usan `select_related` y `prefetch_related` antes de materializar listas, con límite predeterminado de 100; las vistas paginan a 50. Objetivos PostgreSQL: lista ≤ 12 consultas, detalle 360 ≤ 18, comparativo ≤ 15, aging ≤ 10, dashboard ≤ 20 y exportación sin N+1. Validar con datos equivalentes al volumen demo y p95 inferior a 800 ms para vistas, 2 s para comparativo y 5 s para exportaciones.
