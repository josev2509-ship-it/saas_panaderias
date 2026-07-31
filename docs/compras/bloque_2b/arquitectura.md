# Arquitectura

Compras depende de Core, Catálogos, Documentos y la API pública de Workflow. Workflow nunca importa Compras. Modelos, selectores, formularios y vistas delegan transiciones a `compras.application.solicitudes.services`; los callbacks viven en el adaptador registrado por `ComprasConfig.ready()`.
