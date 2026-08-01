# Concurrencia
Numeración/NCF/cobros/reservas/facturación usan atomic+select_for_update+unique constraints+idempotency key y revalidación bajo lock. Precio/descuento se resuelven contra versión publicada y detectan ambigüedad. Despacho, factoring, devolución y comisión bloquean raíz y saldos. PostgreSQL prueba carreras reales; SQLite solo lógica y constraints, nunca certificación productiva.
