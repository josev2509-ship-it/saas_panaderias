# Riesgos

- Algunas pantallas heredadas conservan markup específico; los selectores compatibles reducen divergencia, pero deben migrarse gradualmente al template Enterprise Table.
- Las métricas ejecutivas no disponibles se muestran vacías para evitar alterar consultas certificadas.
- El estado de navegación es local al navegador y no se sincroniza entre dispositivos.
- Chart.js permanece como dependencia del dashboard solo cuando hay datos; una política CSP futura debería alojarlo localmente.
- La validación visual autenticada requiere una sesión con permisos representativos; nunca deben usarse credenciales reales en capturas o documentación.
