# Datos demo

Ejecutar `python manage.py generar_demo_ready --empresa <id>` únicamente sobre una empresa destinada a demostración. `--dry-run` muestra objetivos y pipeline. El orquestador reutiliza generadores idempotentes CRM, configuración comercial, O2C, P2P y administrativos; los datos usan dominios `.invalid` y prefijos DEMO/DMP2P. No escribe stock directamente ni evita servicios certificados. Verificar los conteos objetivo antes de presentar.
