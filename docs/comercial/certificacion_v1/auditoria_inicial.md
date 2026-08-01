# Auditoría inicial — Comercial Enterprise Certified v1.0

Base auditada: `7990ebf`. Rama: `comercial-enterprise-certified-v1`.

## Matriz de componentes

| Componente | Clasificación | Evidencia actual | Acción requerida |
|---|---|---|---|
| `comercial.Cliente` | AMPLIABLE | Tenant, código, crédito básico, contactos y direcciones | Normalizar identificación; segmentos, canal, vendedor/ruta canónicos, moneda, riesgo, exposición, documentos e historial. |
| `DireccionCliente` / `ContactoCliente` | REUTILIZABLE Y AMPLIABLE | Relaciones canónicas con Cliente | Añadir empresa explícita o validación derivada, auditoría, documentos y reglas de principal. |
| `comercial.Pedido` | AMPLIABLE | Cabecera, líneas, Decimal, numeración, estados, auditoría y programación básica | Expandir estados; origen cotización; crédito; reserva; despacho, entrega y facturación parcial; Workflow/EventBus. |
| `DetallePedido` | REUTILIZABLE Y AMPLIABLE | Producto canónico, cantidades, descuentos, impuestos y totales backend | Snapshots, unidades/factores, cantidades reservadas/despachadas/entregadas/facturadas/devueltas. |
| `HistorialEstadoPedido` | AMPLIABLE | Historial básico | Hacer inmutable; motivo, versión y metadata segura. |
| `SecuenciaDocumento` + Core numbering | DUPLICADO CONTROLADO | Comercial conserva tabla histórica; Core ya es motor certificado | Conmutar servicios nuevos a Core; mantener tabla existente durante migración. |
| Prospectos, oportunidades y actividades | REQUIERE MIGRACIÓN / NUEVO | No existen | Crear CRM multiempresa, servicios, pipeline, historial, documentos y eventos. |
| Listas de precios | REQUIERE MIGRACIÓN / NUEVO | Cliente/Pedido guardan texto libre | Crear modelos declarativos y `resolver_precio_comercial`; migrar valores existentes sin borrarlos. |
| Descuentos/promociones | REQUIERE MIGRACIÓN / NUEVO | Solo porcentaje manual en pedido | Motor declarativo sin `eval`, prioridades, vigencia, topes y Workflow de excepción. |
| Cotizaciones | REQUIERE MIGRACIÓN / NUEVO | No existen | Crear cabecera, líneas, versiones, PDF y conversión idempotente a pedido. |
| Programación | AMPLIABLE | Vistas diaria/semanal y enlace con Producción | Persistir agenda/reprogramación y separar disponibilidad de producción requerida. |
| `InventoryEngine` / reservas | REUTILIZABLE | API transaccional, idempotencia, eventos y reservas certificadas | Integrar mediante adaptador Comercial; no modificar motor ni stock directamente. |
| Producción desde pedidos | REUTILIZABLE Y AMPLIABLE | Planes/órdenes consumen pedidos aprobados | Mantener contratos; ampliar estados sin romper filtros actuales. |
| `conduces.Conduce` | LEGACY CONGELADO / RIESGO CRÍTICO | Vertical INABIE, numeración en `save()`, número global, centro obligatorio | No usar como núcleo general. Crear capa enterprise y estrategia expandir–migrar–conmutar; adaptador INABIE. |
| Entrega enterprise | REQUIERE MIGRACIÓN / NUEVO | Estado `entregado` en Conduce, sin evidencia completa | Crear entrega, diferencias, evidencias, devoluciones e historial. |
| `conduces.Factura` / `DetalleFactura` | LEGACY CONGELADO / RIESGO CRÍTICO | Factura INABIE por periodo y rango de conduces | Preservar. Crear FacturaVenta canónica relacionada con pedido/conduce/entrega y migración explícita. |
| `ComprobanteFiscal` / rangos NCF | AMPLIABLE CON MIGRACIÓN | NCF individual y rango gubernamental parcialmente tenant | Crear secuencia/rango canónico, consumo atómico, vigencia, alertas y auditoría; adaptar legacy. |
| Notas de crédito/débito | REQUIERE MIGRACIÓN / NUEVO | No existen | Crear agregados fiscales y efectos controlados en CxC. |
| `contabilidad.CuentaPorCobrar` | LEGACY CONGELADO | Texto, monto y bandera; sin tenant ni movimientos | No ampliar directamente. Crear CxC enterprise en Comercial y mapeo/migración. |
| Cobros/recibos/aplicaciones | REQUIERE MIGRACIÓN / NUEVO | No existe ciclo comercial canónico | Crear recibos, aplicaciones, anticipos, reversión y PDF. |
| `contabilidad.Factoring` | LEGACY CONGELADO | Modelo textual orientado a UMPI, sin tenant | Crear factoring comercial canónico; conservar y mapear histórico. |
| Devoluciones comerciales | REQUIERE MIGRACIÓN / NUEVO | No existe agregado canónico | Crear solicitud/aprobación/recepción y adaptador hacia InventoryEngine. |
| Comisiones | REQUIERE MIGRACIÓN / NUEVO | No existen | Crear planes, liquidaciones y reversión por notas. |
| Centros, menús y conduces INABIE | REUTILIZABLE COMO VERTICAL | `CentroEducativo`, `MenuDiario`, generación y PDFs existentes | Ocultar tras `modulo_inabie`; adaptar al núcleo sin duplicarlo. Actualmente Empresa no tiene flag dedicado. |
| Documentos | REUTILIZABLE Y AMPLIABLE | Allowlist, tenant, reemplazo, anulación, descarga y auditoría | Registrar agregados Comerciales y eventos específicos; no crear almacenamiento paralelo. |
| Workflow | REUTILIZABLE | Motor desacoplado con adaptadores y condiciones | Comercial importará Workflow mediante adaptadores; Workflow nunca importará Comercial. |
| EventBus | REUTILIZABLE | Outbox, idempotencia, retries y payload seguro | Crear catálogo Comercial sin consumidores ficticios. |
| Auditoría | REUTILIZABLE | Registro con empresa, usuario, request y objetos | Aplicar en todos los servicios y exportaciones. |
| OperationContext/idempotencia | REUTILIZABLE | Contrato certificado | Obligatorio en comandos y servicios críticos. |
| Design System | REUTILIZABLE | Componentes, navegación y responsive global | Aplicar a todas las pantallas; verificar breakpoints exigidos. |
| API interna | REQUIERE NUEVO | No hay contratos Comerciales estables | Crear fachada/selectores sin imports circulares. |
| Reportes/exportaciones | AMPLIABLE | Dashboards y CSV básicos | Añadir ciclo completo, separación por moneda, PDF/Excel/CSV/impresión y protección CSV. |

