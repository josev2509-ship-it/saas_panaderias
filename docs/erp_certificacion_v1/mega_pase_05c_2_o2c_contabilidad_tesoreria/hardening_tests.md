# Batería de hardening

Resultado dirigido: 80 pruebas nuevas, 80 aprobadas, 0 omitidas, 0 fallidas.

## Contabilidad — 25

`test_01_asiento_balanceado_valido`, `test_02_asiento_desbalanceado_rechazado`, `test_03_asiento_cero_rechazado`, `test_04_linea_doble_lado_rechazada`, `test_05_doble_contabilizacion_impedida`, `test_06_reintento_mismo_payload_estable`, `test_07_reintento_concepto_distinto_falla`, `test_08_reintento_total_distinto_falla`, `test_09_periodo_cerrado_bloquea`, `test_10_periodo_inexistente_bloquea`, `test_11_cuenta_faltante_bloquea`, `test_12_cuenta_inactiva_bloquea`, `test_13_cuenta_control_bloquea`, `test_14_diario_faltante_bloquea`, `test_15_regla_faltante`, `test_16_regla_ambigua`, `test_17_origen_cross_tenant`, `test_18_simulacion_sin_persistencia`, `test_19_trazabilidad_origen`, `test_20_auditoria_creada`, `test_21_evento_normalizado`, `test_22_evento_unico`, `test_23_reversion_balanceada`, `test_24_reversion_idempotente`, `test_25_cierre_y_reapertura`.

## Tesorería — 20

`test_01_movimiento_ingreso_valido`, `test_02_movimiento_duplicado_idempotente`, `test_03_movimiento_cross_tenant`, `test_04_caja_inexistente`, `test_05_banco_inexistente`, `test_06_banco_inactivo`, `test_07_cobro_efectivo_en_caja`, `test_08_transferencia_incrementa_banco`, `test_09_destino_doble_rechazado`, `test_10_monto_no_positivo_rechazado`, `test_11_reversion_no_conciliada`, `test_12_reversion_duplicada_idempotente`, `test_13_importacion_csv_valida`, `test_14_importacion_xlsx_valida`, `test_15_archivo_duplicado_idempotente`, `test_16_fila_duplicada_rechazada`, `test_17_matching_por_referencia`, `test_18_matching_por_monto_fecha`, `test_19_conciliar_y_desconciliar`, `test_20_cierre_evento_y_auditoria`.

## O2C financiero — 20

`test_01_factura_emitida_contabiliza`, `test_02_factura_reintento_asiento_unico`, `test_03_factura_anulada_no_contabiliza`, `test_04_factura_borrador_no_contabiliza`, `test_05_cxc_unica_por_factura`, `test_06_asiento_venta_unico`, `test_07_nota_credito_parcial`, `test_08_nota_credito_total`, `test_09_nota_credito_excesiva`, `test_10_nota_credito_idempotente`, `test_11_nota_debito_valida`, `test_12_nota_debito_idempotente`, `test_13_cobro_parcial`, `test_14_cobro_total`, `test_15_cobro_multiples_facturas`, `test_16_sobreaplicacion_bloqueada`, `test_17_integracion_cobro_idempotente`, `test_18_reversion_integral_idempotente`, `test_19_factoring_valido`, `test_20_factoring_duplicado_bloqueado`.

## Seguridad — 15

`test_01_cross_tenant_factura`, `test_02_cross_tenant_cobro`, `test_03_cross_tenant_tesoreria`, `test_04_cross_tenant_conciliacion`, `test_05_cross_tenant_factoring`, `test_06_idor_factura_inexistente`, `test_07_idor_documento`, `test_08_exportacion_tenant_safe`, `test_09_contabilizar_sin_permiso`, `test_10_reversion_sin_permiso`, `test_11_factoring_sin_permiso`, `test_12_exportacion_sin_permiso`, `test_13_numero_bancario_enmascarado`, `test_14_payload_sensible_rechazado`, `test_15_idempotency_maliciosa_rechazada`.
# Extensión semántica 5C-2F

Se agregaron 22 pruebas: 14 multimoneda/dimensiones, 5 HTTP/CSRF y 3 presupuestos de consultas.

5C-2G agrega 20 métodos ejecutables: 10 flujos multimoneda, 6 reportes moneda/dimensión, 3 ampliaciones HTTP/CSRF y un E2E único. Además amplía tres presupuestos existentes para listas financieras.
