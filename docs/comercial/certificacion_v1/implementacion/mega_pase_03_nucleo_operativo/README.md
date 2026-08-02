# Mega Pase 03 — Núcleo comercial operativo

## Arquitectura y alcance

El núcleo implementa Cliente 360, capa `ProductoComercial`, pricing declarativo, cotizaciones versionadas, conversión idempotente a pedidos y programación comercial. Los servicios reciben `OperationContext`, bloquean cruces de empresa, registran auditoría y publican eventos con payload seguro. Comercial solo consulta/referencia `ProductoInventario`: no modifica stock, costo, reservas ni `InventoryEngine`.

## Cliente 360, riesgo y crédito

Cliente conserva su identidad histórica y añade segmentación, canal, vendedor/equipo/zona/ruta, moneda, condiciones, exposición, riesgo explicable 0–100 y estados empresariales. Los cambios de estado, límite y riesgo pasan por servicios con permisos. Contactos y direcciones cubren facturación, compras, cobranza, recepción, fiscal, entrega, cobro y sucursal. La eliminación física está prohibida.

## Producto y pricing

`ProductoComercial` es una relación 1:1 con inventario. Listas versionadas y sus detalles admiten ámbito por cliente/segmento/canal/zona, volumen, vigencia y prioridad. Reglas y promociones usan JSON declarativo, nunca `eval`. El resolvedor usa `Decimal`, produce explicación, warnings, blockers y hash SHA-256 reproducible; las prioridades ambiguas bloquean la cotización.

## Cotizaciones, pedidos y programación

Las cotizaciones preservan snapshots de producto/precio/impuesto y un historial inmutable. Las transiciones críticas son POST y la conversión aceptada crea exactamente un pedido, con nueva numeración y vínculo 1:1. La aprobación vuelve a validar cliente y crédito. Programar o reprogramar publica demanda informativa; no genera producción ni reserva existencias.

## API, UI, documentos y seguridad

Las APIs retornan DTO/diccionarios, no QuerySets. Los selectores aplican `select_related`/`prefetch_related`. La UI utiliza el Design System e incluye dashboard, Cliente 360, productos, listas, simulador, cotizaciones, PDF, pedidos, programación y reportes/exportación. La allowlist documental admite Cliente, ProductoComercial, ListaPrecio, CotizacionVenta y Pedido. Se aplican autenticación, permisos granulares, CSRF, tenant estricto y protección de CSV.

## Operación, demo y rendimiento

Los doce comandos aceptan `--empresa`; los mutantes aceptan `--dry-run`. El generador demo crea datos sintéticos e idempotentes. Las vistas de consulta filtran por empresa y usan carga relacionada. En producción se recomienda PostgreSQL, pruebas de concurrencia con bloqueos reales, almacenamiento privado de documentos y observabilidad del EventBus.

## Manual de usuario

Complete primero Cliente 360 y active una lista con precios. Use el simulador antes de cotizar. Envíe la cotización a revisión, apruébela, márquela enviada y registre aceptación. Conviértala una vez a pedido, envíe el pedido a aprobación y programe su fecha. Los bloqueos de crédito o pricing deben resolverse mediante el permiso/Workflow correspondiente.

## Manual de administración

Asigne permisos comerciales por rol, configure moneda/impuestos/numeraciones, ejecute verificadores de integridad y vencimiento con `--dry-run`, revise auditoría/eventos y respalde antes de migrar. No habilite reservas, despacho, facturación, CxC ni cobros dentro de este pase.

## Riesgos y deuda técnica

- Validar concurrencia y planes de consulta bajo PostgreSQL; SQLite no reproduce locks de fila.
- El workflow excepcional queda integrado como punto de bloqueo, pero sus matrices de aprobación dependen de configuración empresarial.
- PDF/XLSX y responsive requieren validación visual por navegador en cada despliegue.
- Reserva, despacho, entrega, facturación, CxC y cobros pertenecen a pases futuros.

Véase [matriz de certificación](matriz_certificacion.md).
