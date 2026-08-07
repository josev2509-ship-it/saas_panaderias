# Causa raíz

La línea del extracto bancario tenía fecha fija `2026-08-02`. El cobro DOP se creaba sin fecha, por lo que `registrar_cobro` asignaba `timezone.localdate()`.

Al ejecutarse el 6 de agosto de 2026, el movimiento quedaba fechado `2026-08-06`: cuatro días después del extracto. `sugerir_coincidencias` filtra primero por cuenta, tenant, estado, monto y una tolerancia de ±3 días; por ello no existían candidatos y la comparación exacta de referencia nunca llegaba a ejecutarse.

No había contaminación entre pruebas ni diferencias SQLite/PostgreSQL. El fallo era una dependencia del reloj en el fixture E2E.
