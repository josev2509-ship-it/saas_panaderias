# Wizards P2P

Tres flujos persistentes: Compra (10 pasos), Recepción (10) y Factura/Pago (14). `WizardSession` limita por empresa y usuario; `WizardStepState` valida secuencia y reanudación; `WizardAuditTrail` es inmutable. Los payloads rechazan secretos, archivos, documentos y datos bancarios completos. Expiran a las 24 horas por defecto y soportan atrás, cancelación e idempotencia.
