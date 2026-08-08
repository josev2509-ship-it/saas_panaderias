# Matriz funcional

| Cobertura | Método | Resultado |
|---|---|---|
| GET estático seguro | crawler autenticado, tenant con módulos activos | 110/110 en 200/302 |
| Navegación representativa | smoke D1 de 21 rutas | verde |
| Rutas parametrizadas | pruebas funcionales de cada dominio | preservadas |
| POST/transiciones | suite existente; nunca ejecutadas por crawler | preservadas |
| Descargas/PDF/exportaciones | excluidas por seguridad | NO APLICA al crawler |
| Migraciones | `makemigrations --check --dry-run` | sin cambios esperados |
