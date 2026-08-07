# Matriz de certificación

| Criterio | Evidencia | Estado |
|---|---|---|
| Cinco capturas | `capturas/dashboard_*.png` | Cumple |
| Similitud con referencia | `COMPARACION_VISUAL.md` | Cumple |
| Sin bloques legacy | Pruebas estructurales y DOM | Cumple |
| Responsive | `RESPONSIVE.md` | Cumple |
| Máximo 20 consultas | Test de presupuesto | Cumple |
| Sin migraciones | `makemigrations --check --dry-run` y `migrate --plan` | Cumple |
| Pruebas de alcance | 19/19; subconjunto dirigido 17/17 | Cumple |
| Fallo global separado | Reproducido aisladamente en O2C; sin archivos O2C en el diff | Cumple por alcance |
| Working tree limpio | Verificación posterior al commit independiente | Pendiente de commit |

Decisión de Puerta A: certificado por alcance. El Dashboard supera su validación visual, estructural, responsive y de rendimiento; el fallo O2C queda separado para la Puerta B.
