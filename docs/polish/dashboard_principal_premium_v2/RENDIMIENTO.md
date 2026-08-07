# Rendimiento

El dashboard agrega métricas tenant-scoped y evita N+1 mediante agregaciones y una consulta acotada de actividad. Las métricas antiguas no visibles dejaron de consultar la base.

El contrato automatizado exige un máximo de 20 consultas para el render autenticado. Chart.js sólo se solicita cuando existen valores de producción y el gráfico sólo se inicializa si existe el canvas.
