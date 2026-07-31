# Manual de usuario — Expediente de compra y RFQ

1. Abra una solicitud aprobada y use **Crear expediente**. El sistema conserva monto, moneda y estado como snapshot y evita crear dos expedientes para la misma solicitud.
2. En el expediente puede vincular otras solicitudes aprobadas compatibles, completar título, responsable, centro, tipo, prioridad y observaciones mientras sea editable, y luego **Abrir** y **Preparar RFQ**.
3. Cree la RFQ indicando objeto, calendario, entrega y condiciones comerciales. En BORRADOR genere las líneas desde las solicitudes y edite descripción, cantidad y entrega cuando sea necesario.
4. Agregue criterios de evaluación; los pesos activos deben sumar 100%. Agregue al menos una regla de participación obligatoria.
5. Invite proveedores activos y no bloqueados. Seleccione un contacto activo del mismo proveedor; solo puede cambiarlo antes de enviar la invitación.
6. Cargue al menos un documento activo en la RFQ. Las cargas, nuevas versiones, reemplazos y anulaciones quedan auditados y generan trazabilidad de dominio.
7. Envíe la RFQ a revisión. Puede devolverla a borrador con motivo. Al publicar se validan solicitudes, líneas, criterios, reglas, proveedores mínimos, condiciones, fechas y documento obligatorio.
8. Desde PUBLICADA use **Abrir**. Las invitaciones pueden marcarse enviadas y luego confirmadas, declinadas con motivo o sin respuesta. Los resultados finales no se contradicen ni se repiten.
9. Para extender una RFQ abierta indique una fecha posterior y un motivo. Para cerrar, primero resuelva todas las invitaciones pendientes. La cancelación exige motivo y no elimina relaciones ni historial.
10. Una RFQ cerrada, cancelada o desierta puede versionarse; la nueva versión inicia en BORRADOR y conserva las líneas activas.
11. El dashboard permite filtrar por responsable, centro de costo, tipo de compra, fechas y estado. Muestra competencia, invitaciones, extensiones, cancelaciones, salud, riesgo y totales por moneda. **Exportar CSV** aplica los mismos filtros y requiere permiso.
12. La salud es un indicador determinista de integridad y avance; el riesgo destaca expedientes que requieren atención. Ninguno sustituye la aprobación humana.

Todas las acciones de cambio usan POST y CSRF. Los mensajes de error explican la regla incumplida. El módulo no envía correo real ni expone portal de proveedor.
