# Etapa 01 — Configuración comercial

Esta etapa implementa la base operativa multiempresa de Comercial Enterprise v1: configuración, catálogos, vendedores, equipos, zonas, rutas, políticas versionadas, numeración, readiness, documentos, permisos, reportes y exportaciones.

## Arquitectura implementada

- `comercial.models`: configuración por empresa, catálogos, estructura comercial, políticas y snapshots inmutables.
- `comercial.application.configuracion`: mutaciones auditadas y eventos de configuración/catálogos/políticas.
- `comercial.application.configuracion_operativa`: secuencias, snapshots y readiness transaccionales.
- `comercial.api.configuracion`: DTOs y consulta de preparación sin efectos laterales por defecto.
- `comercial.configuracion_views`: UI autenticada, tenant-safe, acciones críticas POST y exportaciones.
- `documentos.services.MODELOS_PERMITIDOS`: allowlist explícita para configuración, vendedor, ruta y seis políticas.

## Operación

El dashboard está en `/comercial/configuracion/`. El porcentaje usa la fórmula `1.0` y persiste porcentaje, instante, resumen y estado listo/no listo. Evalúa empresa, moneda, impuestos, condiciones de pago, catálogos, estructura, seis políticas, catorce secuencias, Workflow, documentos, permisos, grupos e INABIE.

Las políticas activas no se editan desde UI. `versionar_politica()` conserva un snapshot JSON, SHA-256, motivo, actor y vínculo al snapshot anterior, y crea un borrador con versión incremental.

Las secuencias admitidas son COT, PED, PRG, DSP, CON, ENT, FAC, NCR, NDB, COB, DEV, COM, PROS y OPO. Se configuran con bloqueo de fila y la emisión usa `core.application.numbering`; nunca `count() + 1`.

## Seguridad y permisos

Todas las consultas de objetos se restringen por `empresa`. La empresa y campos técnicos no aparecen en formularios. Las mutaciones de estado requieren POST/CSRF. Los roles se crean idempotentemente y solo agregan permisos, sin retirar permisos externos. Las exportaciones requieren `exportar_configuracion_comercial`; el CSV neutraliza celdas que comienzan con `=`, `+`, `-` o `@`.

## Comandos

- `configurar_comercial --empresa ID [--dry-run]`
- `validar_configuracion_comercial --empresa ID [--dry-run]`
- `configurar_roles_comerciales [--empresa ID] [--dry-run]`
- `crear_catalogos_comerciales_base --empresa ID [--dry-run]`
- `configurar_secuencias_comerciales --empresa ID [--dry-run]`
- `verificar_integridad_catalogos_comerciales --empresa ID`
- `verificar_integridad_politicas_comerciales --empresa ID`
- `recalcular_preparacion_comercial --empresa ID [--dry-run]`
- `generar_datos_demo_configuracion_comercial --empresa ID [--dry-run] [--inabie]`

## Manual de usuario

Abra el dashboard, atienda las tarjetas rojas, configure catálogos y estructura, active políticas, complete las 14 numeraciones y ejecute Validar readiness. Los reportes se pueden imprimir o exportar a CSV, XLSX y PDF.

## Manual de administrador

Ejecute primero migraciones y `configurar_roles_comerciales`. Asigne grupos siguiendo mínimo privilegio. Use los comandos de integridad en despliegues y mantenga tipos documentales y Workflow activos. Los snapshots y auditoría no deben editarse desde admin.

## Migraciones y PostgreSQL

`0004` crea la configuración y catálogos; `0005` crea snapshots. SQLite cubre la suite funcional. Sigue siendo obligatoria la validación de concurrencia real de numeración en PostgreSQL antes de producción de alta carga.

## Rendimiento

Listados paginados a 25 elementos. El dashboard utiliza conteos agregados y limita cambios recientes a ocho. Las exportaciones actuales materializan el conjunto filtrado; para volúmenes masivos deberá migrarse XLSX/PDF a trabajo asíncrono.

## Riesgos y deuda técnica

- La concurrencia física solo queda certificable con PostgreSQL.
- PDF/XLSX dependen de ReportLab/openpyxl ya declarados en el entorno.
- La asignación de usuarios demo depende de usuarios existentes y puede producir menos de cinco vendedores.
- Los filtros avanzados de reportes son una base extensible; los dominios futuros añadirán filtros propios.
