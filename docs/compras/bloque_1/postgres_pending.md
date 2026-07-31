# PostgreSQL pendiente

SQLite valida reglas y constraints, pero no certifica semántica real de
`select_for_update`. Falta ejecutar en PostgreSQL pruebas concurrentes de
numeración, principales, preferencia, RNC, transición e importación repetida.
