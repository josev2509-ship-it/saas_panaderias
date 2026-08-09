# Rendimiento

Se revisaron los contratos de queries y el uso de `select_related`/`prefetch_related` en los dominios críticos. El código contiene 134 optimizaciones explícitas en los módulos auditados.

Presupuestos ejecutables existentes cubren Clientes (≤20), Pedidos (≤24), Órdenes de compra (≤18), Facturas (≤18), CxC (≤18), CxP (≤18), Productos (≤20) y Conciliaciones (≤16), además de CRM, O2C, P2P y dashboard de Conduces.

No se elevó ningún presupuesto durante este pase.
