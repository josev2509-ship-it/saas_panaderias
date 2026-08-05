# Riesgos y operación

- La certificación local no sustituye pruebas de concurrencia e índices en PostgreSQL.
- El demo crea datos sintéticos identificados por prefijo `DMP2P-`; debe ejecutarse solo en empresas de demostración.
- Las exportaciones se generan en memoria; para volúmenes muy superiores al demo conviene procesamiento asíncrono.
- Las reglas contables deben configurarse por empresa antes de integrar facturas o pagos.
- Una orden adjudicada a múltiples proveedores debe generar una orden separada por proveedor.
- Reintentos deben conservar empresa, origen y clave idempotente.
- Nunca escribir stock, saldos bancarios o asientos directamente desde Compras.
- La retención queda trazada en la orden de pago; su liquidación fiscal especializada debe validarse con la configuración contable de cada país.
