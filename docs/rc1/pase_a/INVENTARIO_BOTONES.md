# Inventario de botones y acciones visibles

Total estático: 759 controles `a`, `button` e `input` accionables. La validación runtime complementaria cubre enlaces, métodos, CSRF y resolución.

| Template | Línea | Elemento | Tipo | Etiqueta | Destino |
|---|---|---|---|---|---|
| admin/centros_form.html | 6 | a | link | (texto interno) | /carga-centros/ |
| admin/change_list.html | 7 | a | link | (texto interno) | /buscar-conduces/ |
| admin/change_list.html | 13 | a | link | (texto interno) | /generar-conduces/ |
| admin/conduces_changelist.html | 67 | a | link | (texto interno) | /buscar-conduces/ |
| admin/conduces_changelist.html | 71 | a | link | (texto interno) | /generar-conduces/ |
| admin/menu_form.html | 6 | a | link | (texto interno) | /carga-menu/ |
| agregar_dia_no_docencia.html | 15 | a | link | (texto interno) | {% url 'calendario_escolar' %} |
| agregar_dia_no_docencia.html | 55 | button | submit | (texto interno) | formulario/JS |
| agregar_dia_no_docencia.html | 56 | a | link | (texto interno) | {% url 'calendario_escolar' %} |
| base.html | 12 | a | link | (texto interno) | #contenido-principal |
| base.html | 14 | a | link | Ir al Dashboard Premium | {% url 'inicio' %} |
| base.html | 14 | button | button | Cerrar menú | formulario/JS |
| base.html | 18 | a | link | (texto interno) | {% url 'inicio' %} |
| base.html | 19 | a | link | (texto interno) | {% url 'core:workspace_home' %} |
| base.html | 20 | a | link | (texto interno) | {% url 'workflow:bandeja' %} |
| base.html | 20 | a | link | (texto interno) | {% url 'workflow:reportes' %} |
| base.html | 21 | a | link | (texto interno) | {% url 'comercial:crm_dashboard' %} |
| base.html | 21 | a | link | (texto interno) | {% url 'comercial:prospectos_lista' %} |
| base.html | 21 | a | link | (texto interno) | {% url 'comercial:pipeline' %} |
| base.html | 21 | a | link | (texto interno) | {% url 'comercial:clientes_lista' %} |
| base.html | 21 | a | link | (texto interno) | {% url 'comercial:cotizaciones_lista' %} |
| base.html | 21 | a | link | (texto interno) | {% url 'comercial:pedidos_lista' %} |
| base.html | 21 | a | link | (texto interno) | {% url 'comercial:programacion_diaria' %} |
| base.html | 22 | a | link | (texto interno) | {% url 'buscar_conduces' %} |
| base.html | 22 | a | link | (texto interno) | {% url 'generar_conduces' %} |
| base.html | 22 | a | link | (texto interno) | {% url 'facturacion' %} |
| base.html | 23 | a | link | (texto interno) | {% url 'compras:lista' %} |
| base.html | 23 | a | link | (texto interno) | {% url 'compras:solicitudes_lista' %} |
| base.html | 23 | a | link | (texto interno) | {% url 'compras:expedientes_lista' %} |
| base.html | 23 | a | link | (texto interno) | {% url 'compras:rfq_lista' %} |
| base.html | 24 | a | link | (texto interno) | {% url 'inventario:dashboard' %} |
| base.html | 24 | a | link | (texto interno) | {% url 'inventario:productos' %} |
| base.html | 24 | a | link | (texto interno) | {% url 'inventario:movimientos' %} |
| base.html | 25 | a | link | (texto interno) | {% url 'inventario:produccion_dashboard' %} |
| base.html | 25 | a | link | (texto interno) | {% url 'inventario:ordenes_lista' %} |
| base.html | 25 | a | link | (texto interno) | {% url 'inventario:necesidades_materia_prima' %} |
| base.html | 26 | a | link | (texto interno) | {% url 'contabilidad:dashboard_enterprise' %} |
| base.html | 26 | a | link | (texto interno) | {% url 'comercial:o2c_full_dashboard' %} |
| base.html | 27 | a | link | (texto interno) | {% url 'comercial:dashboard' %} |
| base.html | 27 | a | link | (texto interno) | {% url 'workflow:reportes' %} |
| base.html | 28 | a | link | (texto interno) | {% url 'mi_empresa' %} |
| base.html | 28 | a | link | (texto interno) | {% url 'core:motor_dashboard' %} |
| base.html | 28 | a | link | (texto interno) | {% url 'core:design_system' %} |
| base.html | 28 | a | link | (texto interno) | {% url 'catalogos:centro' %} |
| base.html | 30 | button | button | Cerrar navegación | formulario/JS |
| base.html | 31 | button | button | Abrir menú | formulario/JS |
| base.html | 31 | button | button | Alternar menú compacto | formulario/JS |
| base.html | 31 | a | link | Agenda | {% url 'comercial:agenda' %} |
| base.html | 31 | button | button | Notificaciones | formulario/JS |
| base.html | 31 | a | link | Tareas pendientes | {% url 'workflow:bandeja' %} |
| base.html | 31 | button | button | (texto interno) | formulario/JS |
| base.html | 31 | a | link | (texto interno) | {% url 'mi_empresa' %} |
| base.html | 31 | a | link | (texto interno) | {% url 'logout_usuario' %} |
| buscar_conduces.html | 16 | a | link | (texto interno) | {% url 'inicio' %} |
| buscar_conduces.html | 17 | a | link | (texto interno) | {% url 'generar_conduces' %} |
| buscar_conduces.html | 70 | button | submit | (texto interno) | formulario/JS |
| buscar_conduces.html | 71 | a | link | (texto interno) | {% url 'buscar_conduces' %} |
| buscar_conduces.html | 83 | a | link | (texto interno) | {% url 'generar_relacion_diaria_pdf' %}?fecha_inicio={{ fecha_desde }}&fecha_fin={{ fecha_hasta }} |
| buscar_conduces.html | 89 | a | link | (texto interno) | {% url 'generar_relacion_general_pdf' %}?fecha_inicio={{ fecha_desde }}&fecha_fin={{ fecha_hasta }} |
| buscar_conduces.html | 103 | button | submit | (texto interno) | formulario/JS |
| buscar_conduces.html | 128 | button | submit | (texto interno) | formulario/JS |
| buscar_conduces.html | 180 | a | link | (texto interno) | {% url 'vista_conduce' conduce.id %} |
| buscar_conduces.html | 181 | a | link | (texto interno) | {% url 'editar_conduce' conduce.id %} |
| buscar_conduces.html | 182 | a | link | (texto interno) | {% url 'visualizar_pdf_conduce' conduce.id %} |
| buscar_conduces.html | 184 | a | link | (texto interno) | {% url 'eliminar_conduce' conduce.id %} |
| calendario_escolar.html | 15 | a | link | (texto interno) | {% url 'agregar_dia_no_docencia' %} |
| calendario_escolar.html | 55 | a | link | (texto interno) | {% url 'editar_dia_no_docencia' dia.id %} |
| carga_centros.html | 14 | a | link | (texto interno) | {% url 'inicio' %} |
| carga_centros.html | 36 | button | submit | (texto interno) | formulario/JS |
| carga_centros.html | 37 | a | link | (texto interno) | {% url 'carga_centros' %} |
| carga_centros.html | 38 | a | link | (texto interno) | {% url 'plantilla_centros' %} |
| carga_centros.html | 39 | a | link | (texto interno) | {% url 'mapa_centros' %} |
| carga_centros.html | 97 | button | submit | (texto interno) | formulario/JS |
| carga_centros.html | 118 | button | submit | (texto interno) | formulario/JS |
| carga_centros.html | 160 | a | link | (texto interno) | {% url 'editar_centro' centro.id %} |
| carga_centros.html | 170 | button | submit | (texto interno) | formulario/JS |
| carga_masiva.html | 74 | a | link | (texto interno) | /plantilla-centros/ |
| carga_masiva.html | 80 | button | submit | (texto interno) | formulario/JS |
| carga_masiva.html | 88 | a | link | (texto interno) | /plantilla-menu/ |
| carga_masiva.html | 94 | button | submit | (texto interno) | formulario/JS |
| carga_masiva.html | 98 | a | link | (texto interno) | /admin/ |
| carga_menu.html | 15 | a | link | (texto interno) | {% url 'inicio' %} |
| carga_menu.html | 38 | button | submit | (texto interno) | formulario/JS |
| carga_menu.html | 40 | a | link | (texto interno) | {% url 'carga_menu' %} |
| carga_menu.html | 44 | a | link | (texto interno) | {% url 'plantilla_menu' %} |
| carga_menu.html | 81 | button | submit | (texto interno) | formulario/JS |
| carga_menu.html | 106 | button | submit | (texto interno) | formulario/JS |
| carga_menu.html | 139 | a | link | (texto interno) | {% url 'editar_menu_diario' menu.id %} |
| carga_menu.html | 149 | button | submit | (texto interno) | formulario/JS |
| cargar_excel.html | 16 | button | submit | (texto interno) | formulario/JS |
| cargar_excel.html | 21 | a | link | (texto interno) | /admin/ |
| cartas_administrativas.html | 14 | a | link | (texto interno) | {% url 'inicio' %} |
| cartas_administrativas.html | 77 | button | submit | (texto interno) | formulario/JS |
| catalogos/centro.html | 3 | a | link | (texto interno) | {% url 'catalogos:lista' clave %} |
| catalogos/form.html | 3 | button | submit | (texto interno) | formulario/JS |
| catalogos/form.html | 3 | a | link | (texto interno) | {% url 'catalogos:lista' clave %} |
| catalogos/lista.html | 2 | a | link | (texto interno) | {% url 'catalogos:centro' %} |
| catalogos/lista.html | 2 | a | link | (texto interno) | {% url 'catalogos:crear' clave %} |
| catalogos/lista.html | 3 | input | submit | {{ q }} | formulario/JS |
| catalogos/lista.html | 3 | button | submit | (texto interno) | formulario/JS |
| catalogos/lista.html | 4 | a | link | (texto interno) | {% url 'catalogos:editar' clave objeto.pk %} |
| comercial/cliente_detalle.html | 5 | a | link | (texto interno) | {% url 'comercial:cliente_editar' cliente.pk %} |
| comercial/cliente_detalle.html | 5 | button | submit | (texto interno) | formulario/JS |
| comercial/cliente_detalle.html | 11 | a | link | (texto interno) | {% url 'comercial:direccion_crear' cliente.pk %} |
| comercial/cliente_detalle.html | 11 | a | link | (texto interno) | {% url 'comercial:direccion_editar' d.pk %} |
| comercial/cliente_detalle.html | 12 | a | link | (texto interno) | {% url 'comercial:contacto_crear' cliente.pk %} |
| comercial/cliente_detalle.html | 12 | a | link | (texto interno) | {% url 'comercial:contacto_editar' c.pk %} |
| comercial/cliente_detalle.html | 17 | a | link | (texto interno) | {% url 'documentos:cargar' 'comercial' 'cliente' cliente.pk %} |
| comercial/cliente_detalle.html | 18 | a | link | (texto interno) | {% url 'documentos:detalle' d.pk %} |
| comercial/cliente_detalle.html | 18 | a | link | (texto interno) | {% url 'documentos:descargar' d.pk %} |
| comercial/cliente_detalle.html | 19 | a | link | (texto interno) | {% url 'documentos:detalle' d.pk %} |
| comercial/cliente_detalle.html | 19 | a | link | (texto interno) | {% url 'documentos:descargar' d.pk %} |
| comercial/cliente_form.html | 3 | button | submit | (texto interno) | formulario/JS |
| comercial/cliente_form.html | 3 | a | link | (texto interno) | {% if cliente %}{% url 'comercial:cliente_detalle' cliente.pk %}{% else %}{% url 'comercial:clientes_lista' %}{% endif %} |
| comercial/clientes_lista.html | 11 | input | submit | {{ q }} | formulario/JS |
| comercial/clientes_lista.html | 15 | button | submit | (texto interno) | formulario/JS |
| comercial/clientes_lista.html | 19 | a | link | (texto interno) | {% url 'comercial:cliente_detalle' c.pk %} |
| comercial/clientes_lista.html | 21 | a | link | (texto interno) | {% url 'comercial:cliente_detalle' c.pk %} |
| comercial/clientes_lista.html | 22 | a | link | (texto interno) | ?page={{ pagina.previous_page_number }}&q={{ q }} |
| comercial/clientes_lista.html | 22 | a | link | (texto interno) | ?page={{ pagina.next_page_number }}&q={{ q }} |
| comercial/configuracion/base.html | 4 | a | link | (texto interno) | {% url 'comercial:configuracion_dashboard' %} |
| comercial/configuracion/base.html | 4 | a | link | (texto interno) | {% url 'comercial:secuencias' %} |
| comercial/configuracion/base.html | 4 | a | link | (texto interno) | {% url 'comercial:configuracion_reportes' %} |
| comercial/configuracion/dashboard.html | 2 | button | submit | (texto interno) | formulario/JS |
| comercial/configuracion/dashboard.html | 2 | a | link | (texto interno) | {% url 'comercial:secuencias' %} |
| comercial/configuracion/dashboard.html | 4 | a | link | (texto interno) | {% url 'comercial:catalogo_lista' item.tipo %} |
| comercial/configuracion/dashboard.html | 6 | a | link | (texto interno) | {% url 'comercial:configuracion_editar' %} |
| comercial/configuracion/dashboard.html | 6 | a | link | (texto interno) | {% url 'comercial:configuracion_exportar' 'csv' %} |
| comercial/configuracion/dashboard.html | 6 | a | link | (texto interno) | {% url 'comercial:configuracion_exportar' 'xlsx' %} |
| comercial/configuracion/dashboard.html | 6 | a | link | (texto interno) | {% url 'comercial:configuracion_exportar' 'pdf' %} |
| comercial/configuracion/dashboard.html | 6 | a | link | (texto interno) | {% url 'comercial:configuracion_exportar' 'print' %} |
| comercial/configuracion/detalle.html | 1 | a | link | (texto interno) | {% if es_politica %}{% url 'comercial:politica_editar' tipo objeto.pk %}{% else %}{% url 'comercial:catalogo_editar' tipo objeto.pk %}{% endif %} |
| comercial/configuracion/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/configuracion/detalle.html | 1 | input | submit | motivo | formulario/JS |
| comercial/configuracion/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/configuracion/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/configuracion/form.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/configuracion/impresion.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/configuracion/lista.html | 1 | a | link | (texto interno) | {% if es_politica %}{% url 'comercial:politica_crear' tipo %}{% else %}{% url 'comercial:catalogo_crear' tipo %}{% endif %} |
| comercial/configuracion/lista.html | 1 | a | link | (texto interno) | {% if es_politica %}{% url 'comercial:politica_detalle' tipo objeto.pk %}{% else %}{% url 'comercial:catalogo_detalle' tipo objeto.pk %}{% endif %} |
| comercial/configuracion/reportes.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/configuracion/secuencias.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/contacto_form.html | 2 | button | submit | (texto interno) | formulario/JS |
| comercial/contacto_form.html | 2 | a | link | (texto interno) | {% url 'comercial:cliente_detalle' cliente.pk %} |
| comercial/crm/agenda.html | 1 | a | link | (texto interno) | {% url 'comercial:agenda_vista' 'dia' %} |
| comercial/crm/agenda.html | 1 | a | link | (texto interno) | {% url 'comercial:agenda_vista' 'semana' %} |
| comercial/crm/agenda.html | 1 | a | link | (texto interno) | {% url 'comercial:agenda_vista' 'mes' %} |
| comercial/crm/agenda.html | 1 | a | link | (texto interno) | {% url 'comercial:actividad_detalle' x.pk %} |
| comercial/crm/base.html | 1 | a | link | (texto interno) | {% url 'comercial:crm_dashboard' %} |
| comercial/crm/base.html | 1 | a | link | (texto interno) | {% url 'comercial:prospectos_lista' %} |
| comercial/crm/base.html | 1 | a | link | (texto interno) | {% url 'comercial:oportunidades_lista' %} |
| comercial/crm/base.html | 1 | a | link | (texto interno) | {% url 'comercial:pipeline' %} |
| comercial/crm/base.html | 1 | a | link | (texto interno) | {% url 'comercial:actividades_lista' %} |
| comercial/crm/base.html | 1 | a | link | (texto interno) | {% url 'comercial:agenda' %} |
| comercial/crm/base.html | 1 | a | link | (texto interno) | {% url 'comercial:crm_reportes' %} |
| comercial/crm/dashboard.html | 1 | a | link | (texto interno) | {% url 'comercial:actividad_detalle' x.pk %} |
| comercial/crm/dashboard.html | 1 | a | link | (texto interno) | {% url 'comercial:actividad_detalle' x.pk %} |
| comercial/crm/dashboard.html | 1 | a | link | (texto interno) | {% url 'comercial:oportunidad_detalle' x.pk %} |
| comercial/crm/detalle.html | 1 | a | link | (texto interno) | {% if tipo == 'prospecto' %}{% url 'comercial:prospecto_editar' objeto.pk %}{% elif tipo == 'oportunidad' %}{% url 'comercial:oportunidad_editar' objeto.pk %}{% else %}{% url 'comercial:actividad_editar' objeto.pk %}{% endif %} |
| comercial/crm/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/crm/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/crm/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/crm/detalle.html | 1 | a | link | (texto interno) | {% url 'documentos:cargar' 'comercial' 'prospecto' objeto.pk %} |
| comercial/crm/detalle.html | 1 | input | submit | motivo | formulario/JS |
| comercial/crm/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/crm/detalle.html | 1 | a | link | (texto interno) | {% url 'documentos:cargar' 'comercial' 'oportunidadcomercial' objeto.pk %} |
| comercial/crm/detalle.html | 1 | input | submit | resultado | formulario/JS |
| comercial/crm/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/crm/detalle.html | 1 | a | link | (texto interno) | {% url 'documentos:cargar' 'comercial' 'actividadcomercial' objeto.pk %} |
| comercial/crm/detalle.html | 1 | a | link | (texto interno) | {% url 'comercial:actividad_detalle' a.pk %} |
| comercial/crm/form.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/crm/impresion.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/crm/lista.html | 7 | input | submit | {{ request.GET.q }} | formulario/JS |
| comercial/crm/lista.html | 7 | button | submit | (texto interno) | formulario/JS |
| comercial/crm/lista.html | 8 | button | submit | (texto interno) | {% url 'comercial:crm_accion_masiva' tipo_plural 'reasignar' %} |
| comercial/crm/lista.html | 8 | button | submit | (texto interno) | {% url 'comercial:crm_accion_masiva' tipo_plural 'prioridad' %} |
| comercial/crm/lista.html | 8 | button | submit | (texto interno) | {% url 'comercial:crm_accion_masiva' tipo_plural 'completar' %} |
| comercial/crm/lista.html | 8 | button | submit | (texto interno) | {% url 'comercial:crm_accion_masiva' tipo_plural 'seguimiento' %} |
| comercial/crm/lista.html | 8 | button | submit | (texto interno) | {% url 'comercial:crm_accion_masiva' tipo_plural 'exportar' %} |
| comercial/crm/lista.html | 9 | a | link | (texto interno) | {% if tipo == 'prospecto' %}{% url 'comercial:prospecto_detalle' x.pk %}{% elif tipo == 'oportunidad' %}{% url 'comercial:oportunidad_detalle' x.pk %}{% else %}{% url 'comercial:actividad_detalle' x.pk %}{% endif %} |
| comercial/crm/pipeline.html | 1 | a | link | (texto interno) | {% url 'comercial:oportunidad_detalle' x.pk %} |
| comercial/crm/reportes.html | 1 | a | link | (texto interno) | {% url 'comercial:crm_exportar' 'prospectos' 'csv' %} |
| comercial/crm/reportes.html | 1 | a | link | (texto interno) | {% url 'comercial:crm_exportar' 'oportunidades' 'xlsx' %} |
| comercial/crm/reportes.html | 1 | a | link | (texto interno) | {% url 'comercial:crm_exportar' 'actividades' 'pdf' %} |
| comercial/crm/reportes.html | 1 | a | link | (texto interno) | {% url 'comercial:crm_exportar' 'prospectos' 'print' %} |
| comercial/dashboard.html | 5 | a | link | (texto interno) | {% url 'comercial:cliente_crear' %} |
| comercial/dashboard.html | 12 | a | link | (texto interno) | {% url 'comercial:clientes_lista' %} |
| comercial/dashboard.html | 13 | a | link | (texto interno) | {% url 'comercial:cliente_detalle' cliente.pk %} |
| comercial/direccion_form.html | 2 | button | submit | (texto interno) | formulario/JS |
| comercial/direccion_form.html | 2 | a | link | (texto interno) | {% url 'comercial:cliente_detalle' cliente.pk %} |
| comercial/o2c/base.html | 1 | a | link | (texto interno) | {% url 'comercial:o2c_dashboard' %} |
| comercial/o2c/base.html | 1 | a | link | (texto interno) | {% url 'comercial:clientes_lista' %} |
| comercial/o2c/base.html | 1 | a | link | (texto interno) | {% url 'comercial:productos_comerciales' %} |
| comercial/o2c/base.html | 1 | a | link | (texto interno) | {% url 'comercial:listas_precio' %} |
| comercial/o2c/base.html | 1 | a | link | (texto interno) | {% url 'comercial:simulador_precio' %} |
| comercial/o2c/base.html | 1 | a | link | (texto interno) | {% url 'comercial:cotizaciones_lista' %} |
| comercial/o2c/base.html | 1 | a | link | (texto interno) | {% url 'comercial:pedidos_lista' %} |
| comercial/o2c/base.html | 1 | a | link | (texto interno) | {% url 'comercial:programacion_comercial' %} |
| comercial/o2c/base.html | 1 | a | link | (texto interno) | {% url 'comercial:o2c_reportes' %} |
| comercial/o2c/cliente360.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c/cotizacion.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c/cotizacion.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c/cotizacion.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c/cotizacion.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c/cotizacion.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c/cotizacion.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c/cotizacion.html | 1 | a | link | (texto interno) | {% url 'comercial:cotizacion_pdf' objeto.pk %} |
| comercial/o2c/dashboard.html | 1 | a | link | (texto interno) | {% url 'comercial:cotizacion_detalle' x.pk %} |
| comercial/o2c/dashboard.html | 1 | a | link | (texto interno) | {% url 'comercial:pedido_detalle' x.pk %} |
| comercial/o2c/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c/form.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c/lista.html | 4 | a | link | (texto interno) | {% if tipo == 'producto' %}{% url 'comercial:producto_detalle' x.pk %}{% elif tipo == 'lista' %}{% url 'comercial:lista_detalle' x.pk %}{% else %}{% url 'comercial:cotizacion_detalle' x.pk %}{% endif %} |
| comercial/o2c/programacion.html | 1 | a | link | (texto interno) | {% url 'comercial:programacion_comercial_vista' 'dia' %} |
| comercial/o2c/programacion.html | 1 | a | link | (texto interno) | {% url 'comercial:programacion_comercial_vista' 'semana' %} |
| comercial/o2c/programacion.html | 1 | a | link | (texto interno) | {% url 'comercial:programacion_comercial_vista' 'mes' %} |
| comercial/o2c/programacion.html | 1 | a | link | (texto interno) | {% url 'comercial:pedido_detalle' x.pedido.pk %} |
| comercial/o2c/reportes.html | 1 | a | link | (texto interno) | {% url 'comercial:o2c_exportar' 'clientes' 'csv' %} |
| comercial/o2c/reportes.html | 1 | a | link | (texto interno) | {% url 'comercial:o2c_exportar' 'productos' 'csv' %} |
| comercial/o2c/reportes.html | 1 | a | link | (texto interno) | {% url 'comercial:o2c_exportar' 'cotizaciones' 'print' %} |
| comercial/o2c/simulador.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c_full/dashboard.html | 9 | a | link | (texto interno) | {% url 'comercial:o2c_full_lista' 'reservas' %} |
| comercial/o2c_full/dashboard.html | 10 | a | link | (texto interno) | {% url 'comercial:o2c_full_lista' 'preparaciones' %} |
| comercial/o2c_full/dashboard.html | 11 | a | link | (texto interno) | {% url 'comercial:o2c_full_lista' 'picking' %} |
| comercial/o2c_full/dashboard.html | 12 | a | link | (texto interno) | {% url 'comercial:o2c_full_lista' 'packing' %} |
| comercial/o2c_full/dashboard.html | 13 | a | link | (texto interno) | {% url 'comercial:o2c_full_lista' 'despachos' %} |
| comercial/o2c_full/dashboard.html | 14 | a | link | (texto interno) | {% url 'comercial:o2c_full_lista' 'entregas' %} |
| comercial/o2c_full/dashboard.html | 15 | a | link | (texto interno) | {% url 'comercial:o2c_full_lista' 'facturas' %} |
| comercial/o2c_full/dashboard.html | 16 | a | link | (texto interno) | {% url 'comercial:o2c_full_lista' 'cxc' %} |
| comercial/o2c_full/dashboard.html | 17 | a | link | (texto interno) | {% url 'comercial:o2c_full_lista' 'cobros' %} |
| comercial/o2c_full/dashboard.html | 18 | a | link | (texto interno) | {% url 'comercial:o2c_full_lista' 'factoring' %} |
| comercial/o2c_full/lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c_full/lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c_full/lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c_full/lista.html | 1 | input | submit | 0 | formulario/JS |
| comercial/o2c_full/lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c_full/lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c_full/lista.html | 1 | input | submit | receptor | formulario/JS |
| comercial/o2c_full/lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c_full/lista.html | 1 | input | submit | ncf | formulario/JS |
| comercial/o2c_full/lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/o2c_full/lista.html | 1 | input | submit | monto | formulario/JS |
| comercial/o2c_full/lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| comercial/pedido_detalle.html | 2 | a | link | (texto interno) | {% url 'comercial:pedido_editar' pedido.pk %} |
| comercial/pedido_detalle.html | 2 | button | submit | (texto interno) | formulario/JS |
| comercial/pedido_detalle.html | 2 | button | submit | (texto interno) | formulario/JS |
| comercial/pedido_detalle.html | 2 | button | submit | (texto interno) | formulario/JS |
| comercial/pedido_detalle.html | 6 | button | submit | (texto interno) | formulario/JS |
| comercial/pedido_detalle.html | 6 | button | submit | (texto interno) | formulario/JS |
| comercial/pedido_detalle.html | 6 | button | submit | (texto interno) | formulario/JS |
| comercial/pedido_detalle.html | 7 | a | link | (texto interno) | {% url 'documentos:cargar' 'comercial' 'pedido' pedido.pk %} |
| comercial/pedido_detalle.html | 7 | a | link | (texto interno) | {% url 'documentos:detalle' d.pk %} |
| comercial/pedido_detalle.html | 7 | a | link | (texto interno) | {% url 'documentos:descargar' d.pk %} |
| comercial/pedido_form.html | 3 | button | button | (texto interno) | formulario/JS |
| comercial/pedido_form.html | 3 | button | submit | (texto interno) | formulario/JS |
| comercial/pedido_form.html | 3 | a | link | (texto interno) | {% url 'comercial:pedidos_lista' %} |
| comercial/pedidos_dashboard.html | 2 | a | link | (texto interno) | {% url 'comercial:pedido_crear' %} |
| comercial/pedidos_dashboard.html | 2 | a | link | (texto interno) | {% url 'comercial:programacion_diaria' %} |
| comercial/pedidos_dashboard.html | 2 | a | link | (texto interno) | {% url 'comercial:programacion_semanal' %} |
| comercial/pedidos_dashboard.html | 5 | a | link | (texto interno) | {% url 'comercial:pedido_detalle' p.pk %} |
| comercial/pedidos_dashboard.html | 6 | a | link | (texto interno) | {% url 'comercial:pedidos_lista' %} |
| comercial/pedidos_dashboard.html | 6 | a | link | (texto interno) | {% url 'comercial:pedido_detalle' p.pk %} |
| comercial/pedidos_lista.html | 4 | input | submit | {{ q }} | formulario/JS |
| comercial/pedidos_lista.html | 4 | button | submit | (texto interno) | formulario/JS |
| comercial/pedidos_lista.html | 6 | a | link | (texto interno) | {% url 'comercial:pedido_detalle' p.pk %} |
| comercial/pedidos_lista.html | 7 | a | link | (texto interno) | {% url 'comercial:pedido_detalle' p.pk %} |
| comercial/programacion.html | 2 | button | submit | (texto interno) | formulario/JS |
| comercial/programacion.html | 4 | a | link | (texto interno) | {% url 'comercial:pedido_detalle' p.pk %} |
| components/alert_card.html | 1 | a | link | (texto interno) | {{ href }} |
| components/breadcrumbs.html | 1 | a | link | (texto interno) | {% url 'inicio' %} |
| components/breadcrumbs.html | 1 | a | link | (texto interno) | {{ item.url }} |
| components/drawer.html | 1 | button | button | Cerrar | formulario/JS |
| components/empty_state.html | 1 | a | link | (texto interno) | {{ action_url }} |
| components/enterprise_list_command_bar.html | 4 | button | button | (texto interno) | formulario/JS |
| components/enterprise_list_command_bar.html | 5 | button | button | (texto interno) | formulario/JS |
| components/enterprise_list_command_bar.html | 7 | a | link | (texto interno) | {{ export_url }} |
| components/enterprise_list_command_bar.html | 8 | button | button | (texto interno) | formulario/JS |
| components/enterprise_list_command_bar.html | 10 | button | button | (texto interno) | formulario/JS |
| components/enterprise_list_command_bar.html | 11 | button | button | (texto interno) | formulario/JS |
| components/enterprise_list_header.html | 3 | a | link | (texto interno) | {% url 'inicio' %} |
| components/enterprise_list_header.html | 8 | a | link | (texto interno) | {{ primary_url }} |
| components/export_menu.html | 1 | button | button | (texto interno) | formulario/JS |
| components/filter_bar.html | 1 | button | submit | (texto interno) | formulario/JS |
| components/filter_bar.html | 1 | a | link | (texto interno) | {{ clear_url }} |
| components/kpi_card.html | 1 | a | link | (texto interno) | {{ href }} |
| components/modal.html | 1 | button | button | Cerrar | formulario/JS |
| components/module_card.html | 1 | a | link | (texto interno) | {{ href }} |
| components/pagination.html | 1 | a | link | Primera página | ?page=1{{ query_suffix }} |
| components/pagination.html | 1 | a | link | (texto interno) | ?page={{ page.previous_page_number }}{{ query_suffix }} |
| components/pagination.html | 1 | a | link | (texto interno) | ?page={{ page.next_page_number }}{{ query_suffix }} |
| components/pagination.html | 1 | a | link | Última página | ?page={{ page.paginator.num_pages }}{{ query_suffix }} |
| components/sticky_form_actions.html | 1 | a | link | (texto interno) | {{ cancel_url }} |
| components/sticky_form_actions.html | 1 | button | submit | (texto interno) | formulario/JS |
| components/tabs.html | 1 | a | link | (texto interno) | {{ tab.url }} |
| compras/dashboard.html | 16 | a | link | (texto interno) | {% url 'compras:lista' %} |
| compras/dashboard.html | 16 | a | link | (texto interno) | {% url 'compras:crear' %} |
| compras/detalle.html | 5 | a | link | (texto interno) | #{{ tab\|slugify }} |
| compras/detalle.html | 6 | a | link | (texto interno) | {% url 'compras:editar' proveedor.pk %} |
| compras/detalle.html | 7 | button | submit | (texto interno) | {% url 'compras:estado' proveedor.pk accion %} |
| compras/detalle.html | 8 | button | submit | (texto interno) | formulario/JS |
| compras/detalle.html | 9 | button | submit | (texto interno) | formulario/JS |
| compras/detalle.html | 10 | button | submit | (texto interno) | formulario/JS |
| compras/detalle.html | 12 | a | link | (texto interno) | {% url 'documentos:objeto' 'compras' 'proveedor' proveedor.pk %} |
| compras/detalle.html | 13 | button | button | (texto interno) | formulario/JS |
| compras/detalle.html | 13 | input | submit | motivo | formulario/JS |
| compras/detalle.html | 13 | button | submit | (texto interno) | {% url 'compras:revisar_cuenta' x.pk 'verificar' %} |
| compras/detalle.html | 13 | button | submit | (texto interno) | {% url 'compras:revisar_cuenta' x.pk 'rechazar' %} |
| compras/detalle.html | 13 | button | submit | (texto interno) | formulario/JS |
| compras/detalle.html | 16 | button | submit | (texto interno) | formulario/JS |
| compras/expedientes/detalle.html | 1 | a | link | (texto interno) | {% url 'compras:expediente_editar' expediente.pk %} |
| compras/expedientes/detalle.html | 1 | a | link | (texto interno) | {% url 'compras:rfq_detalle' r.pk %} |
| compras/expedientes/detalle.html | 1 | a | link | (texto interno) | {% url 'compras:rfq_crear' expediente.pk %} |
| compras/expedientes/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/expedientes/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/expedientes/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/expedientes/detalle.html | 1 | input | submit | motivo | formulario/JS |
| compras/expedientes/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/expedientes/detalle.html | 1 | input | submit | motivo | formulario/JS |
| compras/expedientes/detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/expedientes/form.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/expedientes/lista.html | 1 | a | link | (texto interno) | {% url 'compras:expediente_detalle' x.pk %} |
| compras/form.html | 6 | button | submit | (texto interno) | formulario/JS |
| compras/form.html | 6 | a | link | (texto interno) | {% if objeto %}{% url 'compras:detalle' objeto.pk %}{% else %}{% url 'compras:lista' %}{% endif %} |
| compras/lista.html | 6 | input | submit | {{ filtros.q }} | formulario/JS |
| compras/lista.html | 9 | button | submit | (texto interno) | formulario/JS |
| compras/lista.html | 10 | a | link | (texto interno) | {% url 'compras:crear' %} |
| compras/lista.html | 10 | a | link | (texto interno) | {% url 'compras:exportar' %}?{{ request.GET.urlencode }} |
| compras/lista.html | 12 | a | link | (texto interno) | {% url 'compras:detalle' p.pk %} |
| compras/p2p/finance_detail.html | 4 | a | link | (texto interno) | {% url 'compras:p2p_finance_list' recurso %} |
| compras/p2p/finance_detail.html | 5 | a | link | (texto interno) | {% url 'compras:p2p_finance_pdf' recurso obj.pk %} |
| compras/p2p/finance_detail.html | 5 | a | link | (texto interno) | {% url 'compras:p2p_finance_certificado' obj.pk %} |
| compras/p2p/finance_detail.html | 7 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 8 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 8 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 8 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 9 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 10 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 10 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 11 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 11 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 13 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 13 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 13 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 13 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 13 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 13 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 13 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 13 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 14 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 14 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 14 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 14 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 14 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 14 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 14 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 14 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 14 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 15 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 15 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 15 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 15 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 15 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 15 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 16 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 16 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_detail.html | 16 | input | submit | motivo | formulario/JS |
| compras/p2p/finance_detail.html | 16 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_list.html | 1 | input | submit | {{ estado }} | formulario/JS |
| compras/p2p/finance_list.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/finance_list.html | 1 | a | link | (texto interno) | {% url 'compras:p2p_finance_detail' recurso obj.pk %} |
| compras/p2p/recurso_detalle.html | 1 | a | link | (texto interno) | {% url 'compras:p2p_recurso_lista' recurso %} |
| compras/p2p/recurso_lista.html | 1 | input | submit | {{ estado }} | formulario/JS |
| compras/p2p/recurso_lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/recurso_lista.html | 1 | a | link | (texto interno) | {% url 'compras:p2p_recurso_detalle' recurso item.pk %} |
| compras/p2p/settlement_form.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/settlements.html | 1 | a | link | (texto interno) | {% url 'compras:p2p_dashboard' %} |
| compras/p2p/wizard.html | 1 | a | link | (texto interno) | {% url 'compras:p2p_dashboard' %} |
| compras/p2p/wizard.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/p2p/wizard_enterprise.html | 2 | a | link | (texto interno) | {% url 'compras:p2p_dashboard' %} |
| compras/p2p/wizard_enterprise.html | 2 | button | submit | atras | formulario/JS |
| compras/p2p/wizard_enterprise.html | 2 | button | submit | avanzar | formulario/JS |
| compras/p2p/wizard_enterprise.html | 2 | button | submit | cancelar | formulario/JS |
| compras/p2p_dashboard.html | 1 | a | link | (texto interno) | {% url 'compras:p2p_recurso_lista' slug %} |
| compras/p2p_dashboard.html | 1 | a | link | (texto interno) | {% url 'compras:p2p_recurso_lista' slug %}{% if estado %}?estado={{ estado }}{% endif %} |
| compras/p2p_dashboard.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 5 | a | link | (texto interno) | {% url 'compras:rfq_editar' rfq.pk %} |
| compras/rfq/detalle.html | 9 | input | submit | {{ l.descripcion }} | formulario/JS |
| compras/rfq/detalle.html | 9 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 11 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 13 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 14 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 15 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 15 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 15 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 15 | input | submit | motivo | formulario/JS |
| compras/rfq/detalle.html | 15 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 15 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 15 | input | submit | motivo | formulario/JS |
| compras/rfq/detalle.html | 15 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 15 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 17 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 17 | input | submit | motivo | formulario/JS |
| compras/rfq/detalle.html | 17 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 17 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 17 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 17 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 17 | input | submit | motivo | formulario/JS |
| compras/rfq/detalle.html | 17 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 17 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/detalle.html | 18 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/form.html | 1 | button | submit | (texto interno) | formulario/JS |
| compras/rfq/lista.html | 1 | a | link | (texto interno) | {% url 'compras:rfq_detalle' x.pk %} |
| compras/solicitudes/dashboard.html | 4 | a | link | (texto interno) | {% url 'compras:solicitudes_lista' %} |
| compras/solicitudes/dashboard.html | 4 | a | link | (texto interno) | {% url 'compras:solicitud_crear' %} |
| compras/solicitudes/detalle.html | 6 | button | submit | (texto interno) | formulario/JS |
| compras/solicitudes/detalle.html | 6 | button | submit | (texto interno) | formulario/JS |
| compras/solicitudes/detalle.html | 7 | a | link | (texto interno) | {% url 'documentos:detalle' d.pk %} |
| compras/solicitudes/detalle.html | 7 | a | link | (texto interno) | {% url 'documentos:cargar' 'compras' 'solicitudcompra' solicitud.pk %} |
| compras/solicitudes/detalle.html | 9 | a | link | (texto interno) | {% url 'compras:solicitud_editar' solicitud.pk %} |
| compras/solicitudes/detalle.html | 9 | button | submit | (texto interno) | formulario/JS |
| compras/solicitudes/detalle.html | 9 | button | submit | (texto interno) | formulario/JS |
| compras/solicitudes/detalle.html | 9 | button | submit | (texto interno) | formulario/JS |
| compras/solicitudes/detalle.html | 9 | button | submit | (texto interno) | formulario/JS |
| compras/solicitudes/form.html | 3 | button | submit | (texto interno) | formulario/JS |
| compras/solicitudes/form.html | 3 | a | link | (texto interno) | {% if solicitud %}{% url 'compras:solicitud_detalle' solicitud.pk %}{% else %}{% url 'compras:solicitudes_lista' %}{% endif %} |
| compras/solicitudes/lista.html | 4 | button | submit | (texto interno) | formulario/JS |
| compras/solicitudes/lista.html | 5 | a | link | (texto interno) | {% url 'compras:solicitud_crear' %} |
| compras/solicitudes/lista.html | 5 | a | link | (texto interno) | {% url 'compras:solicitudes_exportar' %}?{{ request.GET.urlencode }} |
| compras/solicitudes/lista.html | 6 | a | link | (texto interno) | {% url 'compras:solicitud_detalle' s.pk %} |
| contabilidad/balance_general.html | 12 | a | link | (texto interno) | {% url 'contabilidad:reportes_financieros' %} |
| contabilidad/crear_factura_606.html | 15 | a | link | (texto interno) | {% url 'contabilidad:facturas_606' %} |
| contabilidad/crear_factura_606.html | 30 | button | submit | (texto interno) | formulario/JS |
| contabilidad/crear_factura_606.html | 34 | a | link | (texto interno) | {% url 'contabilidad:facturas_606' %} |
| contabilidad/crear_proveedor.html | 15 | a | link | (texto interno) | {% url 'contabilidad:proveedores' %} |
| contabilidad/crear_proveedor.html | 39 | button | button | (texto interno) | formulario/JS |
| contabilidad/crear_proveedor.html | 105 | button | submit | (texto interno) | formulario/JS |
| contabilidad/crear_proveedor.html | 109 | a | link | (texto interno) | {% url 'contabilidad:proveedores' %} |
| contabilidad/cuentas_por_cobrar.html | 2 | a | link | (texto interno) | {% url 'contabilidad:crear_cuenta_por_cobrar' %} |
| contabilidad/cuentas_por_pagar.html | 2 | a | link | (texto interno) | {% url 'contabilidad:crear_cuenta_por_pagar' %} |
| contabilidad/dashboard.html | 93 | a | link | (texto interno) | {% url 'contabilidad:reportes_financieros' %} |
| contabilidad/dashboard.html | 94 | a | link | (texto interno) | {% url 'contabilidad:gastos' %} |
| contabilidad/dashboard_enterprise.html | 1 | a | link | (texto interno) | {% url 'contabilidad:reportes_financieros' %} |
| contabilidad/dashboard_enterprise.html | 1 | a | link | (texto interno) | {% url 'contabilidad:cuentas_por_pagar' %} |
| contabilidad/dashboard_enterprise.html | 1 | a | link | (texto interno) | {% url 'contabilidad:facturas_606' %} |
| contabilidad/estado_resultados.html | 12 | a | link | (texto interno) | {% url 'contabilidad:reportes_financieros' %} |
| contabilidad/factoring.html | 2 | a | link | (texto interno) | {% url 'contabilidad:crear_factoring' %} |
| contabilidad/facturas_606.html | 7 | a | link | (texto interno) | {% url 'contabilidad:crear_factura_606' %} |
| contabilidad/flujo_efectivo.html | 12 | a | link | (texto interno) | {% url 'contabilidad:reportes_financieros' %} |
| contabilidad/gastos.html | 15 | a | link | (texto interno) | {% url 'contabilidad:crear_factura_606' %} |
| contabilidad/gastos.html | 19 | a | link | (texto interno) | {% url 'contabilidad:exportar_606_excel' %} |
| contabilidad/gastos.html | 23 | a | link | (texto interno) | {% url 'contabilidad:dashboard' %} |
| contabilidad/presupuesto.html | 2 | a | link | (texto interno) | {% url 'contabilidad:crear_presupuesto' %} |
| contabilidad/proveedores.html | 7 | a | link | (texto interno) | {% url 'contabilidad:crear_proveedor' %} |
| contabilidad/reporte_cxc.html | 15 | a | link | (texto interno) | {% url 'contabilidad:reportes_financieros' %} |
| contabilidad/reporte_cxp.html | 15 | a | link | (texto interno) | {% url 'contabilidad:reportes_financieros' %} |
| contabilidad/reportes_financieros.html | 15 | a | link | (texto interno) | {% url 'contabilidad:dashboard' %} |
| contabilidad/reportes_financieros.html | 20 | a | link | (texto interno) | {% url 'contabilidad:estado_resultados' %} |
| contabilidad/reportes_financieros.html | 26 | a | link | (texto interno) | {% url 'contabilidad:balance_general' %} |
| contabilidad/reportes_financieros.html | 32 | a | link | (texto interno) | {% url 'contabilidad:flujo_efectivo' %} |
| contabilidad/reportes_financieros.html | 38 | a | link | (texto interno) | {% url 'contabilidad:reporte_cuentas_por_cobrar' %} |
| contabilidad/reportes_financieros.html | 44 | a | link | (texto interno) | {% url 'contabilidad:reporte_cuentas_por_pagar' %} |
| contabilidad/reportes_financieros.html | 50 | a | link | (texto interno) | {% url 'contabilidad:gastos' %} |
| core/design_system.html | 5 | a | link | (texto interno) | {% url 'core:motor_dashboard' %} |
| core/design_system.html | 7 | a | link | (texto interno) | #tokens |
| core/design_system.html | 7 | a | link | (texto interno) | #components |
| core/design_system.html | 7 | a | link | (texto interno) | #patterns |
| core/design_system.html | 7 | a | link | (texto interno) | #responsive |
| core/design_system.html | 16 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 16 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 16 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 16 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 16 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 16 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 16 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 16 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 20 | input | submit | (texto interno) | formulario/JS |
| core/design_system.html | 20 | input | submit | 0.00 | formulario/JS |
| core/design_system.html | 20 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 20 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 23 | a | link | (texto interno) | #components |
| core/design_system.html | 23 | a | link | (texto interno) | #components |
| core/design_system.html | 24 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 24 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 24 | button | button | (texto interno) | formulario/JS |
| core/design_system.html | 24 | button | button | (texto interno) | formulario/JS |
| core/design_system.html | 24 | button | button | (texto interno) | formulario/JS |
| core/design_system.html | 26 | button | submit | (texto interno) | formulario/JS |
| core/design_system.html | 26 | button | submit | (texto interno) | formulario/JS |
| core/detalle_tecnico.html | 3 | a | link | (texto interno) | {% url 'core:motor_dashboard' %} |
| core/detalle_tecnico.html | 3 | button | button | (texto interno) | formulario/JS |
| core/detalle_tecnico.html | 8 | button | submit | (texto interno) | formulario/JS |
| core/detalle_tecnico.html | 8 | button | submit | (texto interno) | formulario/JS |
| core/detalle_tecnico.html | 8 | a | link | (texto interno) | {% url 'core:secuencia_editar' objeto.pk %} |
| core/experience/activity.html | 2 | a | link | (texto interno) | {% url 'core:workspace_home' %} |
| core/experience/activity.html | 3 | input | submit | {{ request.GET.q }} | formulario/JS |
| core/experience/activity.html | 3 | button | submit | (texto interno) | formulario/JS |
| core/experience/activity.html | 4 | a | link | (texto interno) | {{ item.url }} |
| core/experience/alerts.html | 1 | a | link | (texto interno) | {{ item.url_origen }} |
| core/experience/enterprise_360.html | 1 | a | link | (texto interno) | {% url 'core:workspace_home' %} |
| core/experience/enterprise_360.html | 1 | a | link | (texto interno) | #tab-{{ forloop.counter }} |
| core/experience/home.html | 2 | a | link | (texto interno) | {% url 'inicio' %} |
| core/experience/home.html | 3 | a | link | (texto interno) | {% url 'core:busqueda_global' %} |
| core/experience/home.html | 5 | a | link | (texto interno) | {% url 'core:workspace' key %} |
| core/experience/home.html | 6 | a | link | (texto interno) | {{ item.url }} |
| core/experience/home.html | 6 | a | link | (texto interno) | {{ item.url }} |
| core/experience/home.html | 7 | a | link | (texto interno) | {% url route %} |
| core/experience/search.html | 1 | input | submit | {{ query }} | formulario/JS |
| core/experience/search.html | 1 | button | submit | (texto interno) | formulario/JS |
| core/experience/search.html | 1 | a | link | (texto interno) | {{ url }} |
| core/experience/workspace.html | 2 | a | link | (texto interno) | {% url 'core:workspace_home' %} |
| core/experience/workspace.html | 3 | button | submit | Agregar o quitar favorito | formulario/JS |
| core/experience/workspace.html | 3 | a | link | (texto interno) | {% url route %} |
| core/experience/workspace.html | 4 | a | link | (texto interno) | {% url route %} |
| core/experience/workspace.html | 5 | a | link | (texto interno) | {{ item.url }} |
| core/experience/workspace.html | 5 | a | link | (texto interno) | {% url route %} |
| core/form_tecnico.html | 2 | button | submit | (texto interno) | formulario/JS |
| core/lista_tecnica.html | 3 | a | link | (texto interno) | {% url 'core:motor_dashboard' %} |
| core/lista_tecnica.html | 3 | a | link | (texto interno) | {% url crear_url %} |
| core/lista_tecnica.html | 4 | button | submit | (texto interno) | formulario/JS |
| core/lista_tecnica.html | 4 | a | link | (texto interno) | {{ request.path }} |
| core/lista_tecnica.html | 5 | button | submit | (texto interno) | formulario/JS |
| core/lista_tecnica.html | 5 | button | submit | (texto interno) | formulario/JS |
| core/lista_tecnica.html | 6 | a | link | (texto interno) | {% url detalle_url objeto.pk %} |
| core/motor_dashboard.html | 3 | a | link | (texto interno) | {% url 'inicio' %} |
| core/motor_dashboard.html | 3 | a | link | (texto interno) | {% url 'core:design_system' %} |
| core/motor_dashboard.html | 5 | a | link | (texto interno) | {% url 'core:idempotencias' %} |
| core/motor_dashboard.html | 5 | a | link | (texto interno) | {% url 'core:eventos' %} |
| core/motor_dashboard.html | 5 | a | link | (texto interno) | {% url 'core:eventos_fallidos' %} |
| core/motor_dashboard.html | 5 | a | link | (texto interno) | {% url 'core:secuencias' %} |
| core/motor_dashboard.html | 5 | a | link | (texto interno) | {% url 'core:conciliaciones' %} |
| core/motor_dashboard.html | 6 | a | link | (texto interno) | {% url 'core:evento_detalle' item.pk %} |
| core/motor_dashboard.html | 6 | a | link | (texto interno) | {% url 'core:conciliacion_detalle' item.pk %} |
| core/reconstruccion_preview.html | 2 | button | submit | (texto interno) | formulario/JS |
| design_system/catalog.html | 1 | a | link | (texto interno) | #content |
| documentos/documento_detalle.html | 3 | a | link | (texto interno) | {% url 'documentos:descargar' documento.pk %} |
| documentos/documento_detalle.html | 6 | button | submit | (texto interno) | formulario/JS |
| documentos/documento_detalle.html | 7 | button | submit | (texto interno) | formulario/JS |
| documentos/documento_detalle.html | 8 | a | link | (texto interno) | {% url 'comercial:cliente_detalle' documento.object_id %} |
| documentos/documento_detalle.html | 8 | a | link | (texto interno) | {% url 'comercial:pedido_detalle' documento.object_id %} |
| documentos/documento_detalle.html | 8 | a | link | (texto interno) | {% url 'inventario:receta_detalle' documento.object_id %} |
| documentos/documento_detalle.html | 8 | a | link | (texto interno) | {% url 'inventario:plan_detalle' documento.object_id %} |
| documentos/documento_detalle.html | 8 | a | link | (texto interno) | {% url 'inventario:orden_detalle' documento.object_id %} |
| documentos/documento_form.html | 4 | button | submit | (texto interno) | formulario/JS |
| documentos/documento_form.html | 4 | a | link | (texto interno) | {% url 'comercial:cliente_detalle' objeto.pk %} |
| documentos/documentos_lista.html | 4 | input | submit | {{ q }} | formulario/JS |
| documentos/documentos_lista.html | 4 | button | submit | (texto interno) | formulario/JS |
| documentos/documentos_lista.html | 5 | a | link | (texto interno) | {% url 'documentos:detalle' d.pk %} |
| documentos/documentos_lista.html | 6 | a | link | (texto interno) | {% url 'documentos:detalle' d.pk %} |
| editar_centro.html | 55 | button | submit | (texto interno) | formulario/JS |
| editar_centro.html | 56 | a | link | (texto interno) | {% url 'carga_centros' %} |
| editar_conduce.html | 4 | a | link | (texto interno) | {% url 'inicio' %} |
| editar_conduce.html | 4 | a | link | (texto interno) | {% url 'buscar_conduces' %} |
| editar_conduce.html | 16 | a | link | (texto interno) | {% url 'buscar_conduces' %} |
| editar_conduce.html | 16 | button | submit | (texto interno) | formulario/JS |
| editar_dia_no_docencia.html | 15 | a | link | (texto interno) | {% url 'calendario_escolar' %} |
| editar_dia_no_docencia.html | 62 | button | submit | (texto interno) | formulario/JS |
| editar_dia_no_docencia.html | 63 | a | link | (texto interno) | {% url 'calendario_escolar' %} |
| editar_factura.html | 4 | a | link | (texto interno) | {% url 'inicio' %} |
| editar_factura.html | 4 | a | link | (texto interno) | {% url 'facturacion' %} |
| editar_factura.html | 24 | a | link | (texto interno) | {% url 'facturacion' %} |
| editar_factura.html | 24 | a | link | (texto interno) | {% url 'pdf_factura' factura.id %} |
| editar_factura.html | 24 | button | submit | (texto interno) | formulario/JS |
| editar_menu.html | 4 | a | link | (texto interno) | {% url 'inicio' %} |
| editar_menu.html | 12 | a | link | (texto interno) | {% url 'carga_menu' %} |
| editar_menu.html | 12 | button | submit | (texto interno) | formulario/JS |
| editar_producto_facturacion.html | 4 | a | link | (texto interno) | {% url 'inicio' %} |
| editar_producto_facturacion.html | 4 | a | link | (texto interno) | {% url 'facturacion' %} |
| editar_producto_facturacion.html | 15 | a | link | (texto interno) | {% url 'facturacion' %} |
| editar_producto_facturacion.html | 15 | button | submit | (texto interno) | formulario/JS |
| facturacion.html | 14 | a | link | (texto interno) | {% url 'inicio' %} |
| facturacion.html | 100 | button | submit | (texto interno) | formulario/JS |
| facturacion.html | 149 | button | submit | (texto interno) | formulario/JS |
| facturacion.html | 176 | a | link | (texto interno) | {% url 'editar_producto_facturacion' producto.id %} |
| facturacion.html | 180 | button | submit | (texto interno) | formulario/JS |
| facturacion.html | 231 | button | submit | (texto interno) | formulario/JS |
| facturacion.html | 282 | button | submit | (texto interno) | formulario/JS |
| facturacion.html | 358 | button | submit | (texto interno) | formulario/JS |
| facturacion.html | 364 | button | submit | (texto interno) | formulario/JS |
| facturacion.html | 441 | a | link | (texto interno) | {% url 'pdf_factura' factura.id %} |
| facturacion.html | 442 | a | link | (texto interno) | {% url 'editar_factura' factura.id %} |
| facturacion.html | 444 | a | link | (texto interno) | {% url 'generar_relacion_general_pdf' %}?fecha_inicio={{ factura.fecha_inicio\|date:'Y-m-d' }}&fecha_fin={{ factura.fecha_fin\|date:'Y-m-d' }} |
| facturacion.html | 454 | button | submit | (texto interno) | formulario/JS |
| facturacion.html | 460 | button | submit | (texto interno) | formulario/JS |
| generar_conduces.html | 13 | a | link | (texto interno) | {% url 'inicio' %} |
| generar_conduces.html | 59 | button | submit | (texto interno) | formulario/JS |
| generar_conduces.html | 60 | a | link | (texto interno) | {% url 'buscar_conduces' %} |
| inicio.html | 6 | button | button | Alternar menú | formulario/JS |
| inicio.html | 6 | button | button | Actualizar | formulario/JS |
| inicio.html | 6 | a | link | Notificaciones | {% url 'core:alertas' %} |
| inicio.html | 6 | button | button | Pantalla completa | formulario/JS |
| inicio.html | 8 | a | link | (texto interno) | {% url 'buscar_conduces' %} |
| inicio.html | 8 | a | link | (texto interno) | {% url 'buscar_conduces' %} |
| inicio.html | 8 | a | link | (texto interno) | {% url 'lista_centros' %} |
| inicio.html | 8 | a | link | (texto interno) | {% url 'comercial:dashboard' %} |
| inicio.html | 12 | a | link | (texto interno) | {% url 'core:alertas' %} |
| inicio.html | 12 | a | link | (texto interno) | {% url 'core:alertas' %} |
| inicio.html | 14 | a | link | (texto interno) | {% url 'carga_menu' %} |
| inicio.html | 14 | a | link | (texto interno) | {% url 'crear_menu_diario' %} |
| inicio.html | 16 | a | link | (texto interno) | {% url 'core:actividad' %} |
| inicio.html | 18 | a | link | (texto interno) | {% url 'generar_conduces' %} |
| inicio.html | 18 | a | link | (texto interno) | {% url 'crear_menu_diario' %} |
| inicio.html | 18 | a | link | (texto interno) | {% url 'lista_centros' %} |
| inicio.html | 18 | a | link | (texto interno) | {% url 'facturacion' %} |
| inicio.html | 18 | a | link | (texto interno) | {% url 'mapa_centros' %} |
| inicio.html | 18 | a | link | (texto interno) | {% url 'comercial:o2c_reportes' %} |
| inicio.html | 20 | a | link | (texto interno) | {% url 'contabilidad:dashboard_enterprise' %} |
| inicio.html | 20 | a | link | (texto interno) | {% url 'comercial:o2c_full_dashboard' %} |
| inicio.html | 20 | a | link | (texto interno) | {% url 'inventario:produccion_dashboard' %} |
| inicio.html | 20 | a | link | (texto interno) | {% url 'inventario:dashboard' %} |
| inicio_backup.html | 20 | a | link | (texto interno) | {% url 'inicio' %} |
| inicio_backup.html | 21 | a | link | (texto interno) | {% url 'buscar_conduces' %} |
| inicio_backup.html | 22 | a | link | (texto interno) | {% url 'carga_centros' %} |
| inicio_backup.html | 23 | a | link | (texto interno) | {% url 'carga_menu' %} |
| inicio_backup.html | 24 | a | link | (texto interno) | {% url 'generar_conduces' %} |
| inicio_backup.html | 66 | a | link | (texto interno) | {% url 'generar_conduces' %} |
| inicio_backup.html | 72 | a | link | (texto interno) | {% url 'buscar_conduces' %} |
| inicio_backup.html | 78 | a | link | (texto interno) | {% url 'carga_centros' %} |
| inicio_backup.html | 84 | a | link | (texto interno) | {% url 'carga_menu' %} |
| inventario/crear_prestamo.html | 15 | a | link | (texto interno) | {% url 'inventario:prestamos' %} |
| inventario/crear_prestamo.html | 80 | button | submit | (texto interno) | formulario/JS |
| inventario/dashboard.html | 3 | a | link | (texto interno) | {% url 'inicio' %} |
| inventario/dashboard.html | 3 | a | link | (texto interno) | {% url 'inventario:registrar_movimiento_manual' %} |
| inventario/dashboard.html | 3 | a | link | (texto interno) | {% url 'inventario:pdf_inventario' %} |
| inventario/dashboard.html | 6 | a | link | (texto interno) | {% url 'inventario:kardex_producto' item.producto.id %} |
| inventario/dashboard.html | 6 | a | link | (texto interno) | {% url 'inventario:editar_producto_inventario' item.producto.id %} |
| inventario/detalle_orden_compra.html | 17 | a | link | (texto interno) | {% url 'inventario:pdf_orden_compra' orden.id %} |
| inventario/detalle_orden_compra.html | 21 | a | link | (texto interno) | {% url 'inventario:descargar_pdf_orden_compra' orden.id %} |
| inventario/detalle_orden_compra.html | 25 | a | link | (texto interno) | {% url 'inventario:ordenes_compra' %} |
| inventario/detalle_orden_compra.html | 39 | a | link | (texto interno) | {% url 'inventario:recibir_orden_compra' orden.id %} |
| inventario/detalle_orden_compra.html | 131 | button | submit | (texto interno) | formulario/JS |
| inventario/detalle_orden_compra.html | 201 | button | submit | (texto interno) | formulario/JS |
| inventario/detalle_orden_compra.html | 205 | a | link | (texto interno) | {% url 'inventario:eliminar_detalle_orden' detalle.id %} |
| inventario/detalle_produccion.html | 17 | a | link | (texto interno) | {% url 'inventario:ejecutar_produccion' produccion.id %} |
| inventario/detalle_produccion.html | 24 | a | link | (texto interno) | {% url 'inventario:produccion' %} |
| inventario/detalle_receta.html | 16 | a | link | (texto interno) | {% url 'inventario:recetas' %} |
| inventario/detalle_receta.html | 104 | button | submit | (texto interno) | formulario/JS |
| inventario/detalle_receta.html | 143 | a | link | (texto interno) | {% url 'inventario:eliminar_ingrediente_receta' detalle.id %} |
| inventario/editar_producto.html | 15 | a | link | (texto interno) | {% url 'inventario:productos' %} |
| inventario/editar_producto.html | 95 | button | submit | (texto interno) | formulario/JS |
| inventario/editar_producto.html | 96 | a | link | (texto interno) | {% url 'inventario:productos' %} |
| inventario/generar_orden_compra.html | 15 | a | link | (texto interno) | {% url 'inventario:ordenes_compra' %} |
| inventario/generar_orden_compra.html | 76 | button | submit | (texto interno) | formulario/JS |
| inventario/generar_orden_compra.html | 80 | a | link | (texto interno) | {% url 'inventario:ordenes_compra' %} |
| inventario/kardex_producto.html | 16 | a | link | (texto interno) | {% url 'inventario:productos' %} |
| inventario/orden_compra_legada_bloqueada.html | 4 | a | link | (texto interno) | {% url 'inventario:ordenes_compra' %} |
| inventario/orden_detalle.html | 1 | a | link | (texto interno) | {% url 'inventario:orden_editar' orden.pk %} |
| inventario/orden_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/orden_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/orden_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/orden_detalle.html | 1 | a | link | (texto interno) | {% url 'documentos:cargar' 'inventario' 'ordenproduccion' orden.pk %} |
| inventario/orden_detalle.html | 1 | a | link | (texto interno) | {% url 'documentos:detalle' d.pk %} |
| inventario/ordenes_compra.html | 16 | a | link | (texto interno) | {% url 'inventario:dashboard' %} |
| inventario/ordenes_compra.html | 60 | a | link | (texto interno) | {% url 'inventario:detalle_orden_compra' orden.id %} |
| inventario/ordenes_lista.html | 1 | input | submit | {{ q }} | formulario/JS |
| inventario/ordenes_lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/ordenes_lista.html | 1 | a | link | (texto interno) | {% url 'inventario:orden_detalle' o.pk %} |
| inventario/plan_detalle.html | 1 | a | link | (texto interno) | {% url 'inventario:plan_editar' plan.pk %} |
| inventario/plan_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/plan_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/plan_detalle.html | 1 | a | link | (texto interno) | {% url 'inventario:orden_detalle' o.pk %} |
| inventario/plan_detalle.html | 1 | a | link | (texto interno) | {% url 'documentos:cargar' 'inventario' 'planproduccion' plan.pk %} |
| inventario/planes_lista.html | 1 | input | submit | {{ q }} | formulario/JS |
| inventario/planes_lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/planes_lista.html | 1 | a | link | (texto interno) | {% url 'inventario:plan_generar_desde_pedidos' %} |
| inventario/planes_lista.html | 1 | a | link | (texto interno) | {% url 'inventario:plan_detalle' p.pk %} |
| inventario/prestamos.html | 16 | a | link | (texto interno) | {% url 'inventario:crear_prestamo' %} |
| inventario/prestamos.html | 17 | a | link | (texto interno) | {% url 'inventario:dashboard' %} |
| inventario/prestamos.html | 67 | button | submit | (texto interno) | formulario/JS |
| inventario/produccion.html | 15 | a | link | (texto interno) | {% url 'inventario:dashboard' %} |
| inventario/produccion.html | 51 | button | submit | (texto interno) | formulario/JS |
| inventario/produccion.html | 96 | a | link | (texto interno) | {% url 'inventario:detalle_produccion' produccion.id %} |
| inventario/produccion_dashboard.html | 1 | a | link | (texto interno) | {% url 'inventario:receta_crear' %} |
| inventario/produccion_dashboard.html | 1 | a | link | (texto interno) | {% url 'inventario:plan_generar_desde_pedidos' %} |
| inventario/produccion_dashboard.html | 1 | a | link | (texto interno) | {% url 'inventario:plan_crear' %} |
| inventario/produccion_dashboard.html | 1 | a | link | (texto interno) | {% url 'inventario:plan_detalle' p.pk %} |
| inventario/produccion_form.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/produccion_programacion.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/produccion_programacion.html | 1 | a | link | (texto interno) | {% url 'inventario:orden_detalle' o.pk %} |
| inventario/productos.html | 17 | a | link | (texto interno) | {% url 'inventario:descargar_plantilla' %} |
| inventario/productos.html | 21 | a | link | (texto interno) | {% url 'inventario:registrar_movimiento_manual' %} |
| inventario/productos.html | 25 | a | link | (texto interno) | {% url 'inventario:pdf_inventario' %} |
| inventario/productos.html | 29 | a | link | (texto interno) | {% url 'inventario:dashboard' %} |
| inventario/productos.html | 64 | button | submit | (texto interno) | formulario/JS |
| inventario/productos.html | 115 | a | link | (texto interno) | {% url 'inventario:editar_producto_inventario' producto.id %} |
| inventario/productos.html | 120 | a | link | (texto interno) | {% url 'inventario:kardex_producto' producto.id %} |
| inventario/productos.html | 126 | a | link | (texto interno) | {% url 'inventario:desactivar_producto_inventario' producto.id %} |
| inventario/receta_produccion_detalle.html | 1 | a | link | (texto interno) | {% url 'inventario:receta_editar' receta.pk %} |
| inventario/receta_produccion_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/receta_produccion_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/receta_produccion_detalle.html | 1 | a | link | (texto interno) | {% url 'documentos:cargar' 'inventario' 'recetaproduccion' receta.pk %} |
| inventario/receta_produccion_detalle.html | 1 | a | link | (texto interno) | {% url 'documentos:detalle' d.pk %} |
| inventario/recetas.html | 15 | a | link | (texto interno) | {% url 'inventario:dashboard' %} |
| inventario/recetas.html | 58 | button | submit | (texto interno) | formulario/JS |
| inventario/recetas.html | 109 | button | submit | (texto interno) | formulario/JS |
| inventario/recetas.html | 151 | a | link | (texto interno) | {% url 'inventario:detalle_receta' receta.id %} |
| inventario/recetas_produccion_lista.html | 1 | a | link | (texto interno) | {% url 'inventario:receta_crear' %} |
| inventario/recetas_produccion_lista.html | 1 | input | submit | {{ q }} | formulario/JS |
| inventario/recetas_produccion_lista.html | 1 | button | submit | (texto interno) | formulario/JS |
| inventario/recetas_produccion_lista.html | 1 | a | link | (texto interno) | {% url 'inventario:receta_detalle' r.pk %} |
| inventario/recetas_produccion_lista.html | 1 | a | link | (texto interno) | {% url 'inventario:receta_detalle' r.pk %} |
| inventario/registrar_movimiento.html | 15 | a | link | (texto interno) | {% url 'inventario:movimientos' %} |
| inventario/registrar_movimiento.html | 70 | button | submit | (texto interno) | formulario/JS |
| login.html | 363 | button | button | Mostrar contraseña | formulario/JS |
| login.html | 374 | button | submit | (texto interno) | formulario/JS |
| login.html | 384 | a | link | (texto interno) | /password-reset/ |
| login.html | 385 | a | link | (texto interno) | /registro/ |
| mapa_centros.html | 18 | a | link | (texto interno) | {% url 'carga_centros' %} |
| mapa_centros.html | 43 | button | submit | (texto interno) | formulario/JS |
| mapa_centros.html | 44 | a | link | (texto interno) | {% url 'mapa_centros' %} |
| mapa_centros.html | 94 | button | submit | (texto interno) | formulario/JS |
| mi_empresa.html | 14 | a | link | (texto interno) | {% url 'inicio' %} |
| mi_empresa.html | 132 | button | submit | (texto interno) | formulario/JS |
| mi_empresa.html | 180 | button | submit | (texto interno) | formulario/JS |
| preparar_nota_aclaratoria.html | 15 | a | link | (texto interno) | {% url 'buscar_conduces' %} |
| preparar_nota_aclaratoria.html | 73 | button | submit | (texto interno) | formulario/JS |
| preparar_nota_aclaratoria.html | 77 | a | link | (texto interno) | {% url 'buscar_conduces' %} |
| registration/password_reset_complete.html | 2 | a | link | (texto interno) | /login/ |
| registration/password_reset_confirm.html | 6 | button | submit | (texto interno) | formulario/JS |
| registration/password_reset_done.html | 46 | a | link | (texto interno) | {% url 'login_usuario' %} |
| registration/password_reset_form.html | 223 | button | submit | (texto interno) | formulario/JS |
| registration/password_reset_form.html | 230 | a | link | (texto interno) | /login/ |
| registro.html | 268 | button | submit | (texto interno) | formulario/JS |
| registro.html | 275 | a | link | (texto interno) | {% url 'login_usuario' %} |
| verificar_correo.html | 63 | button | submit | (texto interno) | formulario/JS |
| verificar_correo.html | 82 | a | link | (texto interno) | formulario/JS |
| vista_conduce.html | 165 | button | submit | (texto interno) | formulario/JS |
| vista_conduce.html | 166 | a | link | (texto interno) | /conduce/{{ conduce.id }}/editar/ |
| vista_conduce.html | 167 | a | link | (texto interno) | /conduce/{{ conduce.id }}/anular/ |
| vista_conduce.html | 168 | a | link | (texto interno) | /buscar-conduces/ |
| vista_conduce.html | 169 | a | link | (texto interno) | /admin/conduces/conduce/ |
| workflow/bandeja.html | 1 | a | link | (texto interno) | #pendientes |
| workflow/bandeja.html | 1 | a | link | (texto interno) | #completadas |
| workflow/bandeja.html | 1 | a | link | (texto interno) | {% url 'workflow:suplencias' %} |
| workflow/bandeja.html | 1 | a | link | (texto interno) | {% url 'workflow:instancia' t.instancia_id %} |
| workflow/dashboard.html | 1 | a | link | (texto interno) | {% url 'workflow:bandeja' %} |
| workflow/dashboard.html | 1 | a | link | (texto interno) | {% url 'workflow:reglas' %} |
| workflow/form.html | 1 | button | submit | (texto interno) | formulario/JS |
| workflow/instancia.html | 1 | button | submit | (texto interno) | {% url 'workflow:decidir' instancia.pk 'aprobar' %} |
| workflow/instancia.html | 1 | button | submit | (texto interno) | {% url 'workflow:decidir' instancia.pk 'abstenerse' %} |
| workflow/instancia.html | 1 | button | submit | (texto interno) | {% url 'workflow:decidir' instancia.pk 'rechazar' %} |
| workflow/instancia.html | 1 | button | submit | (texto interno) | {% url 'workflow:decidir' instancia.pk 'devolver' %} |
| workflow/regla_detalle.html | 1 | a | link | (texto interno) | #resumen |
| workflow/regla_detalle.html | 1 | a | link | (texto interno) | #condiciones |
| workflow/regla_detalle.html | 1 | a | link | (texto interno) | #niveles |
| workflow/regla_detalle.html | 1 | a | link | (texto interno) | #asignadores |
| workflow/regla_detalle.html | 1 | a | link | (texto interno) | #versiones |
| workflow/regla_detalle.html | 1 | a | link | (texto interno) | #validacion |
| workflow/regla_detalle.html | 1 | a | link | (texto interno) | {% url 'workflow:regla_editar' regla.pk %} |
| workflow/regla_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| workflow/regla_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| workflow/regla_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| workflow/regla_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| workflow/regla_detalle.html | 1 | button | submit | (texto interno) | formulario/JS |
| workflow/reglas.html | 1 | input | submit | {{ request.GET.q }} | formulario/JS |
| workflow/reglas.html | 1 | button | submit | (texto interno) | formulario/JS |
| workflow/reglas.html | 1 | a | link | (texto interno) | {% url 'workflow:regla_crear' %} |
| workflow/reglas.html | 1 | a | link | (texto interno) | {% url 'workflow:regla_detalle' r.pk %} |
| workflow/reportes.html | 1 | a | link | (texto interno) | {% url 'workflow:exportar' %} |
| workflow/suplencias.html | 1 | button | submit | (texto interno) | formulario/JS |
