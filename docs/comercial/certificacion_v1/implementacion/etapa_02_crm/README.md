# Etapa 02 — CRM Enterprise v1

## Arquitectura

CRM se implementa dentro de `comercial` y reutiliza `OperationContext`, numeración Core, EventBus, auditoría, documentos, permisos y aislamiento por empresa. Workflow permanece desacoplado y optativo. No se introducen dependencias desde Workflow hacia Comercial.

Capas:

- `models.py`: FuenteProspecto, Prospecto, OportunidadComercial, ActividadComercial y tres historiales inmutables.
- `application/crm.py`: comandos transaccionales, locks, permisos, estados, conversión e idempotencia.
- `selectors_crm.py`: consultas optimizadas con `select_related`, agregados y filtros por tenant.
- `api/crm.py`: DTOs y contratos sin QuerySets.
- `crm_views.py`: dashboard, CRUD, pipeline, agenda, acciones masivas, reportes y exportaciones.

## Prospectos

PROS genera números mediante `core.application.numbering`. Identificación y teléfono se normalizan; identificación, correo y teléfono bloquean duplicados activos. Estados terminales no admiten edición ni eliminación física. La calificación, descarte, reasignación y conversión pasan por servicios auditados y emiten eventos versionados.

## Oportunidades y pipeline

OPO genera la numeración. Toda oportunidad exige prospecto o cliente de la empresa. El monto ponderado se calcula en backend. El grafo de etapas valida cada transición y GANADA, PERDIDA y CANCELADA son terminales. El pipeline separa monedas y agrega cantidad, monto, ponderado y probabilidad.

## Actividades y agenda

Las actividades exigen relación comercial y responsable de la empresa. Las fechas se validan, completar exige resultado y las actividades vencidas se marcan mediante servicio/comando. La agenda ofrece día, semana y mes, además de filtros por responsable, tipo y estado.

## Conversión

Solo CALIFICADO se convierte. La operación bloquea el prospecto, reutiliza Cliente si coincide RNC/correo, crea dirección/contacto cuando procede, mueve oportunidades abiertas, conserva actividades e historial y es idempotente.

## Documentos

La allowlist incluye Prospecto, OportunidadComercial y ActividadComercial. Carga, reemplazo/versionado y anulación usan el servicio documental existente, no exponen `archivo.url`, auditan y emiten `DocumentoCRMActualizado`.

## Eventos y auditoría

Se implementan eventos para altas, cambios, estados, etapas, reasignaciones, conversión, actividades, documentos y exportaciones. Los payloads incluyen `schema_version`, empresa, agregado y actor, sin datos sensibles. Cada mutación registra auditoría y los historiales no son editables ni eliminables.

## Permisos y grupos

Los modelos incorporan permisos granulares para calificar, descartar, convertir, reasignar, cambiar etapa, ganar, perder, cancelar, completar, reprogramar, exportar y administrar. `configurar_roles_comerciales` agrega permisos idempotentemente a los diez grupos existentes sin retirar permisos externos.

## UI y dashboard

El menú Comercial enlaza CRM, Prospectos, Pipeline y Agenda. Las vistas usan Design System, no contienen endpoints ficticios y son responsive a 320 px o más. Dashboard muestra conversión, estados, oportunidades, actividades, pipeline por moneda, vencidas y estancadas.

## Reportes y exportaciones

Reportes cubren estados, fuentes, responsables, pipeline, conversión y productividad mediante selectores agregados. CSV neutraliza fórmulas; XLSX usa openpyxl; PDF usa ReportLab; impresión tiene CSS específico. Todas las exportaciones son tenant-safe, autorizadas, auditadas y eventadas.

## API interna

Contratos disponibles: `obtener_prospecto`, `buscar_prospectos`, `crear_prospecto`, `calificar_prospecto`, `convertir_prospecto`, `obtener_oportunidad`, `crear_oportunidad`, `cambiar_etapa_oportunidad`, `obtener_pipeline`, `crear_actividad`, `obtener_agenda` y `obtener_resumen_crm`. Retornan dataclasses, tuplas, diccionarios o identificadores.

## Comandos y demo

- `configurar_crm --empresa ID [--dry-run]`
- `crear_fuentes_prospecto_base --empresa ID [--dry-run]`
- `marcar_actividades_vencidas --empresa ID [--dry-run]`
- `recalcular_pipeline --empresa ID [--dry-run]`
- `verificar_integridad_crm --empresa ID`
- `generar_datos_demo_crm --empresa ID [--dry-run]`

El demo crea hasta 30 prospectos, 15 oportunidades y 40 actividades consistentes, sin binarios.

## Migraciones, seguridad y rendimiento

La migración `0007` añade CRM sin modificar migraciones previas. Constraints e índices cubren tenant/número, estados, responsables y fechas. Las vistas filtran siempre por empresa, las acciones críticas son POST/CSRF, se rechaza IDOR/cross-tenant y los formularios excluyen empresa/campos técnicos. Listados se paginan a 25 y los selectores evitan N+1 críticos.

## Manual de usuario

Registre el prospecto, documente actividades, califíquelo, cree oportunidades y avance solo mediante acciones permitidas. Use Pipeline para priorizar monto ponderado y Agenda para seguimiento. Convierta a cliente únicamente cuando esté CALIFICADO.

## Manual de administrador

Aplique migraciones, ejecute `configurar_crm`, asigne los grupos de mínimo privilegio y programe `marcar_actividades_vencidas`. Ejecute `verificar_integridad_crm` y `recalcular_pipeline` después de importaciones controladas.

## PostgreSQL pendiente, riesgos y deuda técnica

- La exclusión lógica de duplicados se valida transaccionalmente; para carga concurrente extrema se recomienda índice funcional/constraint PostgreSQL sobre identificadores normalizados.
- La concurrencia de PROS/OPO depende del bloqueo de fila de Core y debe repetirse en PostgreSQL antes de producción de alta carga.
- No se envían notificaciones externas; solo se preparan eventos.
- Calendario gráfico drag-and-drop no es necesario para operar: la agenda y el cambio de etapa son server-side.
- Exportaciones masivas futuras deberían moverse a trabajos asíncronos.
