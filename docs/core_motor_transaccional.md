# Motor transaccional del ERP

## Propósito

`core` contiene contratos transversales para operaciones multiempresa: contexto,
excepciones, idempotencia, numeración, eventos, auditoría y conciliación. Los
módulos de negocio conservan sus modelos, pero ejecutan operaciones críticas a
través de servicios de aplicación.

## Capas

- `core.domain`: reglas puras, excepciones y eventos serializables.
- `core.application`: contexto, idempotencia, numeración, transacciones y bus.
- `core.infrastructure`: adaptación del módulo de auditoría existente.
- `inventario.engine.InventoryEngine`: única fachada autorizada para existencias.

## Fuente de verdad

`MovimientoInventario` es el historial inmutable. `ProductoInventario.stock_actual`
es un saldo operativo cacheado y `LoteInventario.cantidad_disponible` es el saldo
por lote. Todo movimiento aplicado guarda saldo anterior y posterior.

`MovimientoInventario.save()` únicamente persiste el registro. No actualiza
productos ni lotes.

`aplicado_por_servicio` se conserva temporalmente para compatibilidad con las
migraciones 0010/0011 y datos existentes. Es interno, no editable y no constituye
la barrera de seguridad: la protección real es la fachada, los permisos, la
inmutabilidad administrativa y la idempotencia transversal.

## Idempotencia

Cada operación crítica recibe un `OperationContext` con empresa y clave. El motor
registra el hash de la solicitud en `RegistroIdempotencia`. Repetir la misma clave
y carga devuelve el resultado; cambiar la carga produce conflicto.

## Numeración

`obtener_siguiente_numero` reutiliza la tabla histórica
`comercial.SecuenciaDocumento`, bloqueándola dentro de una transacción. Esto
mantiene los formatos PED, PLA y OP sin mover datos entre aplicaciones.

## Eventos

El bus es interno y síncrono. El registro `EventoDominio` funciona como outbox
local. El procesamiento se agenda con `transaction.on_commit`; el payload contiene
identificadores y valores serializables, nunca instancias Django.

## Auditoría

El adaptador de `core.infrastructure.audit_adapter` reutiliza
`auditoria.registrar_evento`, normaliza las llamadas y elimina claves sensibles.

## Conciliación y reconstrucción

El diagnóstico compara el último saldo histórico, el saldo cacheado y la suma de
lotes. La reconstrucción exige permiso y motivo, bloquea el producto, conserva
movimientos y crea `ConciliacionInventario` más auditoría.

## Ejemplo

```python
context = OperationContext(
    empresa=empresa,
    usuario=usuario,
    clave_idempotente="recepcion:42",
    referencia="OC-2026-000042",
)
movimiento = InventoryEngine.apply_movement(
    context=context,
    producto=producto,
    lote=lote,
    tipo="entrada",
    cantidad="25.0000",
)
```

## Reglas para módulos futuros

Las vistas validan entrada y llaman servicios. Los servicios resuelven empresa,
permisos, bloqueos, idempotencia, movimientos, auditoría y eventos. Los efectos
externos se programan después del commit.

SQLite permite comprobar restricciones e idempotencia lógica, pero no sustituye
pruebas reales de contención y bloqueo de filas en PostgreSQL.

## Dashboard y permisos

Las vistas bajo `/core/` muestran métricas, idempotencias, eventos, secuencias y
conciliaciones de la empresa activa. Las acciones de reintento, diagnóstico y
reconstrucción son POST. Los permisos sensibles no se asignan automáticamente.

## Compatibilidad temporal de secuencias

La tabla continúa en `comercial.SecuenciaDocumento` para preservar PED, PLA y OP.
Core es su única API de emisión. El modelo admite prefijo, longitud, estado,
reinicio anual, responsables y fecha de última emisión. Su ubicación en Comercial
es deuda técnica deliberada; no deben crearse otros motores de numeración.

## PostgreSQL

`core/tests/test_postgresql_concurrency.py` contiene escenarios de contención y se
omite automáticamente fuera de PostgreSQL. Antes de producción debe ejecutarse
contra la misma versión y nivel de aislamiento usados en despliegue. SQLite no
reproduce bloqueos de filas, deadlocks ni contención real.

## Matriz de 75 requisitos

