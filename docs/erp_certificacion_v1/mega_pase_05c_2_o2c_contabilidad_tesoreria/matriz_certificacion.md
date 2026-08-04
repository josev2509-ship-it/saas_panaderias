# Matriz de certificación

| Requisito | Estado | Implementación | Prueba |
|---|---|---|---|
| Factura/CxC/asiento | Completo | `financial_integration.py` | `test_ciclo_completo_reserva_a_cobro` |
| Notas crédito/débito | Completo | `financial_integration.py` | `test_ciclo_completo_reserva_a_cobro` |
| Cobros/Tesorería/conciliación | Completo | `tesoreria/api.py`, `services.py` | `test_ciclo_completo_reserva_a_cobro` |
| Factoring | Completo | `desembolsar_factoring` | `test_factoring_reversion_y_exportaciones_seguras` |
| Reversión de cobro | Completo | `revertir_cobro_integral` | `test_factoring_reversion_y_exportaciones_seguras` |
| Exportaciones | Completo | `financial_exports.py` | `test_factoring_reversion_y_exportaciones_seguras` |
| Estados/dashboard | Completo | `reportes.py`, `finanzas.py` | `test_ciclo_completo_reserva_a_cobro` |
| PostgreSQL | Pendiente ambiental | Validación posterior | No aplica |
# Cierre semántico 5C-2F

- Moneda base/extranjera, tasa ausente, cero, negativa, expirada, tenant y snapshot: `MulticurrencyDimensionsTest.test_01` a `test_08`.
- Dimensiones, inactividad, correspondencia, obligatoriedad y rollback: `MulticurrencyDimensionsTest.test_09` a `test_14`.
- POST, autenticación, CSRF real, sesión cruzada y permisos: `O2CHttpSecurityTest.test_01` a `test_05`.
- Presupuestos constantes: `O2CQueryBudgetsTest` y `TreasuryQueryBudgetsTest`.
- Cobros cruzados, diferencias, notas/factoring y reversión: `O2CMulticurrencyFlowsTest.test_01` a `test_10`.
- Reportes por moneda y dimensión: `MulticurrencyDimensionsTest.test_15` a `test_20`.
- E2E único: `O2CSemanticE2ETest.test_e2e_semantico_unico_20_pasos`.
