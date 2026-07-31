# Core 2C: operacion, despliegue y cobertura

## Estado

Core 2C endurece el motor transaccional existente. No incorpora modulos de
compras, finanzas ni contabilidad. La suite SQLite y la instalacion limpia
estan verificadas. La concurrencia PostgreSQL permanece pendiente hasta contar
con un servidor y `DATABASE_URL`; un resultado SQLite nunca valida locks de
PostgreSQL.

## Configuracion

| Variable | Predeterminado | Uso |
|---|---:|---|
| `CORE_IDEMPOTENCY_STALE_SECONDS` | 900 | Timeout de operaciones INICIADA |
| `CORE_IDEMPOTENCY_MAX_RETRIES` | 3 | Intentos maximos |
| `CORE_DOUBLE_SUBMIT_WINDOW_SECONDS` | 5 | Ventana reservada para proteccion UI |
| `CORE_EVENT_PROCESSING_TIMEOUT_SECONDS` | 900 | Timeout de PROCESANDO |
| `CORE_EVENT_MAX_ATTEMPTS` | 5 | Intentos maximos por evento |
| `CORE_EVENT_BATCH_SIZE` | 100 | Lote de procesamiento |

## Idempotencia

Los clientes programaticos deben enviar `Idempotency-Key` y repetir la misma
clave despues de un timeout. La clave queda aislada por empresa y operacion, y
su hash impide reutilizarla con otro payload.

Sin encabezado, Core genera una clave ligada a un `request_id` aleatorio. Dos
operaciones nuevas con datos iguales no se deduplican permanentemente. Origen,
request ID, ruta, usuario, timestamp y operacion quedan en metadata.

```powershell
python manage.py recuperar_idempotencias
python manage.py recuperar_idempotencias --empresa 1 --limit 50
```

## InventoryEngine y conciliacion

`inventario.engine.InventoryEngine` es la API publica de escritura.
`inventario.inventario_avanzado_services` es implementacion interna conservada
por compatibilidad. Las vistas no lo importan directamente. El admin no permite
editar stock, cantidades de lotes, movimientos ni reservas.

La conciliacion deriva el saldo desde la apertura del primer movimiento y la
suma firmada del historial; no confia en el ultimo `saldo_posterior`. Tambien
calcula lotes, reservas y disponibilidad. Si los lotes no coinciden, el
resultado queda `REQUIERE_INTERVENCION`; Core no inventa distribuciones.

## Eventos

Los eventos son de trazabilidad o ejecutables. Un evento ejecutable sin
consumidor termina en error, nunca en procesado. Los bloqueados pueden
recuperarse por timeout. `SaldoReconstruido` genera seguimiento en auditoria.

```powershell
python manage.py procesar_eventos_dominio
python manage.py procesar_eventos_dominio --empresa 1 --limit 100
python manage.py recuperar_eventos_bloqueados
```

## Numeracion

Las secuencias usan `select_for_update`, empresa, tipo y periodo. Respetan
activacion, longitud y reinicio anual. Con `OperationContext`, la emision es
idempotente y registra usuario. El Centro Tecnico permite crear, consultar,
previsualizar y editar configuracion segura.

## Permisos y Centro Tecnico

```powershell
python manage.py configurar_roles_core
```

El comando crea idempotentemente Administrador de empresa, Supervisor tecnico,
Operador tecnico, Auditor y Consulta tecnica. Los querysets tecnicos del admin
se filtran por empresa para no superusuarios.

El Centro Tecnico vive en `/core/`; aparece en el menu solo con
`core.view_transaction_engine`. Tiene KPIs, paneles, listados, filtros,
paginacion, detalles, reintento de eventos, cierre controlado de idempotencias,
diagnostico, vista previa, reconstruccion y secuencias. Las mutaciones usan
POST, CSRF y permisos.

## Despliegue

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan
python manage.py migrate
python manage.py configurar_roles_core
python manage.py test core
python manage.py test inventario
python manage.py test comercial
python manage.py test
```

La migracion de esta fase es `core.0003_core2c_hardening`.

## PostgreSQL

Configure `DATABASE_URL` fuera del repositorio y ejecute:

```powershell
python manage.py test core.tests.test_postgresql_concurrency --verbosity 2
```

Las pruebas se omiten deliberadamente fuera de PostgreSQL.

## Solucion de problemas

- `INICIADA` antigua: ejecute `recuperar_idempotencias`.
- `PROCESANDO` antiguo: ejecute `recuperar_eventos_bloqueados`.
- Ejecutable sin consumidor: registre el manejador antes de reprocesar.
- Diferencia de lotes: conserve `REQUIERE_INTERVENCION`; no invente saldos.
- Permiso 403: configure roles y asigne el grupo correcto.

## Matriz real de cobertura

| Area | Estado | Evidencia / restriccion |
|---|---|---|
| OperationContext | IMPLEMENTADO Y PROBADO | Suite Core |
| Idempotencia y fallback | IMPLEMENTADO Y PROBADO | `test_core2c` |
| Recuperacion INICIADA | IMPLEMENTADO Y PROBADO | comando y prueba |
| InventoryEngine | IMPLEMENTADO Y PROBADO | busqueda y suites |
| Conciliacion independiente | IMPLEMENTADO Y PROBADO | posterior corrupto |
| Lotes inconsistentes | IMPLEMENTADO Y PROBADO | requiere intervencion |
| Eventos y recuperacion | IMPLEMENTADO Y PROBADO | comandos y suite Core |
| Numeracion SQLite | IMPLEMENTADO Y PROBADO | suites relacionadas |
| Roles reproducibles | IMPLEMENTADO Y PROBADO | comando idempotente |
| Centro Tecnico | IMPLEMENTADO Y PROBADO | render, permisos y enlaces |
| Instalacion limpia SQLite | IMPLEMENTADO Y PROBADO | migracion completa |
| Suite global SQLite | IMPLEMENTADO Y PROBADO | 153 ejecutadas, 1 omitida |
| Concurrencia PostgreSQL | IMPLEMENTADO, PENDIENTE DE PRUEBA | sin servidor |
| Exportacion tecnica | NO IMPLEMENTADO | no bloquea integridad |
| Graficas historicas | PARCIAL | KPIs y paneles |
