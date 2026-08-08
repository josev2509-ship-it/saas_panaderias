# Inventario de rutas

| Categoría | Total | Validación |
|---|---:|---|
| Declaraciones `path()` del proyecto | 395 | inspección de URLconfs |
| GET estáticas seguras normalizadas | 110 | HTTP 200/302, sin 404/500 |
| Alias deliberados finales | 2 | dashboard O2C y exportación O2C |
| Duplicados exactos retirados | 3 | nota aclaratoria, relación general, reportes O2C |

Rutas con parámetros y acciones POST permanecen cubiertas por las suites funcionales de cada dominio. Admin, media, logout, mutaciones, PDF y descargas no se ejecutan desde el crawler GET.
