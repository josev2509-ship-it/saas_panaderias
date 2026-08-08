# Inventario total de pantallas

| Dominio | Módulos/pantallas | Rutas | Vista/template | Patrón | Estado visual | Estado funcional | Prioridad/evidencia |
|---|---|---|---|---|---|---|---|
| Experiencia | login, inicio, workspace, búsqueda, alertas, actividad, 360 | `/`, `/login/`, `/core/*` | `conduces` / `core` | dashboard, lista, 360 | Enterprise | GET verificado | Alta / login, dashboard |
| Comercial | dashboard, clientes, CRM, prospectos, oportunidades, productos, precios, cotizaciones, pedidos, O2C | `/comercial/*` | `comercial.views`, `crm_views`, `o2c_views`, `o2c_full_views` | dashboard, lista, formulario, detalle, 360 | Enterprise por shell | GET verificado; acciones por dominio | Crítica / clientes, 360, pedidos |
| Operaciones | centros, menús, conduces, facturación INABIE, cartas, calendario | rutas raíz | `conduces.views` / `conduces/templates` | lista, formulario, detalle, reporte | Enterprise por shell | GET verificado; PDF excluido | Crítica / conduce |
| Compras | proveedores, solicitudes, expedientes, RFQ, P2P, finanzas, cierre, wizards | `/compras/*` | `compras.views`, `p2p_*` | dashboard, lista, detalle, wizard | Enterprise | GET verificado | Crítica / compras |
| Inventario | productos, kardex, movimientos, recetas, préstamos, órdenes | `/inventario/*` | `inventario.views` | dashboard, lista, formulario, detalle | Enterprise por shell | GET verificado | Alta / inventario |
| Producción | dashboard, recetas, planes, órdenes, programación, necesidades | `/inventario/produccion/*` | `produccion_views` | dashboard, lista, detalle | Enterprise por shell | GET verificado | Alta / producción |
| Finanzas | contabilidad, CxC, CxP, factoring, presupuestos y reportes | `/contabilidad/*`, cierres P2P/O2C | `contabilidad.views` y vistas financieras | dashboard, lista, reporte | Enterprise; 4 corregidas | GET verificado | Crítica / finanzas, reportes |
| Configuración | comercial, catálogos, secuencias, empresa, usuarios, workflow | `/comercial/configuracion/*`, `/catalogos/*`, `/workflow/*`, `/mi-empresa/*` | vistas de cada dominio | configuración, lista, formulario | Enterprise por shell | GET verificado | Media |
| Documentos | lista, objeto, detalle, carga, reemplazo, descarga | `/documentos/*` | `documentos.views` | lista, detalle, documento | Enterprise por shell | lista GET; operaciones excluidas | Media |
| Administración Django | administración técnica | `/admin/*` | Django Admin | NO APLICA D3 | NO APLICA | Fuera del menú demo | Baja |

Clasificación: pantallas visibles = **YA ENTERPRISE** por template específico o por Enterprise Shell; dashboard O2C y cuatro listas contables = **CORREGIDA EN ESTE PASE**; descargas/transiciones = **NO APLICA al crawler GET**; administración e apps no iniciadas = **NO APLICA**. No se borraron rutas legacy.
