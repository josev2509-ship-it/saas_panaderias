# Rendimiento

La vista utiliza agregados SQL, filtros tenant y límites explícitos. El contrato automatizado exige un máximo de 20 consultas para una petición autenticada vacía. Las relaciones de agenda usan `select_related` y campos limitados con `only`.