| ID | Descripción | Archivo / clase / método | Estado |
|---:|---|---|---|
| 1 | Contexto exige empresa | `test_core.CoreMotorTest.test_operation_context_requires_company` | Cubierto |
| 2 | Valida usuario | `test_core.CoreMotorTest.test_operation_context_rejects_cross_company_user` | Cubierto |
| 3 | Metadata serializable | `test_core2b.CoreHardeningTest.test_operation_context_rejects_sensitive_or_unserializable_metadata` | Cubierto |
| 4 | Rechaza metadata sensible | mismo método del ID 3 | Cubierto |
| 5 | Excepciones seguras | `test_core2b.CoreHardeningTest.test_domain_exception_is_safe_and_serializable` | Cubierto |
| 6 | Reglas puras | `test_core2b.CoreHardeningTest.test_pure_hardening_rules` | Cubierto |
| 7 | Completada no se repite | `test_core.CoreMotorTest.test_idempotency_completed_is_not_new` | Cubierto |
| 8 | Payload igual devuelve resultado | `test_core.CoreMotorTest.test_engine_is_idempotent` | Cubierto |
| 9 | Payload distinto genera conflicto | `test_core.CoreMotorTest.test_engine_conflicting_request_is_rejected` | Cubierto |
| 10 | Misma clave entre empresas | `test_core.CoreMotorTest.test_idempotency_is_scoped_by_company` | Cubierto |
| 11 | Fallo registrado | `test_core.CoreMotorTest.test_engine_failure_rolls_back_and_is_recorded` | Cubierto |
| 12 | Reintento controlado | `test_core.CoreMotorTest.test_idempotency_failure_and_retry` | Cubierto |
| 13 | Operación iniciada bloqueada | `test_core.IdempotencyConcurrencyTest.test_unique_constraint_prevents_logical_duplicate` | Cubierto |
| 14 | Incremento de intentos | `test_core2b.CoreHardeningTest.test_failed_event_can_be_retried_once` | Cubierto |
| 15 | Resultado asociado | `test_core.CoreMotorTest.test_idempotency_completed_is_not_new` | Cubierto |
| 16 | Admin idempotencia inmutable | `test_core2b.CoreHardeningTest.test_idempotency_and_movement_admin_are_immutable` | Cubierto |
| 17 | Aislamiento empresarial | `test_core2b.CoreHardeningTest.test_cross_company_detail_is_not_visible` | Cubierto |
| 18 | Reserva idempotente | `inventario.tests_inventario_avanzado.test_reserva_es_idempotente` | Cubierto |
| 19 | Liberación idempotente | `inventario.tests_inventario_avanzado.test_liberar_reserva_es_idempotente` | Cubierto |
| 20 | Consumo idempotente | `inventario.tests_inventario_avanzado.test_consumo_repetido_no_duplica` | Cubierto |
| 21 | Merma idempotente | `inventario.tests_inventario_avanzado.test_merma_idempotente` | Cubierto |
| 22 | Devolución idempotente | `inventario.tests_inventario_avanzado.test_devolucion_idempotente` | Cubierto |
| 23 | Entrada terminada idempotente | `inventario.tests_inventario_avanzado.test_cierre_crea_lote_y_entrada_una_sola_vez` | Cubierto |
| 24 | Reversión idempotente | `inventario.tests_inventario_avanzado.test_reversion_idempotente_conserva_originales` | Cubierto |
| 25 | Reconstrucción idempotente | `test_core.CoreMotorTest.test_rebuild_corrects_cache_and_keeps_movements` | Cubierto |
| 26 | Secuencia empresarial | `test_core.CoreMotorTest.test_numbering_is_multi_company` | Cubierto |
| 27-32 | PED, PLA, OP, LOT, RES, MOV | `test_core2b.CoreHardeningTest.test_sequence_supports_current_and_future_types` | Cubierto |
| 33 | Prefijos futuros | mismo método del ID 27 | Cubierto |
| 34 | Longitud configurable | `test_core2b.CoreHardeningTest.test_sequence_length_and_annual_restart` | Cubierto |
| 35 | Secuencia activa | `test_core2b.CoreHardeningTest.test_inactive_sequence_is_blocked` | Cubierto |
| 36 | Reinicio anual | `test_core2b.CoreHardeningTest.test_sequence_length_and_annual_restart` | Cubierto |
| 37 | No reutilización | `test_core.CoreMotorTest.test_numbering_is_sequential_and_not_reused` | Cubierto |
| 38 | Vista previa | `test_core2b.CoreHardeningTest.test_preview_does_not_update_sequence` | Cubierto |
| 39 | Concurrencia lógica | `test_core.IdempotencyConcurrencyTest` y suite PostgreSQL | Cubierto |
| 40 | Empresa manipulada rechazada | `test_core.CoreMotorTest.test_engine_rejects_cross_company_product` | Cubierto |
| 41 | Evento registrado | `test_core.CoreMotorTest.test_event_is_registered_and_processed_after_commit` | Cubierto |
| 42 | Evento procesado | mismo método del ID 41 | Cubierto |
| 43 | Evento fallido | `test_core.CoreMotorTest.test_event_handler_failure_is_recorded` | Cubierto |
| 44 | Evento reintentado | `test_core2b.CoreHardeningTest.test_failed_event_can_be_retried_once` | Cubierto |
| 45 | Permiso de reintento | `test_core2b.CoreHardeningTest.test_all_critical_actions_reject_get` | Cubierto |
| 46 | Evento idempotente | `test_core.CoreMotorTest.test_event_is_idempotent` | Cubierto |
| 47 | Evento posterior al commit | `test_core.CoreMotorTest.test_event_is_registered_and_processed_after_commit` | Cubierto |
| 48 | Varios manejadores | `test_core2b.CoreHardeningTest.test_event_supports_multiple_handlers` | Cubierto |
| 49 | Payload seguro | `test_core2b.CoreHardeningTest.test_event_payload_rejects_django_objects` | Cubierto |
| 50 | Sin recursividad | unicidad de `EventoDominio` en `test_event_is_idempotent` | Cubierto |
| 51 | `Movimiento.save` no afecta | `test_core.CoreMotorTest.test_direct_movement_does_not_change_stock` | Cubierto |
| 52-55 | Producto, lote y saldos | `test_core.CoreMotorTest.test_engine_changes_product_and_lot_atomically` | Cubierto |
| 56 | Bloquea negativo | `inventario.tests_inventario_avanzado.test_movimiento_rechaza_stock_negativo` | Cubierto |
| 57 | Rollback completo | `test_core.CoreMotorTest.test_engine_failure_rolls_back_and_is_recorded` | Cubierto |
| 58 | Reserva no afecta stock | `inventario.tests_inventario_avanzado.test_reserva_no_modifica_stock_fisico` | Cubierto |
| 59 | Consumo reduce stock | `inventario.tests_inventario_avanzado.test_consumo_reduce_lote_stock_y_reserva` | Cubierto |
| 60 | Merma reduce según regla | `inventario.tests_inventario_avanzado.test_merma_idempotente` | Cubierto |
| 61 | Devolución incrementa | `inventario.tests_inventario_avanzado.test_devolucion_idempotente` | Cubierto |
| 62 | Producto terminado incrementa | `inventario.tests_inventario_avanzado.test_cierre_crea_lote_y_entrada_una_sola_vez` | Cubierto |
| 63-65 | Reversa, original y doble reversa | `inventario.tests_inventario_avanzado.test_reversion_idempotente_conserva_originales` | Cubierto |
| 66 | Ninguna vista crea movimientos | `test_core2b.CoreHardeningTest.test_no_view_creates_movements_or_writes_stock_directly` | Cubierto |
| 67 | Admin no crea movimientos | `test_core2b.CoreHardeningTest.test_idempotency_and_movement_admin_are_immutable` | Cubierto |
| 68 | Formularios sin saldo | `test_core.CoreMotorTest.test_forms_do_not_expose_company_or_stock` | Cubierto |
| 69 | Multiempresa | `test_core2b.CoreHardeningTest.test_cross_company_detail_is_not_visible` | Cubierto |
| 70 | Conciliación detecta | `test_core.CoreMotorTest.test_diagnosis_detects_difference_without_mutation` | Cubierto |
| 71 | Diagnóstico no modifica | mismo método del ID 70 | Cubierto |
| 72 | Reconstrucción exige permiso | `test_core.CoreMotorTest.test_rebuild_requires_permission_and_reason` | Cubierto |
| 73 | Acciones rechazan GET | `test_core2b.CoreHardeningTest.test_all_critical_actions_reject_get` | Cubierto |
| 74 | Sin permiso devuelve 403 | `test_core.CoreMotorTest.test_technical_view_without_permission_is_forbidden` | Cubierto |
| 75 | Regresión completa | comando `manage.py test` | Verificación final |

## PRÁCTICAS PROHIBIDAS

- modificar stock directamente;
- crear movimientos desde vistas;
- ejecutar lógica financiera o de inventario en señales;
- usar `count()` para numeración;
- eliminar movimientos históricos;
- publicar eventos antes del commit;
- confiar en una empresa enviada por POST;
- omitir la clave idempotente en operaciones críticas;
- editar saldos o movimientos aplicados desde el admin.
- modificar cantidades de lote directamente;
- crear movimientos reales desde formularios;
- capturar excepciones y continuar parcialmente;
- duplicar `InventoryEngine`;
- crear una segunda implementación de auditoría o numeración.
