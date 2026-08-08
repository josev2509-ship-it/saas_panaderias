# Rutas de demo

El inventario se obtiene del resolver en `core/tests/test_full_demo_routes.py`. Criterios de inclusión: patrón estático, nombre público, sesión autenticada, sin prefijo admin/media y sin verbos de mutación, carga, exportación, PDF o descarga. Criterio de éxito: exclusivamente HTTP 200/302.

Recorrido recomendado: login → dashboard → workspace → Comercial/CRM → clientes 360 → pedidos → Compras/P2P → inventario → producción → contabilidad/reportes → configuración.

Totales: 395 declaraciones de rutas del proyecto; 110 paths GET seguros y únicos; 0 fallos finales esperados. Los parámetros de detalle se recorren en la guía con fixtures demo y permanecen cubiertos por suites de dominio.
