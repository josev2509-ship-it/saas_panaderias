# Pruebas

Cobertura específica:

- render autenticado y aislamiento tenant;
- cuatro KPI y estructura v2;
- topbar, atención, producto de mañana, actividad, finanzas y seis acciones;
- estados vacíos honestos;
- ausencia de Hero y bloques legacy;
- rutas y visibilidad por módulos habilitados;
- contrato responsive;
- presupuesto máximo de 20 consultas;
- JavaScript condicional del gráfico.

## Resultado final

- Pruebas dirigidas del Dashboard: 17 ejecutadas, 17 correctas.
- Batería exacta de Puerta A (`conduces.tests` y `core.tests.test_experience_foundation`): 19 ejecutadas, 19 correctas.
- Suite global: 683 descubiertas; 668 ejecutadas; 1 omitida; 1 error.
- Error global: `comercial.tests_o2c_semantic_e2e.O2CSemanticE2ETest.test_e2e_semantico_unico_20_pasos`, `IndexError` al no obtener coincidencias de conciliación.

El error pertenece a O2C, fue reproducido de forma aislada y ningún archivo O2C forma parte del diff del Dashboard. La Puerta A autoriza por ello la certificación y el commit independientes por alcance.
