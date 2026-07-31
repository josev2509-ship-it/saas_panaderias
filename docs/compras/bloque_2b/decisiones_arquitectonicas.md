# Decisiones arquitectónicas

Se extiende la app Compras; no se crea motor paralelo. La dependencia es Compras hacia la API de Workflow. Los totales se persisten como proyección recalculable; líneas se retiran lógicamente; documentos usan GenericForeignKey existente; estados solo cambian mediante servicios o callbacks.
