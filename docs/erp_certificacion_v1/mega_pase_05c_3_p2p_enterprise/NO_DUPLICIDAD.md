# No duplicidad

La sesión se bloquea con `select_for_update`. Cada paso consulta su referencia persistida antes de ejecutar. Los tokens de sesión y los contratos subyacentes mantienen idempotencia por empresa. Atrás no elimina referencias; cancelar o expirar conserva agregados válidos.
