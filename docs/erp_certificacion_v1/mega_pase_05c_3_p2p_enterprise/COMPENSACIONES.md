# Compensaciones P2P

`CompensacionP2P` registra aplicaciones parciales o totales, moneda, tasa, monto base y diferencia cambiaria. La aplicación y reversión bloquean saldos, son idempotentes y contabilizan exclusivamente mediante `contabilidad.api.contabilizar_compensacion_p2p` y `revertir_compensacion_p2p`. Las cuentas se resuelven por `ReglaContabilizacion`; no hay códigos contables hardcodeados.
