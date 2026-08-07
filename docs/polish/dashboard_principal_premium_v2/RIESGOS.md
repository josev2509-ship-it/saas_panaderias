# Riesgos

- Chart.js se carga desde CDN únicamente cuando hay datos; sin red, el resto del dashboard funciona pero el gráfico no se dibuja.
- En resoluciones estrechas la prioridad es legibilidad: los módulos se apilan y requieren desplazamiento vertical.
- Los KPI reflejan datos existentes; un tenant vacío muestra ceros y estados vacíos deliberados.
- La proyección mensual conserva su carácter estimado y se etiqueta como tal.

No se identificaron cambios en modelos, reglas de negocio, permisos ni contratos O2C/P2P.

## Seguimiento separado

La prueba semántica E2E de O2C falla al intentar tomar el primer elemento de una lista de coincidencias vacía. El problema fue aislado del Dashboard y se corrige únicamente en la Puerta B, mediante un commit posterior e independiente.
