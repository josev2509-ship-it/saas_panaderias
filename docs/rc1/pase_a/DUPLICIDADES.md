# Duplicidades

El resolver detectó dos rutas repetidas fuera de admin:

| Ruta | Clasificación | Decisión |
|---|---|---|
| `/comercial/o2c/` | ALIAS NECESARIO | Compatibilidad explícita entre superficies O2C; cubierta por prueba. |
| `/comercial/o2c/exportar/<str:tipo>/<str:formato>/` | ALIAS NECESARIO | Dispatch por tipo legacy/full; cubierto por prueba CSV. |

No se encontraron otros paths públicos duplicados. Los dashboards por dominio se clasifican como FUNCIONALIDAD DIFERENTE: resumen ejecutivo, CRM, Compras, Inventario, Producción, Contabilidad y Workflow tienen contratos y consumidores distintos.
