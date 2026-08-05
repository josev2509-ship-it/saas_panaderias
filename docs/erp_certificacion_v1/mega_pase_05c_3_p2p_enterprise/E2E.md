# E2E P2P — 48 pasos

1. Crear empresa tenant.
2. Configurar catálogos, moneda, banco y cuentas.
3. Crear proveedor activo y documentado.
4. Crear solicitud con líneas.
5. Aprobar solicitud por Workflow.
6. Crear expediente idempotente.
7. Crear RFQ y líneas.
8. Invitar proveedor y confirmar.
9. Registrar, enviar y versionar oferta.
10. Crear y recalcular comparativo.
11. Guardar escenario de ponderación.
12. Congelar y crear adjudicación.
13. Aprobar adjudicación.
14. Generar orden por proveedor.
15. Aprobar, enviar y aceptar orden.
16. Registrar recepción parcial.
17. Registrar recepción final.
18. Verificar entradas creadas por InventoryEngine.
19. Registrar y validar factura contra cantidades recibidas.
20. Verificar CxP y movimiento origen.
21. Solicitar, aprobar y aplicar pago parcial.
22. Aplicar pago final e idempotencia.
23. Verificar egresos por `tesoreria.api`.
24. Verificar asientos balanceados por `contabilidad.api`.
25. Consultar Diario, Mayor y Balanza.
26. Consultar dashboard tenant-safe.
27. Consultar reportes y exportación segura.
28. Verificar eventos versionados.
29. Verificar auditoría y trazabilidad.
30. Repetir operaciones con misma clave y comprobar ausencia de duplicados.

31. Verificar asiento de recepción.
32. Verificar asiento de factura.
33. Verificar asiento de nota.
34. Verificar asientos de pagos.
35. Consultar extracto.
36. Ejecutar matching.
37. Conciliar y desconciliar.
38. Consultar diario.
39. Consultar mayor.
40. Consultar balanza.
41. Abrir dashboard y drill-down.
42. Generar reportes CSV/XLSX/PDF.
43. Verificar EventBus.
44. Verificar auditoría.
45. Reintentar pago.
46. Confirmar idempotencia.
47. Forzar error de saldo.
48. Confirmar rollback.

El escenario ejecutable no depende del admin y vive en `compras.tests_p2p_operational.P2PTransactionalE2E.test_e2e_transaccional_48_pasos`.
