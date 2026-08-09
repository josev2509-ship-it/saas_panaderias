# Cadena post-login

`POST /login/` → `login_usuario` → `authenticate` → sesión válida → `redirect("inicio")` → `GET /` → URL name `inicio` → `conduces.views.inicio` → `conduces/templates/inicio.html` → `data-dashboard-version="premium-v2"`.

La cadena fue verificada por pruebas automatizadas y mediante login real en el runtime temporal aislado.
