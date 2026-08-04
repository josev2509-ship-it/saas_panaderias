# Rendimiento

El bloque combinado de 156 pruebas concluyó en 162.787 s. Reportes usan `select_related` y agregados; extractos usan `bulk_create`; XLSX usa modo incremental; PDF limita 500 filas. Pendiente: planes PostgreSQL y presupuestos de consultas bajo volumen UAT.
# Presupuestos 5C-2F

Los máximos ejecutables están en `query_budgets.md`. El matching bancario carga líneas y candidatos en bloque, eliminando las consultas por fila.

Las listas financieras se prueban con 30 registros y presupuestos de cuatro consultas, incluyendo relaciones y colecciones prefetched.