## Riesgos críticos

1. Existen dos mundos de cliente/factura/CxC: Comercial canónico parcial y legacy INABIE/Contabilidad. Una sustitución directa perdería compatibilidad.
2. `Conduce.save()` calcula numeración con consulta y máximo; no es apto para concurrencia enterprise.
3. `conduces.Factura` está acoplada a facturación INABIE por periodo, no a pedido/entrega general.
4. La CxC legacy carece de empresa, moneda, movimientos, aplicaciones y aging.
5. Los estados actuales de Pedido son subconjunto del contrato requerido y son consumidos por Producción.
6. `Empresa` carece de `modulo_inabie`; la visibilidad vertical no puede certificarse todavía.
7. No existen CRM, cotizaciones, precios, promociones, notas, cobros, devoluciones ni comisiones.

## Estrategia obligatoria

Aplicar **expandir → migrar → validar → conmutar → congelar → retirar en versión futura**. Los modelos legacy permanecen intactos mientras se crean agregados enterprise y adaptadores. Ningún servicio nuevo modificará stock directamente ni importará Comercial desde Workflow.

## Dictamen inicial

El módulo actual es una base comercial parcial reutilizable, no un ciclo enterprise certificable. La certificación exige implementar y probar los agregados faltantes, migración coexistente, PostgreSQL o bloqueo explícito de producción y el ciclo prospecto → cobro completo.
