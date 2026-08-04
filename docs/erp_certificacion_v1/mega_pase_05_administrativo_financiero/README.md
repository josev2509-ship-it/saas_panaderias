# Mega Pase 05 — Núcleo administrativo y financiero

## Arquitectura

El núcleo separa Contabilidad, Tesorería, Presupuesto, RRHH, Nómina, Activos y Mantenimiento. Cada agregado enterprise está asociado a empresa. Los modelos legacy de Contabilidad permanecen disponibles para coexistencia; ningún módulo consumidor crea asientos con ORM: usa `contabilidad.api`.

## Contabilidad y CxP

El motor soporta plan multinivel, periodos, diarios, asientos balanceados, dimensiones, lotes, reglas, cierres, reversiones e idempotencia por origen. La API pública cubre ventas, notas, cobros, proveedores, pagos, inventario, producción, nómina, depreciación, bajas, revaluaciones y ajustes. CxP incorpora facturas únicas, movimientos, cuotas, anticipos, solicitudes y órdenes de pago.

## Tesorería y presupuesto

Tesorería modela bancos, cajas, movimientos, transferencias, cheques, depósitos, conciliación, posición, flujo proyectado, préstamos, líneas e inversiones, sin conexión bancaria real. Presupuesto soporta versiones, escenarios, líneas, distribuciones, compromisos y ejecución contra asientos.

## RRHH, asistencia y nómina

RRHH cubre estructura, empleados, contratos, beneficios, documentos, vacaciones, licencias, asistencia, turnos, incidencias y horas extras. Nómina usa reglas JSON seguras y vigentes, snapshots, novedades, préstamos, embargos, recibos, regalía y prestaciones. Los valores TSS/ISR/INFOTEP son configurables; no se codifican tasas legales inmutables.

## Activos y mantenimiento

Activos cubre alta, ubicación, componentes, asignaciones, movimientos, mejoras, revaluación, línea recta, baja, seguros, garantías y documentos. Mantenimiento soporta planes por fecha/medidor, órdenes, tareas, repuestos y costos. Inventario solo se integra mediante `InventoryEngine`.

## Seguridad y operación

Tenant por empresa, permisos de Django, Workflow para aprobaciones, auditoría/eventos y documentos protegen operaciones críticas. La cuenta bancaria del empleado se almacena como dato cifrado/enmascarado por integración. UI responsive y APIs devuelven DTOs, nunca QuerySets.

## Límites y riesgos

- PostgreSQL pendiente para concurrencia real, particionado y planes de consulta.
- No hay conexión bancaria, biometría ni envío oficial a DGII.
- Certificación fiscal y tasas legales requieren parametrización y revisión profesional vigente.
- La contabilidad legacy se conserva hasta completar migración controlada.

Véase [matriz de certificación](matriz_certificacion.md).
