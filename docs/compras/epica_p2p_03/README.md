# Épica P2P-03: Expediente y RFQ

Implementa el agregado Expediente de Compra, consolidación de solicitudes aprobadas y procesos RFQ con líneas, criterios, reglas, invitaciones, estados, documentos e indicadores deterministas. No incluye ofertas, precios de proveedor, comparativo, evaluación, adjudicación, órdenes, recepción, inventario ni CxP.

La dependencia permanece Compras → infraestructura compartida. Estados y operaciones críticas se ejecutan mediante servicios transaccionales y selectores tenant-safe.
