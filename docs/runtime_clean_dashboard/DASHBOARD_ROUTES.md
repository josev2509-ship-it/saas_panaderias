# Rutas del dashboard

| Entrada | URL | URL name | View/resultado | Canónica |
|---|---|---|---|---|
| Raíz | `/` | `inicio` | `conduces.views.inicio` → `inicio.html` | Sí |
| Post-login | `/login/` | `login_usuario` | redirect a `/` | Sí |
| Marca/logo | shell | — | enlace a `/` | Sí |
| Panel principal | shell | `inicio` | enlace a `/` | Sí |
| Breadcrumb Inicio | shell | `inicio` | enlace a `/` | Sí |
| Workspace | `/core/workspace/` | `core:workspace_home` | conserva enlaces a `/` | Sí |

No existen aliases raíz `home`, `dashboard` o `panel`. `inicio_backup.html` no está enlazado ni renderizado.
