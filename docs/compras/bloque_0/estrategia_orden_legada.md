# Estrategia de orden legada

La orden de Inventario queda identificada como legado de solo lectura. Se
conservan listado, detalle, PDF y URLs. Creación, recálculo y edición se
bloquean. La recepción histórica permanece temporalmente para pendientes y
sigue usando `InventoryEngine`. No se renumeran ni recalculan registros.

`inventario/views.py` contiene definiciones duplicadas de creación y detalle;
la última definición es la activa al cargar URLs. Su consolidación se difiere
para evitar una reescritura riesgosa durante la congelación.
