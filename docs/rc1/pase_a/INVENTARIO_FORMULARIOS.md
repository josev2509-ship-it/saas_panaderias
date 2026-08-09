# Inventario de formularios

Total estático: 215 formularios. Los POST visibles son además verificados por el crawler QA.

| Template | Línea | Método | Action | CSRF |
|---|---|---|---|---|
| agregar_dia_no_docencia.html | 20 | POST | actual | Sí |
| buscar_conduces.html | 35 | GET | actual | No/NA |
| buscar_conduces.html | 96 | GET | {% url 'preparar_nota_aclaratoria' %} | No/NA |
| buscar_conduces.html | 115 | POST | {% url 'acciones_conduces' %} | Sí |
| carga_centros.html | 28 | GET | actual | No/NA |
| carga_centros.html | 51 | POST | {% url 'crear_centro' %} | Sí |
| carga_centros.html | 110 | POST | {% url 'cargar_centros_excel' %} | Sí |
| carga_centros.html | 164 | POST | {% url 'eliminar_centro' centro.id %} | Sí |
| carga_masiva.html | 76 | POST | /cargar-centros/ | Sí |
| carga_masiva.html | 90 | POST | /cargar-menu/ | Sí |
| carga_menu.html | 29 | GET | actual | No/NA |
| carga_menu.html | 58 | POST | {% url 'crear_menu_diario' %} | Sí |
| carga_menu.html | 96 | POST | {% url 'cargar_menu_excel' %} | Sí |
| carga_menu.html | 143 | POST | {% url 'eliminar_menu_diario' menu.id %} | Sí |
| cargar_excel.html | 10 | POST | actual | Sí |
| cartas_administrativas.html | 31 | POST | {% url 'generar_carta_pdf' %} | Sí |
| catalogos/form.html | 3 | POST | actual | Sí |
| catalogos/lista.html | 3 | GET | actual | No/NA |
| comercial/cliente_detalle.html | 5 | POST | {% url 'comercial:cliente_cambiar_estado' cliente.pk %} | Sí |
| comercial/cliente_form.html | 3 | POST | actual | Sí |
| comercial/clientes_lista.html | 10 | GET | actual | No/NA |
| comercial/configuracion/dashboard.html | 2 | POST | {% url 'comercial:readiness_ejecutar' %} | Sí |
| comercial/configuracion/detalle.html | 1 | POST | {% url 'comercial:politica_accion' tipo objeto.pk 'activar' %} | Sí |
| comercial/configuracion/detalle.html | 1 | POST | {% url 'comercial:politica_accion' tipo objeto.pk 'versionar' %} | Sí |
| comercial/configuracion/detalle.html | 1 | POST | {% url 'comercial:catalogo_estado' tipo objeto.pk %} | Sí |
| comercial/configuracion/form.html | 1 | POST | actual | Sí |
| comercial/configuracion/reportes.html | 1 | GET | actual | No/NA |
| comercial/configuracion/secuencias.html | 1 | POST | actual | Sí |
| comercial/contacto_form.html | 2 | POST | actual | Sí |
| comercial/crm/detalle.html | 1 | POST | {% url 'comercial:prospecto_accion' objeto.pk 'contactar' %} | Sí |
| comercial/crm/detalle.html | 1 | POST | {% url 'comercial:prospecto_accion' objeto.pk 'calificar' %} | Sí |
| comercial/crm/detalle.html | 1 | POST | {% url 'comercial:prospecto_accion' objeto.pk 'convertir' %} | Sí |
| comercial/crm/detalle.html | 1 | POST | {% url 'comercial:oportunidad_accion' objeto.pk 'etapa' %} | Sí |
| comercial/crm/detalle.html | 1 | POST | {% url 'comercial:actividad_accion' objeto.pk 'completar' %} | Sí |
| comercial/crm/form.html | 1 | POST | actual | Sí |
| comercial/crm/lista.html | 7 | GET | actual | No/NA |
| comercial/crm/lista.html | 8 | POST | actual | Sí |
| comercial/direccion_form.html | 2 | POST | actual | Sí |
| comercial/o2c/cliente360.html | 1 | POST | {% url 'comercial:cliente_360_accion' cliente.pk 'riesgo' %} | Sí |
| comercial/o2c/cotizacion.html | 1 | POST | actual | Sí |
| comercial/o2c/cotizacion.html | 1 | POST | {% url 'comercial:cotizacion_accion' objeto.pk 'revision' %} | Sí |
| comercial/o2c/cotizacion.html | 1 | POST | {% url 'comercial:cotizacion_accion' objeto.pk 'aprobar' %} | Sí |
| comercial/o2c/cotizacion.html | 1 | POST | {% url 'comercial:cotizacion_accion' objeto.pk 'enviar' %} | Sí |
| comercial/o2c/cotizacion.html | 1 | POST | {% url 'comercial:cotizacion_accion' objeto.pk 'aceptar' %} | Sí |
| comercial/o2c/cotizacion.html | 1 | POST | {% url 'comercial:cotizacion_accion' objeto.pk 'convertir' %} | Sí |
| comercial/o2c/detalle.html | 1 | POST | actual | Sí |
| comercial/o2c/detalle.html | 1 | POST | {% url 'comercial:lista_activar' objeto.pk %} | Sí |
| comercial/o2c/form.html | 1 | POST | actual | Sí |
| comercial/o2c/simulador.html | 1 | POST | actual | Sí |
| comercial/o2c_full/lista.html | 1 | POST | {% url 'comercial:o2c_reserva_preparar' x.pk %} | Sí |
| comercial/o2c_full/lista.html | 1 | POST | {% url 'comercial:o2c_preparacion_validar' x.pk %} | Sí |
| comercial/o2c_full/lista.html | 1 | POST | {% url 'comercial:o2c_picking_completar' x.pk %} | Sí |
| comercial/o2c_full/lista.html | 1 | POST | {% url 'comercial:o2c_packing_despachar' x.pk %} | Sí |
| comercial/o2c_full/lista.html | 1 | POST | {% url 'comercial:o2c_despacho_conduce' x.pk %} | Sí |
| comercial/o2c_full/lista.html | 1 | POST | {% url 'comercial:o2c_conduce_entregar' x.pk %} | Sí |
| comercial/o2c_full/lista.html | 1 | POST | {% url 'comercial:o2c_entrega_facturar' x.pk %} | Sí |
| comercial/o2c_full/lista.html | 1 | POST | {% url 'comercial:o2c_cobrar' x.pk %} | Sí |
| comercial/pedido_detalle.html | 2 | POST | {% url 'comercial:pedido_enviar_aprobacion' pedido.pk %} | Sí |
| comercial/pedido_detalle.html | 2 | POST | {% url 'comercial:pedido_aprobar' pedido.pk %} | Sí |
| comercial/pedido_detalle.html | 2 | POST | {% url 'comercial:pedido_duplicar' pedido.pk %} | Sí |
| comercial/pedido_detalle.html | 6 | POST | {% url 'comercial:pedido_rechazar' pedido.pk %} | Sí |
| comercial/pedido_detalle.html | 6 | POST | {% url 'comercial:pedido_reabrir' pedido.pk %} | Sí |
| comercial/pedido_detalle.html | 6 | POST | {% url 'comercial:pedido_cancelar' pedido.pk %} | Sí |
| comercial/pedido_form.html | 3 | POST | actual | Sí |
| comercial/pedidos_lista.html | 4 | GET | actual | No/NA |
| comercial/programacion.html | 2 | GET | actual | No/NA |
| components/filter_bar.html | 1 | GET | actual | No/NA |
| compras/detalle.html | 7 | POST | actual | Sí |
| compras/detalle.html | 8 | POST | {% url 'compras:agregar_relacion' proveedor.pk 'contacto' %} | Sí |
| compras/detalle.html | 9 | POST | {% url 'compras:agregar_relacion' proveedor.pk 'direccion' %} | Sí |
| compras/detalle.html | 10 | POST | {% url 'compras:agregar_relacion' proveedor.pk 'producto' %} | Sí |
| compras/detalle.html | 13 | POST | actual | Sí |
| compras/detalle.html | 13 | POST | {% url 'compras:agregar_relacion' proveedor.pk 'cuenta' %} | Sí |
| compras/detalle.html | 16 | POST | {% url 'compras:agregar_relacion' proveedor.pk 'legado' %} | Sí |
| compras/expedientes/detalle.html | 1 | POST | {% url 'compras:expediente_accion' expediente.pk 'abrir' %} | Sí |
| compras/expedientes/detalle.html | 1 | POST | {% url 'compras:expediente_accion' expediente.pk 'preparar' %} | Sí |
| compras/expedientes/detalle.html | 1 | POST | {% url 'compras:expediente_accion' expediente.pk 'salud' %} | Sí |
| compras/expedientes/detalle.html | 1 | POST | {% url 'compras:expediente_accion' expediente.pk 'cancelar' %} | Sí |
| compras/expedientes/detalle.html | 1 | POST | {% url 'compras:expediente_accion' expediente.pk 'desierto' %} | Sí |
| compras/expedientes/form.html | 1 | POST | actual | Sí |
| compras/form.html | 4 | POST | actual | Sí |
| compras/lista.html | 5 | GET | actual | No/NA |
| compras/p2p/finance_detail.html | 7 | POST | {% url 'compras:p2p_finance_nota_accion' recurso\|slice:'6:' obj.pk 'enviar' %} | Sí |
| compras/p2p/finance_detail.html | 8 | POST | {% url 'compras:p2p_finance_nota_accion' recurso\|slice:'6:' obj.pk 'aprobar' %} | Sí |
| compras/p2p/finance_detail.html | 8 | POST | {% url 'compras:p2p_finance_nota_accion' recurso\|slice:'6:' obj.pk 'rechazar' %} | Sí |
| compras/p2p/finance_detail.html | 9 | POST | {% url 'compras:p2p_finance_nota_accion' recurso\|slice:'6:' obj.pk 'aplicar' %} | Sí |
| compras/p2p/finance_detail.html | 10 | POST | {% url 'compras:p2p_finance_nota_accion' recurso\|slice:'6:' obj.pk 'anular' %} | Sí |
| compras/p2p/finance_detail.html | 11 | POST | {% url 'compras:p2p_finance_nota_accion' recurso\|slice:'6:' obj.pk 'revertir' %} | Sí |
| compras/p2p/finance_detail.html | 13 | POST | {% url 'compras:p2p_finance_anticipo_accion' obj.pk 'aprobar' %} | Sí |
| compras/p2p/finance_detail.html | 13 | POST | {% url 'compras:p2p_finance_anticipo_accion' obj.pk 'rechazar' %} | Sí |
| compras/p2p/finance_detail.html | 13 | POST | {% url 'compras:p2p_finance_anticipo_accion' obj.pk 'aplicar' %} | Sí |
| compras/p2p/finance_detail.html | 13 | POST | {% url 'compras:p2p_finance_anticipo_accion' obj.pk 'anular' %} | Sí |
| compras/p2p/finance_detail.html | 13 | POST | {% url 'compras:p2p_finance_anticipo_accion' obj.pk 'revertir' %} | Sí |
| compras/p2p/finance_detail.html | 14 | POST | {% url 'compras:p2p_finance_retencion_accion' obj.pk 'aprobar' %} | Sí |
| compras/p2p/finance_detail.html | 14 | POST | {% url 'compras:p2p_finance_retencion_accion' obj.pk 'rechazar' %} | Sí |
| compras/p2p/finance_detail.html | 14 | POST | {% url 'compras:p2p_finance_retencion_accion' obj.pk 'aplicar' %} | Sí |
| compras/p2p/finance_detail.html | 14 | POST | {% url 'compras:p2p_finance_retencion_accion' obj.pk 'certificado' %} | Sí |
| compras/p2p/finance_detail.html | 14 | POST | {% url 'compras:p2p_finance_retencion_accion' obj.pk 'revertir' %} | Sí |
| compras/p2p/finance_detail.html | 14 | POST | {% url 'compras:p2p_finance_retencion_accion' obj.pk 'anular' %} | Sí |
| compras/p2p/finance_detail.html | 15 | POST | {% url 'compras:p2p_compensacion_accion' obj.pk 'aprobar' %} | Sí |
| compras/p2p/finance_detail.html | 15 | POST | {% url 'compras:p2p_compensacion_accion' obj.pk 'aplicar' %} | Sí |
| compras/p2p/finance_detail.html | 15 | POST | {% url 'compras:p2p_compensacion_accion' obj.pk 'anular' %} | Sí |
| compras/p2p/finance_detail.html | 15 | POST | {% url 'compras:p2p_compensacion_accion' obj.pk 'revertir' %} | Sí |
| compras/p2p/finance_detail.html | 16 | POST | {% url 'compras:p2p_finance_matching_accion' linea.pk 'desconciliar' %} | Sí |
| compras/p2p/finance_detail.html | 16 | POST | {% url 'compras:p2p_finance_matching_accion' linea.pk 'manual' %} | Sí |
| compras/p2p/finance_list.html | 1 | GET | actual | No/NA |
| compras/p2p/recurso_lista.html | 1 | GET | actual | No/NA |
| compras/p2p/settlement_form.html | 1 | POST | actual | Sí |
| compras/p2p/wizard.html | 1 | POST | actual | Sí |
| compras/p2p/wizard_enterprise.html | 2 | POST | actual | Sí |
| compras/p2p_dashboard.html | 1 | POST | {% url 'compras:p2p_exportacion' %} | Sí |
| compras/rfq/detalle.html | 9 | POST | {% url 'compras:rfq_linea_editar' l.pk %} | Sí |
| compras/rfq/detalle.html | 11 | POST | {% url 'compras:rfq_accion' rfq.pk 'lineas' %} | Sí |
| compras/rfq/detalle.html | 13 | POST | {% url 'compras:rfq_agregar' rfq.pk 'criterio' %} | Sí |
| compras/rfq/detalle.html | 14 | POST | {% url 'compras:rfq_agregar' rfq.pk 'regla' %} | Sí |
| compras/rfq/detalle.html | 15 | POST | {% url 'compras:invitacion_contacto' i.pk %} | Sí |
| compras/rfq/detalle.html | 15 | POST | {% url 'compras:invitacion_accion' i.pk 'enviar' %} | Sí |
| compras/rfq/detalle.html | 15 | POST | {% url 'compras:invitacion_accion' i.pk 'confirmar' %} | Sí |
| compras/rfq/detalle.html | 15 | POST | {% url 'compras:invitacion_accion' i.pk 'declinar' %} | Sí |
| compras/rfq/detalle.html | 15 | POST | {% url 'compras:invitacion_accion' i.pk 'sin-respuesta' %} | Sí |
| compras/rfq/detalle.html | 15 | POST | {% url 'compras:invitacion_accion' i.pk 'retirar' %} | Sí |
| compras/rfq/detalle.html | 15 | POST | {% url 'compras:rfq_agregar' rfq.pk 'proveedor' %} | Sí |
| compras/rfq/detalle.html | 17 | POST | {% url 'compras:rfq_accion' rfq.pk 'revision' %} | Sí |
| compras/rfq/detalle.html | 17 | POST | {% url 'compras:rfq_accion' rfq.pk 'borrador' %} | Sí |
| compras/rfq/detalle.html | 17 | POST | {% url 'compras:rfq_accion' rfq.pk 'publicar' %} | Sí |
| compras/rfq/detalle.html | 17 | POST | {% url 'compras:rfq_accion' rfq.pk 'abrir' %} | Sí |
| compras/rfq/detalle.html | 17 | POST | {% url 'compras:rfq_accion' rfq.pk 'cerrar' %} | Sí |
| compras/rfq/detalle.html | 17 | POST | {% url 'compras:rfq_accion' rfq.pk 'cancelar' %} | Sí |
| compras/rfq/detalle.html | 17 | POST | {% url 'compras:rfq_accion' rfq.pk 'versionar' %} | Sí |
| compras/rfq/detalle.html | 18 | POST | {% url 'compras:rfq_extender' rfq.pk %} | Sí |
| compras/rfq/form.html | 1 | POST | actual | Sí |
| compras/solicitudes/detalle.html | 6 | POST | {% url 'compras:solicitud_linea_retirar' solicitud.pk l.pk %} | Sí |
| compras/solicitudes/detalle.html | 6 | POST | {% url 'compras:solicitud_linea_agregar' solicitud.pk %} | Sí |
| compras/solicitudes/detalle.html | 9 | POST | {% url 'compras:solicitud_accion' solicitud.pk 'marcar-lista' %} | Sí |
| compras/solicitudes/detalle.html | 9 | POST | {% url 'compras:solicitud_accion' solicitud.pk 'borrador' %} | Sí |
| compras/solicitudes/detalle.html | 9 | POST | {% url 'compras:solicitud_accion' solicitud.pk 'enviar' %} | Sí |
| compras/solicitudes/detalle.html | 9 | POST | {% url 'compras:solicitud_accion' solicitud.pk 'duplicar' %} | Sí |
| compras/solicitudes/form.html | 3 | POST | actual | Sí |
| compras/solicitudes/lista.html | 4 | GET | actual | No/NA |
| contabilidad/crear_factura_606.html | 22 | POST | {% url 'contabilidad:crear_factura_606' %} | Sí |
| contabilidad/crear_proveedor.html | 28 | POST | actual | Sí |
| core/design_system.html | 20 | GET | actual | No/NA |
| core/detalle_tecnico.html | 8 | POST | {% url 'core:evento_reintentar' objeto.pk %} | Sí |
| core/detalle_tecnico.html | 8 | POST | {% url 'core:idempotencia_cerrar' objeto.pk %} | Sí |
| core/experience/activity.html | 3 | GET | actual | No/NA |
| core/experience/search.html | 1 | GET | actual | No/NA |
| core/experience/workspace.html | 3 | POST | {% url 'core:favorito_toggle' %} | Sí |
| core/form_tecnico.html | 2 | POST | actual | Sí |
| core/lista_tecnica.html | 4 | GET | actual | No/NA |
| core/lista_tecnica.html | 5 | POST | {% url 'core:diagnostico_producto' %} | Sí |
| core/lista_tecnica.html | 5 | POST | {% url 'core:previsualizar_saldo' %} | Sí |
| core/reconstruccion_preview.html | 2 | POST | {% url 'core:reconstruir_saldo' %} | Sí |
| documentos/documento_detalle.html | 6 | POST | {% url 'documentos:reemplazar' documento.pk %} | Sí |
| documentos/documento_detalle.html | 7 | POST | {% url 'documentos:anular' documento.pk %} | Sí |
| documentos/documento_form.html | 4 | POST | actual | Sí |
| documentos/documentos_lista.html | 4 | GET | actual | No/NA |
| editar_centro.html | 9 | POST | actual | Sí |
| editar_conduce.html | 6 | POST | actual | Sí |
| editar_dia_no_docencia.html | 20 | POST | actual | Sí |
| editar_factura.html | 6 | POST | actual | Sí |
| editar_menu.html | 7 | POST | actual | Sí |
| editar_producto_facturacion.html | 6 | POST | actual | Sí |
| facturacion.html | 57 | POST | {% url 'generar_factura' %} | Sí |
| facturacion.html | 111 | POST | {% url 'crear_producto_facturacion' %} | Sí |
| facturacion.html | 178 | POST | {% url 'eliminar_producto_facturacion' producto.id %} | Sí |
| facturacion.html | 201 | POST | {% url 'crear_comprobante_fiscal' %} | Sí |
| facturacion.html | 242 | POST | {% url 'crear_rango_ncf' %} | Sí |
| facturacion.html | 313 | POST | {% url 'editar_comprobante' comprobante.id %} | Sí |
| facturacion.html | 362 | POST | {% url 'eliminar_comprobante' comprobante.id %} | Sí |
| facturacion.html | 452 | POST | {% url 'anular_factura' factura.id %} | Sí |
| facturacion.html | 458 | POST | {% url 'eliminar_factura' factura.id %} | Sí |
| generar_conduces.html | 30 | POST | actual | Sí |
| inventario/crear_prestamo.html | 20 | POST | actual | Sí |
| inventario/detalle_orden_compra.html | 96 | POST | {% url 'inventario:agregar_producto_manual_orden' orden.id %} | Sí |
| inventario/detalle_orden_compra.html | 164 | POST | {% url 'inventario:actualizar_detalle_orden' detalle.id %} | Sí |
| inventario/detalle_receta.html | 60 | POST | {% url 'inventario:agregar_ingrediente_receta' receta.id %} | Sí |
| inventario/editar_producto.html | 20 | POST | actual | Sí |
| inventario/generar_orden_compra.html | 30 | POST | actual | Sí |
| inventario/orden_detalle.html | 1 | POST | {% url 'inventario:orden_programar' orden.pk %} | Sí |
| inventario/orden_detalle.html | 1 | POST | {% url 'inventario:orden_iniciar' orden.pk %} | Sí |
| inventario/orden_detalle.html | 1 | POST | {% url 'inventario:orden_completar' orden.pk %} | Sí |
| inventario/ordenes_lista.html | 1 | GET | actual | No/NA |
| inventario/plan_detalle.html | 1 | POST | {% url 'inventario:plan_aprobar' plan.pk %} | Sí |
| inventario/plan_detalle.html | 1 | POST | {% url 'inventario:plan_generar_ordenes' plan.pk %} | Sí |
| inventario/planes_lista.html | 1 | GET | actual | No/NA |
| inventario/prestamos.html | 64 | POST | {% url 'inventario:registrar_devolucion_prestamo' prestamo.id %} | Sí |
| inventario/produccion.html | 33 | POST | {% url 'inventario:generar_produccion_desde_menu' %} | Sí |
| inventario/produccion_form.html | 1 | POST | actual | Sí |
| inventario/produccion_programacion.html | 1 | GET | actual | No/NA |
| inventario/productos.html | 49 | POST | {% url 'inventario:cargar_excel' %} | Sí |
| inventario/receta_produccion_detalle.html | 1 | POST | {% url 'inventario:receta_duplicar' receta.pk %} | Sí |
| inventario/receta_produccion_detalle.html | 1 | POST | {% url 'inventario:receta_cambiar_estado' receta.pk %} | Sí |
| inventario/recetas.html | 35 | POST | {% url 'inventario:crear_producto_produccion' %} | Sí |
| inventario/recetas.html | 70 | POST | {% url 'inventario:crear_receta' %} | Sí |
| inventario/recetas_produccion_lista.html | 1 | GET | actual | No/NA |
| inventario/registrar_movimiento.html | 20 | POST | actual | Sí |
| login.html | 349 | POST | actual | Sí |
| mapa_centros.html | 34 | GET | actual | No/NA |
| mapa_centros.html | 65 | POST | {% url 'actualizar_ubicacion_centro' %} | Sí |
| mi_empresa.html | 31 | POST | actual | Sí |
| mi_empresa.html | 143 | POST | {% url 'crear_usuario_empresa' %} | Sí |
| preparar_nota_aclaratoria.html | 25 | GET | {% url 'generar_nota_aclaratoria_pdf' %} | No/NA |
| registration/password_reset_confirm.html | 3 | POST | actual | Sí |
| registration/password_reset_form.html | 219 | POST | actual | Sí |
| registro.html | 245 | POST | {% url 'registro' %} | Sí |
| verificar_correo.html | 43 | POST | actual | Sí |
| workflow/form.html | 1 | POST | actual | Sí |
| workflow/instancia.html | 1 | POST | actual | Sí |
| workflow/regla_detalle.html | 1 | POST | {% url 'workflow:regla_accion' regla.pk 'versionar' %} | Sí |
| workflow/regla_detalle.html | 1 | POST | {% url 'workflow:regla_accion' regla.pk 'activar' %} | Sí |
| workflow/regla_detalle.html | 1 | POST | {% url 'workflow:regla_agregar' regla.pk 'condicion' %} | Sí |
| workflow/regla_detalle.html | 1 | POST | {% url 'workflow:nivel_agregar' regla.pk n.pk 'asignador' %} | Sí |
| workflow/regla_detalle.html | 1 | POST | {% url 'workflow:regla_agregar' regla.pk 'nivel' %} | Sí |
| workflow/reglas.html | 1 | GET | actual | No/NA |
| workflow/suplencias.html | 1 | POST | actual | Sí |
