# Inventario de rutas

Total: 1467. Fuente: resolver Django, sin exclusiones.

| Ruta | Nombre | Clasificación | Dinámica | Callback |
|---|---|---|---|---|
| / | inicio | GET SEGURA | No | conduces.views.inicio |
| /^media/(?P<path>.*)$ | — | GET SEGURA | Sí | django.views.static.serve |
| /_sedl/catalog/ | sedl:catalog | GET SEGURA | No | design_system.views.catalog |
| /acciones-conduces/ | acciones_conduces | GET SEGURA | No | conduces.views.acciones_conduces |
| /admin/ | admin:index | ADMIN | No | django.contrib.admin.sites.index |
| /admin/(?P<url>.*)$ | admin | ADMIN | Sí | django.contrib.admin.sites.catch_all_view |
| /admin/^(?P<app_label>core\|comercial\|auth\|conduces\|inventario\|contabilidad\|documentos\|auditoria\|catalogos\|compras\|workflow)/$ | admin:app_list | ADMIN | Sí | django.contrib.admin.sites.app_index |
| /admin/auditoria/eventoauditoria/ | admin:auditoria_eventoauditoria_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/auditoria/eventoauditoria/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/auditoria/eventoauditoria/<path:object_id>/change/ | admin:auditoria_eventoauditoria_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/auditoria/eventoauditoria/<path:object_id>/delete/ | admin:auditoria_eventoauditoria_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/auditoria/eventoauditoria/<path:object_id>/history/ | admin:auditoria_eventoauditoria_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/auditoria/eventoauditoria/add/ | admin:auditoria_eventoauditoria_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/auth/group/ | admin:auth_group_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/auth/group/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/auth/group/<path:object_id>/change/ | admin:auth_group_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/auth/group/<path:object_id>/delete/ | admin:auth_group_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/auth/group/<path:object_id>/history/ | admin:auth_group_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/auth/group/add/ | admin:auth_group_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/auth/user/ | admin:auth_user_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/auth/user/<id>/password/ | admin:auth_user_password_change | ADMIN | Sí | django.contrib.auth.admin.user_change_password |
| /admin/auth/user/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/auth/user/<path:object_id>/change/ | admin:auth_user_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/auth/user/<path:object_id>/delete/ | admin:auth_user_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/auth/user/<path:object_id>/history/ | admin:auth_user_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/auth/user/add/ | admin:auth_user_add | ADMIN | No | django.contrib.auth.admin.add_view |
| /admin/autocomplete/ | admin:autocomplete | ADMIN | No | django.contrib.admin.sites.autocomplete_view |
| /admin/catalogos/almacen/ | admin:catalogos_almacen_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/catalogos/almacen/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/catalogos/almacen/<path:object_id>/change/ | admin:catalogos_almacen_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/catalogos/almacen/<path:object_id>/delete/ | admin:catalogos_almacen_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/catalogos/almacen/<path:object_id>/history/ | admin:catalogos_almacen_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/catalogos/almacen/add/ | admin:catalogos_almacen_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/catalogos/centrocosto/ | admin:catalogos_centrocosto_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/catalogos/centrocosto/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/catalogos/centrocosto/<path:object_id>/change/ | admin:catalogos_centrocosto_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/catalogos/centrocosto/<path:object_id>/delete/ | admin:catalogos_centrocosto_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/catalogos/centrocosto/<path:object_id>/history/ | admin:catalogos_centrocosto_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/catalogos/centrocosto/add/ | admin:catalogos_centrocosto_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/catalogos/condicionpago/ | admin:catalogos_condicionpago_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/catalogos/condicionpago/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/catalogos/condicionpago/<path:object_id>/change/ | admin:catalogos_condicionpago_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/catalogos/condicionpago/<path:object_id>/delete/ | admin:catalogos_condicionpago_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/catalogos/condicionpago/<path:object_id>/history/ | admin:catalogos_condicionpago_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/catalogos/condicionpago/add/ | admin:catalogos_condicionpago_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/catalogos/conversionunidad/ | admin:catalogos_conversionunidad_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/catalogos/conversionunidad/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/catalogos/conversionunidad/<path:object_id>/change/ | admin:catalogos_conversionunidad_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/catalogos/conversionunidad/<path:object_id>/delete/ | admin:catalogos_conversionunidad_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/catalogos/conversionunidad/<path:object_id>/history/ | admin:catalogos_conversionunidad_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/catalogos/conversionunidad/add/ | admin:catalogos_conversionunidad_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/catalogos/impuesto/ | admin:catalogos_impuesto_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/catalogos/impuesto/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/catalogos/impuesto/<path:object_id>/change/ | admin:catalogos_impuesto_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/catalogos/impuesto/<path:object_id>/delete/ | admin:catalogos_impuesto_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/catalogos/impuesto/<path:object_id>/history/ | admin:catalogos_impuesto_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/catalogos/impuesto/add/ | admin:catalogos_impuesto_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/catalogos/moneda/ | admin:catalogos_moneda_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/catalogos/moneda/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/catalogos/moneda/<path:object_id>/change/ | admin:catalogos_moneda_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/catalogos/moneda/<path:object_id>/delete/ | admin:catalogos_moneda_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/catalogos/moneda/<path:object_id>/history/ | admin:catalogos_moneda_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/catalogos/moneda/add/ | admin:catalogos_moneda_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/catalogos/monedaempresa/ | admin:catalogos_monedaempresa_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/catalogos/monedaempresa/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/catalogos/monedaempresa/<path:object_id>/change/ | admin:catalogos_monedaempresa_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/catalogos/monedaempresa/<path:object_id>/delete/ | admin:catalogos_monedaempresa_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/catalogos/monedaempresa/<path:object_id>/history/ | admin:catalogos_monedaempresa_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/catalogos/monedaempresa/add/ | admin:catalogos_monedaempresa_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/catalogos/tipocompra/ | admin:catalogos_tipocompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/catalogos/tipocompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/catalogos/tipocompra/<path:object_id>/change/ | admin:catalogos_tipocompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/catalogos/tipocompra/<path:object_id>/delete/ | admin:catalogos_tipocompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/catalogos/tipocompra/<path:object_id>/history/ | admin:catalogos_tipocompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/catalogos/tipocompra/add/ | admin:catalogos_tipocompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/catalogos/unidadmedida/ | admin:catalogos_unidadmedida_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/catalogos/unidadmedida/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/catalogos/unidadmedida/<path:object_id>/change/ | admin:catalogos_unidadmedida_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/catalogos/unidadmedida/<path:object_id>/delete/ | admin:catalogos_unidadmedida_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/catalogos/unidadmedida/<path:object_id>/history/ | admin:catalogos_unidadmedida_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/catalogos/unidadmedida/add/ | admin:catalogos_unidadmedida_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/actividadcomercial/ | admin:comercial_actividadcomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/actividadcomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/actividadcomercial/<path:object_id>/change/ | admin:comercial_actividadcomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/actividadcomercial/<path:object_id>/delete/ | admin:comercial_actividadcomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/actividadcomercial/<path:object_id>/history/ | admin:comercial_actividadcomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/actividadcomercial/add/ | admin:comercial_actividadcomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/canalventa/ | admin:comercial_canalventa_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/canalventa/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/canalventa/<path:object_id>/change/ | admin:comercial_canalventa_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/canalventa/<path:object_id>/delete/ | admin:comercial_canalventa_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/canalventa/<path:object_id>/history/ | admin:comercial_canalventa_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/canalventa/add/ | admin:comercial_canalventa_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/cesionfactoring/ | admin:comercial_cesionfactoring_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/cesionfactoring/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/cesionfactoring/<path:object_id>/change/ | admin:comercial_cesionfactoring_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/cesionfactoring/<path:object_id>/delete/ | admin:comercial_cesionfactoring_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/cesionfactoring/<path:object_id>/history/ | admin:comercial_cesionfactoring_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/cesionfactoring/add/ | admin:comercial_cesionfactoring_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/clasificacioncliente/ | admin:comercial_clasificacioncliente_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/clasificacioncliente/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/clasificacioncliente/<path:object_id>/change/ | admin:comercial_clasificacioncliente_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/clasificacioncliente/<path:object_id>/delete/ | admin:comercial_clasificacioncliente_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/clasificacioncliente/<path:object_id>/history/ | admin:comercial_clasificacioncliente_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/clasificacioncliente/add/ | admin:comercial_clasificacioncliente_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/cliente/ | admin:comercial_cliente_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/cliente/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/cliente/<path:object_id>/change/ | admin:comercial_cliente_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/cliente/<path:object_id>/delete/ | admin:comercial_cliente_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/cliente/<path:object_id>/history/ | admin:comercial_cliente_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/cliente/add/ | admin:comercial_cliente_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/conducecomercial/ | admin:comercial_conducecomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/conducecomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/conducecomercial/<path:object_id>/change/ | admin:comercial_conducecomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/conducecomercial/<path:object_id>/delete/ | admin:comercial_conducecomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/conducecomercial/<path:object_id>/history/ | admin:comercial_conducecomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/conducecomercial/add/ | admin:comercial_conducecomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/configuracioncomercialempresa/ | admin:comercial_configuracioncomercialempresa_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/configuracioncomercialempresa/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/configuracioncomercialempresa/<path:object_id>/change/ | admin:comercial_configuracioncomercialempresa_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/configuracioncomercialempresa/<path:object_id>/delete/ | admin:comercial_configuracioncomercialempresa_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/configuracioncomercialempresa/<path:object_id>/history/ | admin:comercial_configuracioncomercialempresa_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/configuracioncomercialempresa/add/ | admin:comercial_configuracioncomercialempresa_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/contactocliente/ | admin:comercial_contactocliente_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/contactocliente/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/contactocliente/<path:object_id>/change/ | admin:comercial_contactocliente_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/contactocliente/<path:object_id>/delete/ | admin:comercial_contactocliente_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/contactocliente/<path:object_id>/history/ | admin:comercial_contactocliente_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/contactocliente/add/ | admin:comercial_contactocliente_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/cotizacionventa/ | admin:comercial_cotizacionventa_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/cotizacionventa/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/cotizacionventa/<path:object_id>/change/ | admin:comercial_cotizacionventa_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/cotizacionventa/<path:object_id>/delete/ | admin:comercial_cotizacionventa_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/cotizacionventa/<path:object_id>/history/ | admin:comercial_cotizacionventa_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/cotizacionventa/add/ | admin:comercial_cotizacionventa_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/cuentaporcobrar/ | admin:comercial_cuentaporcobrar_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/cuentaporcobrar/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/cuentaporcobrar/<path:object_id>/change/ | admin:comercial_cuentaporcobrar_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/cuentaporcobrar/<path:object_id>/delete/ | admin:comercial_cuentaporcobrar_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/cuentaporcobrar/<path:object_id>/history/ | admin:comercial_cuentaporcobrar_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/cuentaporcobrar/add/ | admin:comercial_cuentaporcobrar_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/despachocomercial/ | admin:comercial_despachocomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/despachocomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/despachocomercial/<path:object_id>/change/ | admin:comercial_despachocomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/despachocomercial/<path:object_id>/delete/ | admin:comercial_despachocomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/despachocomercial/<path:object_id>/history/ | admin:comercial_despachocomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/despachocomercial/add/ | admin:comercial_despachocomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/detallecotizacionventa/ | admin:comercial_detallecotizacionventa_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/detallecotizacionventa/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/detallecotizacionventa/<path:object_id>/change/ | admin:comercial_detallecotizacionventa_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/detallecotizacionventa/<path:object_id>/delete/ | admin:comercial_detallecotizacionventa_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/detallecotizacionventa/<path:object_id>/history/ | admin:comercial_detallecotizacionventa_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/detallecotizacionventa/add/ | admin:comercial_detallecotizacionventa_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/detallelistaprecio/ | admin:comercial_detallelistaprecio_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/detallelistaprecio/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/detallelistaprecio/<path:object_id>/change/ | admin:comercial_detallelistaprecio_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/detallelistaprecio/<path:object_id>/delete/ | admin:comercial_detallelistaprecio_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/detallelistaprecio/<path:object_id>/history/ | admin:comercial_detallelistaprecio_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/detallelistaprecio/add/ | admin:comercial_detallelistaprecio_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/detallepedido/ | admin:comercial_detallepedido_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/detallepedido/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/detallepedido/<path:object_id>/change/ | admin:comercial_detallepedido_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/detallepedido/<path:object_id>/delete/ | admin:comercial_detallepedido_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/detallepedido/<path:object_id>/history/ | admin:comercial_detallepedido_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/detallepedido/add/ | admin:comercial_detallepedido_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/direccioncliente/ | admin:comercial_direccioncliente_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/direccioncliente/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/direccioncliente/<path:object_id>/change/ | admin:comercial_direccioncliente_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/direccioncliente/<path:object_id>/delete/ | admin:comercial_direccioncliente_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/direccioncliente/<path:object_id>/history/ | admin:comercial_direccioncliente_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/direccioncliente/add/ | admin:comercial_direccioncliente_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/entregacomercial/ | admin:comercial_entregacomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/entregacomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/entregacomercial/<path:object_id>/change/ | admin:comercial_entregacomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/entregacomercial/<path:object_id>/delete/ | admin:comercial_entregacomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/entregacomercial/<path:object_id>/history/ | admin:comercial_entregacomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/entregacomercial/add/ | admin:comercial_entregacomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/equipocomercial/ | admin:comercial_equipocomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/equipocomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/equipocomercial/<path:object_id>/change/ | admin:comercial_equipocomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/equipocomercial/<path:object_id>/delete/ | admin:comercial_equipocomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/equipocomercial/<path:object_id>/history/ | admin:comercial_equipocomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/equipocomercial/add/ | admin:comercial_equipocomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/facturaventa/ | admin:comercial_facturaventa_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/facturaventa/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/facturaventa/<path:object_id>/change/ | admin:comercial_facturaventa_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/facturaventa/<path:object_id>/delete/ | admin:comercial_facturaventa_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/facturaventa/<path:object_id>/history/ | admin:comercial_facturaventa_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/facturaventa/add/ | admin:comercial_facturaventa_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/fuenteprospecto/ | admin:comercial_fuenteprospecto_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/fuenteprospecto/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/fuenteprospecto/<path:object_id>/change/ | admin:comercial_fuenteprospecto_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/fuenteprospecto/<path:object_id>/delete/ | admin:comercial_fuenteprospecto_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/fuenteprospecto/<path:object_id>/history/ | admin:comercial_fuenteprospecto_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/fuenteprospecto/add/ | admin:comercial_fuenteprospecto_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/historialactividadcomercial/ | admin:comercial_historialactividadcomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/historialactividadcomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/historialactividadcomercial/<path:object_id>/change/ | admin:comercial_historialactividadcomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/historialactividadcomercial/<path:object_id>/delete/ | admin:comercial_historialactividadcomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/historialactividadcomercial/<path:object_id>/history/ | admin:comercial_historialactividadcomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/historialactividadcomercial/add/ | admin:comercial_historialactividadcomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/historialcotizacionventa/ | admin:comercial_historialcotizacionventa_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/historialcotizacionventa/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/historialcotizacionventa/<path:object_id>/change/ | admin:comercial_historialcotizacionventa_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/historialcotizacionventa/<path:object_id>/delete/ | admin:comercial_historialcotizacionventa_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/historialcotizacionventa/<path:object_id>/history/ | admin:comercial_historialcotizacionventa_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/historialcotizacionventa/add/ | admin:comercial_historialcotizacionventa_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/historialestadopedido/ | admin:comercial_historialestadopedido_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/historialestadopedido/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/historialestadopedido/<path:object_id>/change/ | admin:comercial_historialestadopedido_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/historialestadopedido/<path:object_id>/delete/ | admin:comercial_historialestadopedido_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/historialestadopedido/<path:object_id>/history/ | admin:comercial_historialestadopedido_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/historialestadopedido/add/ | admin:comercial_historialestadopedido_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/historialestadoprospecto/ | admin:comercial_historialestadoprospecto_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/historialestadoprospecto/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/historialestadoprospecto/<path:object_id>/change/ | admin:comercial_historialestadoprospecto_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/historialestadoprospecto/<path:object_id>/delete/ | admin:comercial_historialestadoprospecto_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/historialestadoprospecto/<path:object_id>/history/ | admin:comercial_historialestadoprospecto_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/historialestadoprospecto/add/ | admin:comercial_historialestadoprospecto_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/historialetapaoportunidad/ | admin:comercial_historialetapaoportunidad_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/historialetapaoportunidad/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/historialetapaoportunidad/<path:object_id>/change/ | admin:comercial_historialetapaoportunidad_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/historialetapaoportunidad/<path:object_id>/delete/ | admin:comercial_historialetapaoportunidad_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/historialetapaoportunidad/<path:object_id>/history/ | admin:comercial_historialetapaoportunidad_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/historialetapaoportunidad/add/ | admin:comercial_historialetapaoportunidad_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/listaprecio/ | admin:comercial_listaprecio_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/listaprecio/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/listaprecio/<path:object_id>/change/ | admin:comercial_listaprecio_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/listaprecio/<path:object_id>/delete/ | admin:comercial_listaprecio_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/listaprecio/<path:object_id>/history/ | admin:comercial_listaprecio_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/listaprecio/add/ | admin:comercial_listaprecio_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/motivocomercial/ | admin:comercial_motivocomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/motivocomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/motivocomercial/<path:object_id>/change/ | admin:comercial_motivocomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/motivocomercial/<path:object_id>/delete/ | admin:comercial_motivocomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/motivocomercial/<path:object_id>/history/ | admin:comercial_motivocomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/motivocomercial/add/ | admin:comercial_motivocomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/oportunidadcomercial/ | admin:comercial_oportunidadcomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/oportunidadcomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/oportunidadcomercial/<path:object_id>/change/ | admin:comercial_oportunidadcomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/oportunidadcomercial/<path:object_id>/delete/ | admin:comercial_oportunidadcomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/oportunidadcomercial/<path:object_id>/history/ | admin:comercial_oportunidadcomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/oportunidadcomercial/add/ | admin:comercial_oportunidadcomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/packingpedido/ | admin:comercial_packingpedido_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/packingpedido/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/packingpedido/<path:object_id>/change/ | admin:comercial_packingpedido_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/packingpedido/<path:object_id>/delete/ | admin:comercial_packingpedido_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/packingpedido/<path:object_id>/history/ | admin:comercial_packingpedido_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/packingpedido/add/ | admin:comercial_packingpedido_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/pedido/ | admin:comercial_pedido_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/pedido/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/pedido/<path:object_id>/change/ | admin:comercial_pedido_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/pedido/<path:object_id>/delete/ | admin:comercial_pedido_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/pedido/<path:object_id>/history/ | admin:comercial_pedido_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/pedido/add/ | admin:comercial_pedido_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/politicacomision/ | admin:comercial_politicacomision_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/politicacomision/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/politicacomision/<path:object_id>/change/ | admin:comercial_politicacomision_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/politicacomision/<path:object_id>/delete/ | admin:comercial_politicacomision_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/politicacomision/<path:object_id>/history/ | admin:comercial_politicacomision_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/politicacomision/add/ | admin:comercial_politicacomision_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/politicacredito/ | admin:comercial_politicacredito_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/politicacredito/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/politicacredito/<path:object_id>/change/ | admin:comercial_politicacredito_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/politicacredito/<path:object_id>/delete/ | admin:comercial_politicacredito_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/politicacredito/<path:object_id>/history/ | admin:comercial_politicacredito_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/politicacredito/add/ | admin:comercial_politicacredito_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/politicadescuento/ | admin:comercial_politicadescuento_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/politicadescuento/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/politicadescuento/<path:object_id>/change/ | admin:comercial_politicadescuento_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/politicadescuento/<path:object_id>/delete/ | admin:comercial_politicadescuento_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/politicadescuento/<path:object_id>/history/ | admin:comercial_politicadescuento_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/politicadescuento/add/ | admin:comercial_politicadescuento_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/politicadescuentocomercial/ | admin:comercial_politicadescuentocomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/politicadescuentocomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/politicadescuentocomercial/<path:object_id>/change/ | admin:comercial_politicadescuentocomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/politicadescuentocomercial/<path:object_id>/delete/ | admin:comercial_politicadescuentocomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/politicadescuentocomercial/<path:object_id>/history/ | admin:comercial_politicadescuentocomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/politicadescuentocomercial/add/ | admin:comercial_politicadescuentocomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/politicadevolucion/ | admin:comercial_politicadevolucion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/politicadevolucion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/politicadevolucion/<path:object_id>/change/ | admin:comercial_politicadevolucion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/politicadevolucion/<path:object_id>/delete/ | admin:comercial_politicadevolucion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/politicadevolucion/<path:object_id>/history/ | admin:comercial_politicadevolucion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/politicadevolucion/add/ | admin:comercial_politicadevolucion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/politicaentrega/ | admin:comercial_politicaentrega_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/politicaentrega/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/politicaentrega/<path:object_id>/change/ | admin:comercial_politicaentrega_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/politicaentrega/<path:object_id>/delete/ | admin:comercial_politicaentrega_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/politicaentrega/<path:object_id>/history/ | admin:comercial_politicaentrega_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/politicaentrega/add/ | admin:comercial_politicaentrega_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/politicafacturacion/ | admin:comercial_politicafacturacion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/politicafacturacion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/politicafacturacion/<path:object_id>/change/ | admin:comercial_politicafacturacion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/politicafacturacion/<path:object_id>/delete/ | admin:comercial_politicafacturacion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/politicafacturacion/<path:object_id>/history/ | admin:comercial_politicafacturacion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/politicafacturacion/add/ | admin:comercial_politicafacturacion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/preparacionpedido/ | admin:comercial_preparacionpedido_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/preparacionpedido/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/preparacionpedido/<path:object_id>/change/ | admin:comercial_preparacionpedido_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/preparacionpedido/<path:object_id>/delete/ | admin:comercial_preparacionpedido_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/preparacionpedido/<path:object_id>/history/ | admin:comercial_preparacionpedido_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/preparacionpedido/add/ | admin:comercial_preparacionpedido_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/prioridadcomercial/ | admin:comercial_prioridadcomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/prioridadcomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/prioridadcomercial/<path:object_id>/change/ | admin:comercial_prioridadcomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/prioridadcomercial/<path:object_id>/delete/ | admin:comercial_prioridadcomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/prioridadcomercial/<path:object_id>/history/ | admin:comercial_prioridadcomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/prioridadcomercial/add/ | admin:comercial_prioridadcomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/productocomercial/ | admin:comercial_productocomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/productocomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/productocomercial/<path:object_id>/change/ | admin:comercial_productocomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/productocomercial/<path:object_id>/delete/ | admin:comercial_productocomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/productocomercial/<path:object_id>/history/ | admin:comercial_productocomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/productocomercial/add/ | admin:comercial_productocomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/programacionpedido/ | admin:comercial_programacionpedido_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/programacionpedido/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/programacionpedido/<path:object_id>/change/ | admin:comercial_programacionpedido_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/programacionpedido/<path:object_id>/delete/ | admin:comercial_programacionpedido_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/programacionpedido/<path:object_id>/history/ | admin:comercial_programacionpedido_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/programacionpedido/add/ | admin:comercial_programacionpedido_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/promocioncomercial/ | admin:comercial_promocioncomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/promocioncomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/promocioncomercial/<path:object_id>/change/ | admin:comercial_promocioncomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/promocioncomercial/<path:object_id>/delete/ | admin:comercial_promocioncomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/promocioncomercial/<path:object_id>/history/ | admin:comercial_promocioncomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/promocioncomercial/add/ | admin:comercial_promocioncomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/prospecto/ | admin:comercial_prospecto_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/prospecto/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/prospecto/<path:object_id>/change/ | admin:comercial_prospecto_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/prospecto/<path:object_id>/delete/ | admin:comercial_prospecto_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/prospecto/<path:object_id>/history/ | admin:comercial_prospecto_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/prospecto/add/ | admin:comercial_prospecto_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/recibocobro/ | admin:comercial_recibocobro_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/recibocobro/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/recibocobro/<path:object_id>/change/ | admin:comercial_recibocobro_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/recibocobro/<path:object_id>/delete/ | admin:comercial_recibocobro_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/recibocobro/<path:object_id>/history/ | admin:comercial_recibocobro_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/recibocobro/add/ | admin:comercial_recibocobro_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/reglaprecio/ | admin:comercial_reglaprecio_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/reglaprecio/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/reglaprecio/<path:object_id>/change/ | admin:comercial_reglaprecio_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/reglaprecio/<path:object_id>/delete/ | admin:comercial_reglaprecio_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/reglaprecio/<path:object_id>/history/ | admin:comercial_reglaprecio_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/reglaprecio/add/ | admin:comercial_reglaprecio_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/reglapromocion/ | admin:comercial_reglapromocion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/reglapromocion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/reglapromocion/<path:object_id>/change/ | admin:comercial_reglapromocion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/reglapromocion/<path:object_id>/delete/ | admin:comercial_reglapromocion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/reglapromocion/<path:object_id>/history/ | admin:comercial_reglapromocion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/reglapromocion/add/ | admin:comercial_reglapromocion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/reservacomercial/ | admin:comercial_reservacomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/reservacomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/reservacomercial/<path:object_id>/change/ | admin:comercial_reservacomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/reservacomercial/<path:object_id>/delete/ | admin:comercial_reservacomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/reservacomercial/<path:object_id>/history/ | admin:comercial_reservacomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/reservacomercial/add/ | admin:comercial_reservacomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/rutacomercial/ | admin:comercial_rutacomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/rutacomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/rutacomercial/<path:object_id>/change/ | admin:comercial_rutacomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/rutacomercial/<path:object_id>/delete/ | admin:comercial_rutacomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/rutacomercial/<path:object_id>/history/ | admin:comercial_rutacomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/rutacomercial/add/ | admin:comercial_rutacomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/secuenciadocumento/ | admin:comercial_secuenciadocumento_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/secuenciadocumento/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/secuenciadocumento/<path:object_id>/change/ | admin:comercial_secuenciadocumento_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/secuenciadocumento/<path:object_id>/delete/ | admin:comercial_secuenciadocumento_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/secuenciadocumento/<path:object_id>/history/ | admin:comercial_secuenciadocumento_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/secuenciadocumento/add/ | admin:comercial_secuenciadocumento_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/segmentocliente/ | admin:comercial_segmentocliente_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/segmentocliente/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/segmentocliente/<path:object_id>/change/ | admin:comercial_segmentocliente_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/segmentocliente/<path:object_id>/delete/ | admin:comercial_segmentocliente_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/segmentocliente/<path:object_id>/history/ | admin:comercial_segmentocliente_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/segmentocliente/add/ | admin:comercial_segmentocliente_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/tareapicking/ | admin:comercial_tareapicking_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/tareapicking/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/tareapicking/<path:object_id>/change/ | admin:comercial_tareapicking_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/tareapicking/<path:object_id>/delete/ | admin:comercial_tareapicking_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/tareapicking/<path:object_id>/history/ | admin:comercial_tareapicking_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/tareapicking/add/ | admin:comercial_tareapicking_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/tipocliente/ | admin:comercial_tipocliente_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/tipocliente/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/tipocliente/<path:object_id>/change/ | admin:comercial_tipocliente_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/tipocliente/<path:object_id>/delete/ | admin:comercial_tipocliente_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/tipocliente/<path:object_id>/history/ | admin:comercial_tipocliente_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/tipocliente/add/ | admin:comercial_tipocliente_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/tipoentrega/ | admin:comercial_tipoentrega_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/tipoentrega/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/tipoentrega/<path:object_id>/change/ | admin:comercial_tipoentrega_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/tipoentrega/<path:object_id>/delete/ | admin:comercial_tipoentrega_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/tipoentrega/<path:object_id>/history/ | admin:comercial_tipoentrega_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/tipoentrega/add/ | admin:comercial_tipoentrega_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/vendedorcomercial/ | admin:comercial_vendedorcomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/vendedorcomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/vendedorcomercial/<path:object_id>/change/ | admin:comercial_vendedorcomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/vendedorcomercial/<path:object_id>/delete/ | admin:comercial_vendedorcomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/vendedorcomercial/<path:object_id>/history/ | admin:comercial_vendedorcomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/vendedorcomercial/add/ | admin:comercial_vendedorcomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/versioncotizacionventa/ | admin:comercial_versioncotizacionventa_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/versioncotizacionventa/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/versioncotizacionventa/<path:object_id>/change/ | admin:comercial_versioncotizacionventa_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/versioncotizacionventa/<path:object_id>/delete/ | admin:comercial_versioncotizacionventa_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/versioncotizacionventa/<path:object_id>/history/ | admin:comercial_versioncotizacionventa_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/versioncotizacionventa/add/ | admin:comercial_versioncotizacionventa_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/versionpoliticacomercial/ | admin:comercial_versionpoliticacomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/versionpoliticacomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/versionpoliticacomercial/<path:object_id>/change/ | admin:comercial_versionpoliticacomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/versionpoliticacomercial/<path:object_id>/delete/ | admin:comercial_versionpoliticacomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/versionpoliticacomercial/<path:object_id>/history/ | admin:comercial_versionpoliticacomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/versionpoliticacomercial/add/ | admin:comercial_versionpoliticacomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/comercial/zonacomercial/ | admin:comercial_zonacomercial_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/comercial/zonacomercial/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/comercial/zonacomercial/<path:object_id>/change/ | admin:comercial_zonacomercial_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/comercial/zonacomercial/<path:object_id>/delete/ | admin:comercial_zonacomercial_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/comercial/zonacomercial/<path:object_id>/history/ | admin:comercial_zonacomercial_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/comercial/zonacomercial/add/ | admin:comercial_zonacomercial_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/aclaracionoferta/ | admin:compras_aclaracionoferta_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/aclaracionoferta/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/aclaracionoferta/<path:object_id>/change/ | admin:compras_aclaracionoferta_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/aclaracionoferta/<path:object_id>/delete/ | admin:compras_aclaracionoferta_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/aclaracionoferta/<path:object_id>/history/ | admin:compras_aclaracionoferta_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/aclaracionoferta/add/ | admin:compras_aclaracionoferta_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/adjudicacioncompra/ | admin:compras_adjudicacioncompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/adjudicacioncompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/adjudicacioncompra/<path:object_id>/change/ | admin:compras_adjudicacioncompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/adjudicacioncompra/<path:object_id>/delete/ | admin:compras_adjudicacioncompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/adjudicacioncompra/<path:object_id>/history/ | admin:compras_adjudicacioncompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/adjudicacioncompra/add/ | admin:compras_adjudicacioncompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/categoriaproveedor/ | admin:compras_categoriaproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/categoriaproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/categoriaproveedor/<path:object_id>/change/ | admin:compras_categoriaproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/categoriaproveedor/<path:object_id>/delete/ | admin:compras_categoriaproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/categoriaproveedor/<path:object_id>/history/ | admin:compras_categoriaproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/categoriaproveedor/add/ | admin:compras_categoriaproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/comparativocompra/ | admin:compras_comparativocompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/comparativocompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/comparativocompra/<path:object_id>/change/ | admin:compras_comparativocompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/comparativocompra/<path:object_id>/delete/ | admin:compras_comparativocompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/comparativocompra/<path:object_id>/history/ | admin:compras_comparativocompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/comparativocompra/add/ | admin:compras_comparativocompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/contactoproveedor/ | admin:compras_contactoproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/contactoproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/contactoproveedor/<path:object_id>/change/ | admin:compras_contactoproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/contactoproveedor/<path:object_id>/delete/ | admin:compras_contactoproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/contactoproveedor/<path:object_id>/history/ | admin:compras_contactoproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/contactoproveedor/add/ | admin:compras_contactoproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/criterioevaluacionrfq/ | admin:compras_criterioevaluacionrfq_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/criterioevaluacionrfq/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/criterioevaluacionrfq/<path:object_id>/change/ | admin:compras_criterioevaluacionrfq_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/criterioevaluacionrfq/<path:object_id>/delete/ | admin:compras_criterioevaluacionrfq_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/criterioevaluacionrfq/<path:object_id>/history/ | admin:compras_criterioevaluacionrfq_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/criterioevaluacionrfq/add/ | admin:compras_criterioevaluacionrfq_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/cuentabancariaproveedor/ | admin:compras_cuentabancariaproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/cuentabancariaproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/cuentabancariaproveedor/<path:object_id>/change/ | admin:compras_cuentabancariaproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/cuentabancariaproveedor/<path:object_id>/delete/ | admin:compras_cuentabancariaproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/cuentabancariaproveedor/<path:object_id>/history/ | admin:compras_cuentabancariaproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/cuentabancariaproveedor/add/ | admin:compras_cuentabancariaproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/detalleadjudicacion/ | admin:compras_detalleadjudicacion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/detalleadjudicacion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/detalleadjudicacion/<path:object_id>/change/ | admin:compras_detalleadjudicacion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/detalleadjudicacion/<path:object_id>/delete/ | admin:compras_detalleadjudicacion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/detalleadjudicacion/<path:object_id>/history/ | admin:compras_detalleadjudicacion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/detalleadjudicacion/add/ | admin:compras_detalleadjudicacion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/detalledevolucioncompra/ | admin:compras_detalledevolucioncompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/detalledevolucioncompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/detalledevolucioncompra/<path:object_id>/change/ | admin:compras_detalledevolucioncompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/detalledevolucioncompra/<path:object_id>/delete/ | admin:compras_detalledevolucioncompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/detalledevolucioncompra/<path:object_id>/history/ | admin:compras_detalledevolucioncompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/detalledevolucioncompra/add/ | admin:compras_detalledevolucioncompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/detalleordencompraenterprise/ | admin:compras_detalleordencompraenterprise_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/detalleordencompraenterprise/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/detalleordencompraenterprise/<path:object_id>/change/ | admin:compras_detalleordencompraenterprise_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/detalleordencompraenterprise/<path:object_id>/delete/ | admin:compras_detalleordencompraenterprise_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/detalleordencompraenterprise/<path:object_id>/history/ | admin:compras_detalleordencompraenterprise_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/detalleordencompraenterprise/add/ | admin:compras_detalleordencompraenterprise_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/detallerecepcioncompra/ | admin:compras_detallerecepcioncompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/detallerecepcioncompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/detallerecepcioncompra/<path:object_id>/change/ | admin:compras_detallerecepcioncompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/detallerecepcioncompra/<path:object_id>/delete/ | admin:compras_detallerecepcioncompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/detallerecepcioncompra/<path:object_id>/history/ | admin:compras_detallerecepcioncompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/detallerecepcioncompra/add/ | admin:compras_detallerecepcioncompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/detallerfq/ | admin:compras_detallerfq_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/detallerfq/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/detallerfq/<path:object_id>/change/ | admin:compras_detallerfq_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/detallerfq/<path:object_id>/delete/ | admin:compras_detallerfq_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/detallerfq/<path:object_id>/history/ | admin:compras_detallerfq_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/detallerfq/add/ | admin:compras_detallerfq_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/detallesolicitudcompra/ | admin:compras_detallesolicitudcompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/detallesolicitudcompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/detallesolicitudcompra/<path:object_id>/change/ | admin:compras_detallesolicitudcompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/detallesolicitudcompra/<path:object_id>/delete/ | admin:compras_detallesolicitudcompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/detallesolicitudcompra/<path:object_id>/history/ | admin:compras_detallesolicitudcompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/detallesolicitudcompra/add/ | admin:compras_detallesolicitudcompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/devolucioncompra/ | admin:compras_devolucioncompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/devolucioncompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/devolucioncompra/<path:object_id>/change/ | admin:compras_devolucioncompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/devolucioncompra/<path:object_id>/delete/ | admin:compras_devolucioncompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/devolucioncompra/<path:object_id>/history/ | admin:compras_devolucioncompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/devolucioncompra/add/ | admin:compras_devolucioncompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/direccionproveedor/ | admin:compras_direccionproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/direccionproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/direccionproveedor/<path:object_id>/change/ | admin:compras_direccionproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/direccionproveedor/<path:object_id>/delete/ | admin:compras_direccionproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/direccionproveedor/<path:object_id>/history/ | admin:compras_direccionproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/direccionproveedor/add/ | admin:compras_direccionproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/escenariocomparativo/ | admin:compras_escenariocomparativo_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/escenariocomparativo/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/escenariocomparativo/<path:object_id>/change/ | admin:compras_escenariocomparativo_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/escenariocomparativo/<path:object_id>/delete/ | admin:compras_escenariocomparativo_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/escenariocomparativo/<path:object_id>/history/ | admin:compras_escenariocomparativo_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/escenariocomparativo/add/ | admin:compras_escenariocomparativo_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/expedientecompra/ | admin:compras_expedientecompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/expedientecompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/expedientecompra/<path:object_id>/change/ | admin:compras_expedientecompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/expedientecompra/<path:object_id>/delete/ | admin:compras_expedientecompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/expedientecompra/<path:object_id>/history/ | admin:compras_expedientecompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/expedientecompra/add/ | admin:compras_expedientecompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/historialadjudicacion/ | admin:compras_historialadjudicacion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/historialadjudicacion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/historialadjudicacion/<path:object_id>/change/ | admin:compras_historialadjudicacion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/historialadjudicacion/<path:object_id>/delete/ | admin:compras_historialadjudicacion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/historialadjudicacion/<path:object_id>/history/ | admin:compras_historialadjudicacion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/historialadjudicacion/add/ | admin:compras_historialadjudicacion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/historialcomparativo/ | admin:compras_historialcomparativo_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/historialcomparativo/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/historialcomparativo/<path:object_id>/change/ | admin:compras_historialcomparativo_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/historialcomparativo/<path:object_id>/delete/ | admin:compras_historialcomparativo_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/historialcomparativo/<path:object_id>/history/ | admin:compras_historialcomparativo_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/historialcomparativo/add/ | admin:compras_historialcomparativo_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/historialestadoexpedientecompra/ | admin:compras_historialestadoexpedientecompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/historialestadoexpedientecompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/historialestadoexpedientecompra/<path:object_id>/change/ | admin:compras_historialestadoexpedientecompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/historialestadoexpedientecompra/<path:object_id>/delete/ | admin:compras_historialestadoexpedientecompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/historialestadoexpedientecompra/<path:object_id>/history/ | admin:compras_historialestadoexpedientecompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/historialestadoexpedientecompra/add/ | admin:compras_historialestadoexpedientecompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/historialestadoproveedor/ | admin:compras_historialestadoproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/historialestadoproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/historialestadoproveedor/<path:object_id>/change/ | admin:compras_historialestadoproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/historialestadoproveedor/<path:object_id>/delete/ | admin:compras_historialestadoproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/historialestadoproveedor/<path:object_id>/history/ | admin:compras_historialestadoproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/historialestadoproveedor/add/ | admin:compras_historialestadoproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/historialestadorfq/ | admin:compras_historialestadorfq_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/historialestadorfq/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/historialestadorfq/<path:object_id>/change/ | admin:compras_historialestadorfq_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/historialestadorfq/<path:object_id>/delete/ | admin:compras_historialestadorfq_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/historialestadorfq/<path:object_id>/history/ | admin:compras_historialestadorfq_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/historialestadorfq/add/ | admin:compras_historialestadorfq_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/historialestadosolicitudcompra/ | admin:compras_historialestadosolicitudcompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/historialestadosolicitudcompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/historialestadosolicitudcompra/<path:object_id>/change/ | admin:compras_historialestadosolicitudcompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/historialestadosolicitudcompra/<path:object_id>/delete/ | admin:compras_historialestadosolicitudcompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/historialestadosolicitudcompra/<path:object_id>/history/ | admin:compras_historialestadosolicitudcompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/historialestadosolicitudcompra/add/ | admin:compras_historialestadosolicitudcompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/historialoferta/ | admin:compras_historialoferta_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/historialoferta/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/historialoferta/<path:object_id>/change/ | admin:compras_historialoferta_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/historialoferta/<path:object_id>/delete/ | admin:compras_historialoferta_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/historialoferta/<path:object_id>/history/ | admin:compras_historialoferta_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/historialoferta/add/ | admin:compras_historialoferta_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/historialordencompra/ | admin:compras_historialordencompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/historialordencompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/historialordencompra/<path:object_id>/change/ | admin:compras_historialordencompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/historialordencompra/<path:object_id>/delete/ | admin:compras_historialordencompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/historialordencompra/<path:object_id>/history/ | admin:compras_historialordencompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/historialordencompra/add/ | admin:compras_historialordencompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/inspeccionrecepcion/ | admin:compras_inspeccionrecepcion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/inspeccionrecepcion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/inspeccionrecepcion/<path:object_id>/change/ | admin:compras_inspeccionrecepcion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/inspeccionrecepcion/<path:object_id>/delete/ | admin:compras_inspeccionrecepcion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/inspeccionrecepcion/<path:object_id>/history/ | admin:compras_inspeccionrecepcion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/inspeccionrecepcion/add/ | admin:compras_inspeccionrecepcion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/invitacionproveedorrfq/ | admin:compras_invitacionproveedorrfq_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/invitacionproveedorrfq/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/invitacionproveedorrfq/<path:object_id>/change/ | admin:compras_invitacionproveedorrfq_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/invitacionproveedorrfq/<path:object_id>/delete/ | admin:compras_invitacionproveedorrfq_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/invitacionproveedorrfq/<path:object_id>/history/ | admin:compras_invitacionproveedorrfq_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/invitacionproveedorrfq/add/ | admin:compras_invitacionproveedorrfq_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/lineacomparativo/ | admin:compras_lineacomparativo_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/lineacomparativo/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/lineacomparativo/<path:object_id>/change/ | admin:compras_lineacomparativo_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/lineacomparativo/<path:object_id>/delete/ | admin:compras_lineacomparativo_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/lineacomparativo/<path:object_id>/history/ | admin:compras_lineacomparativo_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/lineacomparativo/add/ | admin:compras_lineacomparativo_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/lineaoferta/ | admin:compras_lineaoferta_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/lineaoferta/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/lineaoferta/<path:object_id>/change/ | admin:compras_lineaoferta_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/lineaoferta/<path:object_id>/delete/ | admin:compras_lineaoferta_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/lineaoferta/<path:object_id>/history/ | admin:compras_lineaoferta_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/lineaoferta/add/ | admin:compras_lineaoferta_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/ofertaproveedor/ | admin:compras_ofertaproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/ofertaproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/ofertaproveedor/<path:object_id>/change/ | admin:compras_ofertaproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/ofertaproveedor/<path:object_id>/delete/ | admin:compras_ofertaproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/ofertaproveedor/<path:object_id>/history/ | admin:compras_ofertaproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/ofertaproveedor/add/ | admin:compras_ofertaproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/ordencompraenterprise/ | admin:compras_ordencompraenterprise_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/ordencompraenterprise/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/ordencompraenterprise/<path:object_id>/change/ | admin:compras_ordencompraenterprise_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/ordencompraenterprise/<path:object_id>/delete/ | admin:compras_ordencompraenterprise_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/ordencompraenterprise/<path:object_id>/history/ | admin:compras_ordencompraenterprise_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/ordencompraenterprise/add/ | admin:compras_ordencompraenterprise_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/procesorfq/ | admin:compras_procesorfq_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/procesorfq/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/procesorfq/<path:object_id>/change/ | admin:compras_procesorfq_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/procesorfq/<path:object_id>/delete/ | admin:compras_procesorfq_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/procesorfq/<path:object_id>/history/ | admin:compras_procesorfq_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/procesorfq/add/ | admin:compras_procesorfq_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/productoproveedor/ | admin:compras_productoproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/productoproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/productoproveedor/<path:object_id>/change/ | admin:compras_productoproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/productoproveedor/<path:object_id>/delete/ | admin:compras_productoproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/productoproveedor/<path:object_id>/history/ | admin:compras_productoproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/productoproveedor/add/ | admin:compras_productoproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/proveedor/ | admin:compras_proveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/proveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/proveedor/<path:object_id>/change/ | admin:compras_proveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/proveedor/<path:object_id>/delete/ | admin:compras_proveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/proveedor/<path:object_id>/history/ | admin:compras_proveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/proveedor/add/ | admin:compras_proveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/proveedorlegadomap/ | admin:compras_proveedorlegadomap_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/proveedorlegadomap/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/proveedorlegadomap/<path:object_id>/change/ | admin:compras_proveedorlegadomap_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/proveedorlegadomap/<path:object_id>/delete/ | admin:compras_proveedorlegadomap_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/proveedorlegadomap/<path:object_id>/history/ | admin:compras_proveedorlegadomap_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/proveedorlegadomap/add/ | admin:compras_proveedorlegadomap_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/recepcioncompra/ | admin:compras_recepcioncompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/recepcioncompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/recepcioncompra/<path:object_id>/change/ | admin:compras_recepcioncompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/recepcioncompra/<path:object_id>/delete/ | admin:compras_recepcioncompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/recepcioncompra/<path:object_id>/history/ | admin:compras_recepcioncompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/recepcioncompra/add/ | admin:compras_recepcioncompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/reglaparticipacionrfq/ | admin:compras_reglaparticipacionrfq_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/reglaparticipacionrfq/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/reglaparticipacionrfq/<path:object_id>/change/ | admin:compras_reglaparticipacionrfq_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/reglaparticipacionrfq/<path:object_id>/delete/ | admin:compras_reglaparticipacionrfq_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/reglaparticipacionrfq/<path:object_id>/history/ | admin:compras_reglaparticipacionrfq_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/reglaparticipacionrfq/add/ | admin:compras_reglaparticipacionrfq_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/requisitodocumentoproveedor/ | admin:compras_requisitodocumentoproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/requisitodocumentoproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/requisitodocumentoproveedor/<path:object_id>/change/ | admin:compras_requisitodocumentoproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/requisitodocumentoproveedor/<path:object_id>/delete/ | admin:compras_requisitodocumentoproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/requisitodocumentoproveedor/<path:object_id>/history/ | admin:compras_requisitodocumentoproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/requisitodocumentoproveedor/add/ | admin:compras_requisitodocumentoproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/revisiondocumentoproveedor/ | admin:compras_revisiondocumentoproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/revisiondocumentoproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/revisiondocumentoproveedor/<path:object_id>/change/ | admin:compras_revisiondocumentoproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/revisiondocumentoproveedor/<path:object_id>/delete/ | admin:compras_revisiondocumentoproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/revisiondocumentoproveedor/<path:object_id>/history/ | admin:compras_revisiondocumentoproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/revisiondocumentoproveedor/add/ | admin:compras_revisiondocumentoproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/solicitudcompra/ | admin:compras_solicitudcompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/solicitudcompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/solicitudcompra/<path:object_id>/change/ | admin:compras_solicitudcompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/solicitudcompra/<path:object_id>/delete/ | admin:compras_solicitudcompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/solicitudcompra/<path:object_id>/history/ | admin:compras_solicitudcompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/solicitudcompra/add/ | admin:compras_solicitudcompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/solicitudexpedientecompra/ | admin:compras_solicitudexpedientecompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/solicitudexpedientecompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/solicitudexpedientecompra/<path:object_id>/change/ | admin:compras_solicitudexpedientecompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/solicitudexpedientecompra/<path:object_id>/delete/ | admin:compras_solicitudexpedientecompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/solicitudexpedientecompra/<path:object_id>/history/ | admin:compras_solicitudexpedientecompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/solicitudexpedientecompra/add/ | admin:compras_solicitudexpedientecompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/versionoferta/ | admin:compras_versionoferta_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/versionoferta/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/versionoferta/<path:object_id>/change/ | admin:compras_versionoferta_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/versionoferta/<path:object_id>/delete/ | admin:compras_versionoferta_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/versionoferta/<path:object_id>/history/ | admin:compras_versionoferta_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/versionoferta/add/ | admin:compras_versionoferta_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/versionordencompra/ | admin:compras_versionordencompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/versionordencompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/versionordencompra/<path:object_id>/change/ | admin:compras_versionordencompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/versionordencompra/<path:object_id>/delete/ | admin:compras_versionordencompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/versionordencompra/<path:object_id>/history/ | admin:compras_versionordencompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/versionordencompra/add/ | admin:compras_versionordencompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/wizardaudittrail/ | admin:compras_wizardaudittrail_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/wizardaudittrail/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/wizardaudittrail/<path:object_id>/change/ | admin:compras_wizardaudittrail_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/wizardaudittrail/<path:object_id>/delete/ | admin:compras_wizardaudittrail_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/wizardaudittrail/<path:object_id>/history/ | admin:compras_wizardaudittrail_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/wizardaudittrail/add/ | admin:compras_wizardaudittrail_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/wizardsession/ | admin:compras_wizardsession_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/wizardsession/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/wizardsession/<path:object_id>/change/ | admin:compras_wizardsession_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/wizardsession/<path:object_id>/delete/ | admin:compras_wizardsession_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/wizardsession/<path:object_id>/history/ | admin:compras_wizardsession_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/wizardsession/add/ | admin:compras_wizardsession_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/compras/wizardstepstate/ | admin:compras_wizardstepstate_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/compras/wizardstepstate/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/compras/wizardstepstate/<path:object_id>/change/ | admin:compras_wizardstepstate_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/compras/wizardstepstate/<path:object_id>/delete/ | admin:compras_wizardstepstate_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/compras/wizardstepstate/<path:object_id>/history/ | admin:compras_wizardstepstate_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/compras/wizardstepstate/add/ | admin:compras_wizardstepstate_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/conduces/centroeducativo/ | admin:conduces_centroeducativo_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/conduces/centroeducativo/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/conduces/centroeducativo/<path:object_id>/change/ | admin:conduces_centroeducativo_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/conduces/centroeducativo/<path:object_id>/delete/ | admin:conduces_centroeducativo_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/conduces/centroeducativo/<path:object_id>/history/ | admin:conduces_centroeducativo_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/conduces/centroeducativo/add/ | admin:conduces_centroeducativo_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/conduces/comprobantefiscal/ | admin:conduces_comprobantefiscal_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/conduces/comprobantefiscal/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/conduces/comprobantefiscal/<path:object_id>/change/ | admin:conduces_comprobantefiscal_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/conduces/comprobantefiscal/<path:object_id>/delete/ | admin:conduces_comprobantefiscal_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/conduces/comprobantefiscal/<path:object_id>/history/ | admin:conduces_comprobantefiscal_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/conduces/comprobantefiscal/add/ | admin:conduces_comprobantefiscal_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/conduces/conduce/ | admin:conduces_conduce_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/conduces/conduce/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/conduces/conduce/<path:object_id>/change/ | admin:conduces_conduce_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/conduces/conduce/<path:object_id>/delete/ | admin:conduces_conduce_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/conduces/conduce/<path:object_id>/history/ | admin:conduces_conduce_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/conduces/conduce/add/ | admin:conduces_conduce_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/conduces/detallefactura/ | admin:conduces_detallefactura_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/conduces/detallefactura/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/conduces/detallefactura/<path:object_id>/change/ | admin:conduces_detallefactura_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/conduces/detallefactura/<path:object_id>/delete/ | admin:conduces_detallefactura_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/conduces/detallefactura/<path:object_id>/history/ | admin:conduces_detallefactura_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/conduces/detallefactura/add/ | admin:conduces_detallefactura_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/conduces/dianodocencia/ | admin:conduces_dianodocencia_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/conduces/dianodocencia/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/conduces/dianodocencia/<path:object_id>/change/ | admin:conduces_dianodocencia_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/conduces/dianodocencia/<path:object_id>/delete/ | admin:conduces_dianodocencia_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/conduces/dianodocencia/<path:object_id>/history/ | admin:conduces_dianodocencia_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/conduces/dianodocencia/add/ | admin:conduces_dianodocencia_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/conduces/empresa/ | admin:conduces_empresa_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/conduces/empresa/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/conduces/empresa/<path:object_id>/change/ | admin:conduces_empresa_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/conduces/empresa/<path:object_id>/delete/ | admin:conduces_empresa_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/conduces/empresa/<path:object_id>/history/ | admin:conduces_empresa_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/conduces/empresa/add/ | admin:conduces_empresa_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/conduces/factura/ | admin:conduces_factura_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/conduces/factura/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/conduces/factura/<path:object_id>/change/ | admin:conduces_factura_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/conduces/factura/<path:object_id>/delete/ | admin:conduces_factura_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/conduces/factura/<path:object_id>/history/ | admin:conduces_factura_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/conduces/factura/add/ | admin:conduces_factura_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/conduces/menudiario/ | admin:conduces_menudiario_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/conduces/menudiario/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/conduces/menudiario/<path:object_id>/change/ | admin:conduces_menudiario_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/conduces/menudiario/<path:object_id>/delete/ | admin:conduces_menudiario_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/conduces/menudiario/<path:object_id>/history/ | admin:conduces_menudiario_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/conduces/menudiario/add/ | admin:conduces_menudiario_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/conduces/productofacturacion/ | admin:conduces_productofacturacion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/conduces/productofacturacion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/conduces/productofacturacion/<path:object_id>/change/ | admin:conduces_productofacturacion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/conduces/productofacturacion/<path:object_id>/delete/ | admin:conduces_productofacturacion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/conduces/productofacturacion/<path:object_id>/history/ | admin:conduces_productofacturacion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/conduces/productofacturacion/add/ | admin:conduces_productofacturacion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/conduces/rangocomprobantegubernamental/ | admin:conduces_rangocomprobantegubernamental_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/conduces/rangocomprobantegubernamental/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/conduces/rangocomprobantegubernamental/<path:object_id>/change/ | admin:conduces_rangocomprobantegubernamental_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/conduces/rangocomprobantegubernamental/<path:object_id>/delete/ | admin:conduces_rangocomprobantegubernamental_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/conduces/rangocomprobantegubernamental/<path:object_id>/history/ | admin:conduces_rangocomprobantegubernamental_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/conduces/rangocomprobantegubernamental/add/ | admin:conduces_rangocomprobantegubernamental_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/aplicacionanticipoproveedor/ | admin:contabilidad_aplicacionanticipoproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/aplicacionanticipoproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/aplicacionanticipoproveedor/<path:object_id>/change/ | admin:contabilidad_aplicacionanticipoproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/aplicacionanticipoproveedor/<path:object_id>/delete/ | admin:contabilidad_aplicacionanticipoproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/aplicacionanticipoproveedor/<path:object_id>/history/ | admin:contabilidad_aplicacionanticipoproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/aplicacionanticipoproveedor/add/ | admin:contabilidad_aplicacionanticipoproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/aplicacionretencionproveedor/ | admin:contabilidad_aplicacionretencionproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/aplicacionretencionproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/aplicacionretencionproveedor/<path:object_id>/change/ | admin:contabilidad_aplicacionretencionproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/aplicacionretencionproveedor/<path:object_id>/delete/ | admin:contabilidad_aplicacionretencionproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/aplicacionretencionproveedor/<path:object_id>/history/ | admin:contabilidad_aplicacionretencionproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/aplicacionretencionproveedor/add/ | admin:contabilidad_aplicacionretencionproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/aportesocio/ | admin:contabilidad_aportesocio_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/aportesocio/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/aportesocio/<path:object_id>/change/ | admin:contabilidad_aportesocio_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/aportesocio/<path:object_id>/delete/ | admin:contabilidad_aportesocio_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/aportesocio/<path:object_id>/history/ | admin:contabilidad_aportesocio_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/aportesocio/add/ | admin:contabilidad_aportesocio_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/certificadoretencionproveedor/ | admin:contabilidad_certificadoretencionproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/certificadoretencionproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/certificadoretencionproveedor/<path:object_id>/change/ | admin:contabilidad_certificadoretencionproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/certificadoretencionproveedor/<path:object_id>/delete/ | admin:contabilidad_certificadoretencionproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/certificadoretencionproveedor/<path:object_id>/history/ | admin:contabilidad_certificadoretencionproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/certificadoretencionproveedor/add/ | admin:contabilidad_certificadoretencionproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/compensacionp2p/ | admin:contabilidad_compensacionp2p_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/compensacionp2p/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/compensacionp2p/<path:object_id>/change/ | admin:contabilidad_compensacionp2p_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/compensacionp2p/<path:object_id>/delete/ | admin:contabilidad_compensacionp2p_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/compensacionp2p/<path:object_id>/history/ | admin:contabilidad_compensacionp2p_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/compensacionp2p/add/ | admin:contabilidad_compensacionp2p_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/cuentaporcobrar/ | admin:contabilidad_cuentaporcobrar_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/cuentaporcobrar/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/cuentaporcobrar/<path:object_id>/change/ | admin:contabilidad_cuentaporcobrar_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/cuentaporcobrar/<path:object_id>/delete/ | admin:contabilidad_cuentaporcobrar_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/cuentaporcobrar/<path:object_id>/history/ | admin:contabilidad_cuentaporcobrar_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/cuentaporcobrar/add/ | admin:contabilidad_cuentaporcobrar_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/cuentaporpagar/ | admin:contabilidad_cuentaporpagar_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/cuentaporpagar/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/cuentaporpagar/<path:object_id>/change/ | admin:contabilidad_cuentaporpagar_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/cuentaporpagar/<path:object_id>/delete/ | admin:contabilidad_cuentaporpagar_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/cuentaporpagar/<path:object_id>/history/ | admin:contabilidad_cuentaporpagar_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/cuentaporpagar/add/ | admin:contabilidad_cuentaporpagar_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/deudasocio/ | admin:contabilidad_deudasocio_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/deudasocio/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/deudasocio/<path:object_id>/change/ | admin:contabilidad_deudasocio_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/deudasocio/<path:object_id>/delete/ | admin:contabilidad_deudasocio_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/deudasocio/<path:object_id>/history/ | admin:contabilidad_deudasocio_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/deudasocio/add/ | admin:contabilidad_deudasocio_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/factoring/ | admin:contabilidad_factoring_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/factoring/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/factoring/<path:object_id>/change/ | admin:contabilidad_factoring_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/factoring/<path:object_id>/delete/ | admin:contabilidad_factoring_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/factoring/<path:object_id>/history/ | admin:contabilidad_factoring_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/factoring/add/ | admin:contabilidad_factoring_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/factura606/ | admin:contabilidad_factura606_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/factura606/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/factura606/<path:object_id>/change/ | admin:contabilidad_factura606_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/factura606/<path:object_id>/delete/ | admin:contabilidad_factura606_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/factura606/<path:object_id>/history/ | admin:contabilidad_factura606_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/factura606/add/ | admin:contabilidad_factura606_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/gasto/ | admin:contabilidad_gasto_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/gasto/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/gasto/<path:object_id>/change/ | admin:contabilidad_gasto_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/gasto/<path:object_id>/delete/ | admin:contabilidad_gasto_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/gasto/<path:object_id>/history/ | admin:contabilidad_gasto_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/gasto/add/ | admin:contabilidad_gasto_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/historialcompensacionp2p/ | admin:contabilidad_historialcompensacionp2p_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/historialcompensacionp2p/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/historialcompensacionp2p/<path:object_id>/change/ | admin:contabilidad_historialcompensacionp2p_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/historialcompensacionp2p/<path:object_id>/delete/ | admin:contabilidad_historialcompensacionp2p_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/historialcompensacionp2p/<path:object_id>/history/ | admin:contabilidad_historialcompensacionp2p_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/historialcompensacionp2p/add/ | admin:contabilidad_historialcompensacionp2p_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/pagofactoring/ | admin:contabilidad_pagofactoring_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/pagofactoring/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/pagofactoring/<path:object_id>/change/ | admin:contabilidad_pagofactoring_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/pagofactoring/<path:object_id>/delete/ | admin:contabilidad_pagofactoring_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/pagofactoring/<path:object_id>/history/ | admin:contabilidad_pagofactoring_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/pagofactoring/add/ | admin:contabilidad_pagofactoring_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/presupuesto/ | admin:contabilidad_presupuesto_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/presupuesto/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/presupuesto/<path:object_id>/change/ | admin:contabilidad_presupuesto_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/presupuesto/<path:object_id>/delete/ | admin:contabilidad_presupuesto_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/presupuesto/<path:object_id>/history/ | admin:contabilidad_presupuesto_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/presupuesto/add/ | admin:contabilidad_presupuesto_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/proveedor/ | admin:contabilidad_proveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/proveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/proveedor/<path:object_id>/change/ | admin:contabilidad_proveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/proveedor/<path:object_id>/delete/ | admin:contabilidad_proveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/proveedor/<path:object_id>/history/ | admin:contabilidad_proveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/proveedor/add/ | admin:contabilidad_proveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/retencionproveedor/ | admin:contabilidad_retencionproveedor_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/retencionproveedor/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/retencionproveedor/<path:object_id>/change/ | admin:contabilidad_retencionproveedor_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/retencionproveedor/<path:object_id>/delete/ | admin:contabilidad_retencionproveedor_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/retencionproveedor/<path:object_id>/history/ | admin:contabilidad_retencionproveedor_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/retencionproveedor/add/ | admin:contabilidad_retencionproveedor_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/socio/ | admin:contabilidad_socio_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/socio/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/socio/<path:object_id>/change/ | admin:contabilidad_socio_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/socio/<path:object_id>/delete/ | admin:contabilidad_socio_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/socio/<path:object_id>/history/ | admin:contabilidad_socio_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/socio/add/ | admin:contabilidad_socio_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/contabilidad/tipobienesservicios/ | admin:contabilidad_tipobienesservicios_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/contabilidad/tipobienesservicios/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/contabilidad/tipobienesservicios/<path:object_id>/change/ | admin:contabilidad_tipobienesservicios_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/contabilidad/tipobienesservicios/<path:object_id>/delete/ | admin:contabilidad_tipobienesservicios_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/contabilidad/tipobienesservicios/<path:object_id>/history/ | admin:contabilidad_tipobienesservicios_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/contabilidad/tipobienesservicios/add/ | admin:contabilidad_tipobienesservicios_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/core/conciliacioninventario/ | admin:core_conciliacioninventario_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/core/conciliacioninventario/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/core/conciliacioninventario/<path:object_id>/change/ | admin:core_conciliacioninventario_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/core/conciliacioninventario/<path:object_id>/delete/ | admin:core_conciliacioninventario_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/core/conciliacioninventario/<path:object_id>/history/ | admin:core_conciliacioninventario_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/core/conciliacioninventario/add/ | admin:core_conciliacioninventario_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/core/eventodominio/ | admin:core_eventodominio_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/core/eventodominio/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/core/eventodominio/<path:object_id>/change/ | admin:core_eventodominio_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/core/eventodominio/<path:object_id>/delete/ | admin:core_eventodominio_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/core/eventodominio/<path:object_id>/history/ | admin:core_eventodominio_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/core/eventodominio/add/ | admin:core_eventodominio_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/core/registroidempotencia/ | admin:core_registroidempotencia_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/core/registroidempotencia/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/core/registroidempotencia/<path:object_id>/change/ | admin:core_registroidempotencia_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/core/registroidempotencia/<path:object_id>/delete/ | admin:core_registroidempotencia_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/core/registroidempotencia/<path:object_id>/history/ | admin:core_registroidempotencia_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/core/registroidempotencia/add/ | admin:core_registroidempotencia_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/documentos/documento/ | admin:documentos_documento_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/documentos/documento/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/documentos/documento/<path:object_id>/change/ | admin:documentos_documento_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/documentos/documento/<path:object_id>/delete/ | admin:documentos_documento_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/documentos/documento/<path:object_id>/history/ | admin:documentos_documento_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/documentos/documento/add/ | admin:documentos_documento_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/documentos/tipodocumento/ | admin:documentos_tipodocumento_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/documentos/tipodocumento/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/documentos/tipodocumento/<path:object_id>/change/ | admin:documentos_tipodocumento_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/documentos/tipodocumento/<path:object_id>/delete/ | admin:documentos_tipodocumento_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/documentos/tipodocumento/<path:object_id>/history/ | admin:documentos_tipodocumento_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/documentos/tipodocumento/add/ | admin:documentos_tipodocumento_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/categoriainventario/ | admin:inventario_categoriainventario_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/categoriainventario/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/categoriainventario/<path:object_id>/change/ | admin:inventario_categoriainventario_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/categoriainventario/<path:object_id>/delete/ | admin:inventario_categoriainventario_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/categoriainventario/<path:object_id>/history/ | admin:inventario_categoriainventario_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/categoriainventario/add/ | admin:inventario_categoriainventario_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/consumoproduccion/ | admin:inventario_consumoproduccion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/consumoproduccion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/consumoproduccion/<path:object_id>/change/ | admin:inventario_consumoproduccion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/consumoproduccion/<path:object_id>/delete/ | admin:inventario_consumoproduccion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/consumoproduccion/<path:object_id>/history/ | admin:inventario_consumoproduccion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/consumoproduccion/add/ | admin:inventario_consumoproduccion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/devolucionproduccion/ | admin:inventario_devolucionproduccion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/devolucionproduccion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/devolucionproduccion/<path:object_id>/change/ | admin:inventario_devolucionproduccion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/devolucionproduccion/<path:object_id>/delete/ | admin:inventario_devolucionproduccion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/devolucionproduccion/<path:object_id>/history/ | admin:inventario_devolucionproduccion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/devolucionproduccion/add/ | admin:inventario_devolucionproduccion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/ejecucioninventarioorden/ | admin:inventario_ejecucioninventarioorden_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/ejecucioninventarioorden/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/ejecucioninventarioorden/<path:object_id>/change/ | admin:inventario_ejecucioninventarioorden_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/ejecucioninventarioorden/<path:object_id>/delete/ | admin:inventario_ejecucioninventarioorden_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/ejecucioninventarioorden/<path:object_id>/history/ | admin:inventario_ejecucioninventarioorden_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/ejecucioninventarioorden/add/ | admin:inventario_ejecucioninventarioorden_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/historialestadoordenproduccion/ | admin:inventario_historialestadoordenproduccion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/historialestadoordenproduccion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/historialestadoordenproduccion/<path:object_id>/change/ | admin:inventario_historialestadoordenproduccion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/historialestadoordenproduccion/<path:object_id>/delete/ | admin:inventario_historialestadoordenproduccion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/historialestadoordenproduccion/<path:object_id>/history/ | admin:inventario_historialestadoordenproduccion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/historialestadoordenproduccion/add/ | admin:inventario_historialestadoordenproduccion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/loteinventario/ | admin:inventario_loteinventario_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/loteinventario/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/loteinventario/<path:object_id>/change/ | admin:inventario_loteinventario_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/loteinventario/<path:object_id>/delete/ | admin:inventario_loteinventario_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/loteinventario/<path:object_id>/history/ | admin:inventario_loteinventario_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/loteinventario/add/ | admin:inventario_loteinventario_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/loteproduccion/ | admin:inventario_loteproduccion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/loteproduccion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/loteproduccion/<path:object_id>/change/ | admin:inventario_loteproduccion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/loteproduccion/<path:object_id>/delete/ | admin:inventario_loteproduccion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/loteproduccion/<path:object_id>/history/ | admin:inventario_loteproduccion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/loteproduccion/add/ | admin:inventario_loteproduccion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/mermaproduccion/ | admin:inventario_mermaproduccion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/mermaproduccion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/mermaproduccion/<path:object_id>/change/ | admin:inventario_mermaproduccion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/mermaproduccion/<path:object_id>/delete/ | admin:inventario_mermaproduccion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/mermaproduccion/<path:object_id>/history/ | admin:inventario_mermaproduccion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/mermaproduccion/add/ | admin:inventario_mermaproduccion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/movimientoinventario/ | admin:inventario_movimientoinventario_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/movimientoinventario/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/movimientoinventario/<path:object_id>/change/ | admin:inventario_movimientoinventario_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/movimientoinventario/<path:object_id>/delete/ | admin:inventario_movimientoinventario_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/movimientoinventario/<path:object_id>/history/ | admin:inventario_movimientoinventario_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/movimientoinventario/add/ | admin:inventario_movimientoinventario_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/necesidadmateriaprima/ | admin:inventario_necesidadmateriaprima_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/necesidadmateriaprima/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/necesidadmateriaprima/<path:object_id>/change/ | admin:inventario_necesidadmateriaprima_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/necesidadmateriaprima/<path:object_id>/delete/ | admin:inventario_necesidadmateriaprima_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/necesidadmateriaprima/<path:object_id>/history/ | admin:inventario_necesidadmateriaprima_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/necesidadmateriaprima/add/ | admin:inventario_necesidadmateriaprima_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/ordencompra/ | admin:inventario_ordencompra_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/ordencompra/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/ordencompra/<path:object_id>/change/ | admin:inventario_ordencompra_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/ordencompra/<path:object_id>/delete/ | admin:inventario_ordencompra_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/ordencompra/<path:object_id>/history/ | admin:inventario_ordencompra_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/ordencompra/add/ | admin:inventario_ordencompra_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/ordenproduccion/ | admin:inventario_ordenproduccion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/ordenproduccion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/ordenproduccion/<path:object_id>/change/ | admin:inventario_ordenproduccion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/ordenproduccion/<path:object_id>/delete/ | admin:inventario_ordenproduccion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/ordenproduccion/<path:object_id>/history/ | admin:inventario_ordenproduccion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/ordenproduccion/add/ | admin:inventario_ordenproduccion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/planproduccion/ | admin:inventario_planproduccion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/planproduccion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/planproduccion/<path:object_id>/change/ | admin:inventario_planproduccion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/planproduccion/<path:object_id>/delete/ | admin:inventario_planproduccion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/planproduccion/<path:object_id>/history/ | admin:inventario_planproduccion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/planproduccion/add/ | admin:inventario_planproduccion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/prestamomateriaprima/ | admin:inventario_prestamomateriaprima_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/prestamomateriaprima/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/prestamomateriaprima/<path:object_id>/change/ | admin:inventario_prestamomateriaprima_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/prestamomateriaprima/<path:object_id>/delete/ | admin:inventario_prestamomateriaprima_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/prestamomateriaprima/<path:object_id>/history/ | admin:inventario_prestamomateriaprima_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/prestamomateriaprima/add/ | admin:inventario_prestamomateriaprima_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/produccionprogramada/ | admin:inventario_produccionprogramada_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/produccionprogramada/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/produccionprogramada/<path:object_id>/change/ | admin:inventario_produccionprogramada_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/produccionprogramada/<path:object_id>/delete/ | admin:inventario_produccionprogramada_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/produccionprogramada/<path:object_id>/history/ | admin:inventario_produccionprogramada_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/produccionprogramada/add/ | admin:inventario_produccionprogramada_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/productoinventario/ | admin:inventario_productoinventario_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/productoinventario/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/productoinventario/<path:object_id>/change/ | admin:inventario_productoinventario_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/productoinventario/<path:object_id>/delete/ | admin:inventario_productoinventario_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/productoinventario/<path:object_id>/history/ | admin:inventario_productoinventario_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/productoinventario/add/ | admin:inventario_productoinventario_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/productoproduccion/ | admin:inventario_productoproduccion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/productoproduccion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/productoproduccion/<path:object_id>/change/ | admin:inventario_productoproduccion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/productoproduccion/<path:object_id>/delete/ | admin:inventario_productoproduccion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/productoproduccion/<path:object_id>/history/ | admin:inventario_productoproduccion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/productoproduccion/add/ | admin:inventario_productoproduccion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/receta/ | admin:inventario_receta_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/receta/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/receta/<path:object_id>/change/ | admin:inventario_receta_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/receta/<path:object_id>/delete/ | admin:inventario_receta_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/receta/<path:object_id>/history/ | admin:inventario_receta_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/receta/add/ | admin:inventario_receta_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/recetaproduccion/ | admin:inventario_recetaproduccion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/recetaproduccion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/recetaproduccion/<path:object_id>/change/ | admin:inventario_recetaproduccion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/recetaproduccion/<path:object_id>/delete/ | admin:inventario_recetaproduccion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/recetaproduccion/<path:object_id>/history/ | admin:inventario_recetaproduccion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/recetaproduccion/add/ | admin:inventario_recetaproduccion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/inventario/reservainventario/ | admin:inventario_reservainventario_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/inventario/reservainventario/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/inventario/reservainventario/<path:object_id>/change/ | admin:inventario_reservainventario_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/inventario/reservainventario/<path:object_id>/delete/ | admin:inventario_reservainventario_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/inventario/reservainventario/<path:object_id>/history/ | admin:inventario_reservainventario_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/inventario/reservainventario/add/ | admin:inventario_reservainventario_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/jsi18n/ | admin:jsi18n | ADMIN | No | django.contrib.admin.sites.i18n_javascript |
| /admin/login/ | admin:login | ADMIN | No | django.contrib.admin.sites.login |
| /admin/logout/ | admin:logout | ADMIN | No | django.contrib.admin.sites.logout |
| /admin/password_change/ | admin:password_change | ADMIN | No | django.contrib.admin.sites.password_change |
| /admin/password_change/done/ | admin:password_change_done | ADMIN | No | django.contrib.admin.sites.password_change_done |
| /admin/r/<path:content_type_id>/<path:object_id>/ | admin:view_on_site | ADMIN | Sí | django.contrib.contenttypes.views.shortcut |
| /admin/workflow/asignacionaprobacion/ | admin:workflow_asignacionaprobacion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/asignacionaprobacion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/asignacionaprobacion/<path:object_id>/change/ | admin:workflow_asignacionaprobacion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/asignacionaprobacion/<path:object_id>/delete/ | admin:workflow_asignacionaprobacion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/asignacionaprobacion/<path:object_id>/history/ | admin:workflow_asignacionaprobacion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/asignacionaprobacion/add/ | admin:workflow_asignacionaprobacion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/workflow/asignadornivel/ | admin:workflow_asignadornivel_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/asignadornivel/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/asignadornivel/<path:object_id>/change/ | admin:workflow_asignadornivel_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/asignadornivel/<path:object_id>/delete/ | admin:workflow_asignadornivel_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/asignadornivel/<path:object_id>/history/ | admin:workflow_asignadornivel_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/asignadornivel/add/ | admin:workflow_asignadornivel_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/workflow/condicionreglaaprobacion/ | admin:workflow_condicionreglaaprobacion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/condicionreglaaprobacion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/condicionreglaaprobacion/<path:object_id>/change/ | admin:workflow_condicionreglaaprobacion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/condicionreglaaprobacion/<path:object_id>/delete/ | admin:workflow_condicionreglaaprobacion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/condicionreglaaprobacion/<path:object_id>/history/ | admin:workflow_condicionreglaaprobacion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/condicionreglaaprobacion/add/ | admin:workflow_condicionreglaaprobacion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/workflow/decisionaprobacion/ | admin:workflow_decisionaprobacion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/decisionaprobacion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/decisionaprobacion/<path:object_id>/change/ | admin:workflow_decisionaprobacion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/decisionaprobacion/<path:object_id>/delete/ | admin:workflow_decisionaprobacion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/decisionaprobacion/<path:object_id>/history/ | admin:workflow_decisionaprobacion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/decisionaprobacion/add/ | admin:workflow_decisionaprobacion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/workflow/instanciaworkflow/ | admin:workflow_instanciaworkflow_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/instanciaworkflow/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/instanciaworkflow/<path:object_id>/change/ | admin:workflow_instanciaworkflow_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/instanciaworkflow/<path:object_id>/delete/ | admin:workflow_instanciaworkflow_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/instanciaworkflow/<path:object_id>/history/ | admin:workflow_instanciaworkflow_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/instanciaworkflow/add/ | admin:workflow_instanciaworkflow_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/workflow/miembroworkflowempresa/ | admin:workflow_miembroworkflowempresa_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/miembroworkflowempresa/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/miembroworkflowempresa/<path:object_id>/change/ | admin:workflow_miembroworkflowempresa_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/miembroworkflowempresa/<path:object_id>/delete/ | admin:workflow_miembroworkflowempresa_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/miembroworkflowempresa/<path:object_id>/history/ | admin:workflow_miembroworkflowempresa_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/miembroworkflowempresa/add/ | admin:workflow_miembroworkflowempresa_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/workflow/nivelaprobacion/ | admin:workflow_nivelaprobacion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/nivelaprobacion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/nivelaprobacion/<path:object_id>/change/ | admin:workflow_nivelaprobacion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/nivelaprobacion/<path:object_id>/delete/ | admin:workflow_nivelaprobacion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/nivelaprobacion/<path:object_id>/history/ | admin:workflow_nivelaprobacion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/nivelaprobacion/add/ | admin:workflow_nivelaprobacion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/workflow/nivelinstanciaworkflow/ | admin:workflow_nivelinstanciaworkflow_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/nivelinstanciaworkflow/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/nivelinstanciaworkflow/<path:object_id>/change/ | admin:workflow_nivelinstanciaworkflow_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/nivelinstanciaworkflow/<path:object_id>/delete/ | admin:workflow_nivelinstanciaworkflow_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/nivelinstanciaworkflow/<path:object_id>/history/ | admin:workflow_nivelinstanciaworkflow_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/nivelinstanciaworkflow/add/ | admin:workflow_nivelinstanciaworkflow_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/workflow/reglaaprobacion/ | admin:workflow_reglaaprobacion_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/reglaaprobacion/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/reglaaprobacion/<path:object_id>/change/ | admin:workflow_reglaaprobacion_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/reglaaprobacion/<path:object_id>/delete/ | admin:workflow_reglaaprobacion_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/reglaaprobacion/<path:object_id>/history/ | admin:workflow_reglaaprobacion_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/reglaaprobacion/add/ | admin:workflow_reglaaprobacion_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/workflow/rondaworkflow/ | admin:workflow_rondaworkflow_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/rondaworkflow/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/rondaworkflow/<path:object_id>/change/ | admin:workflow_rondaworkflow_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/rondaworkflow/<path:object_id>/delete/ | admin:workflow_rondaworkflow_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/rondaworkflow/<path:object_id>/history/ | admin:workflow_rondaworkflow_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/rondaworkflow/add/ | admin:workflow_rondaworkflow_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/workflow/solicitudcorreccionworkflow/ | admin:workflow_solicitudcorreccionworkflow_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/solicitudcorreccionworkflow/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/solicitudcorreccionworkflow/<path:object_id>/change/ | admin:workflow_solicitudcorreccionworkflow_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/solicitudcorreccionworkflow/<path:object_id>/delete/ | admin:workflow_solicitudcorreccionworkflow_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/solicitudcorreccionworkflow/<path:object_id>/history/ | admin:workflow_solicitudcorreccionworkflow_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/solicitudcorreccionworkflow/add/ | admin:workflow_solicitudcorreccionworkflow_add | ADMIN | No | django.contrib.admin.options.add_view |
| /admin/workflow/suplenciaaprobador/ | admin:workflow_suplenciaaprobador_changelist | ADMIN | No | django.contrib.admin.options.changelist_view |
| /admin/workflow/suplenciaaprobador/<path:object_id>/ | admin | ADMIN | Sí | django.views.generic.base.view |
| /admin/workflow/suplenciaaprobador/<path:object_id>/change/ | admin:workflow_suplenciaaprobador_change | ADMIN | Sí | django.contrib.admin.options.change_view |
| /admin/workflow/suplenciaaprobador/<path:object_id>/delete/ | admin:workflow_suplenciaaprobador_delete | ADMIN | Sí | django.contrib.admin.options.delete_view |
| /admin/workflow/suplenciaaprobador/<path:object_id>/history/ | admin:workflow_suplenciaaprobador_history | ADMIN | Sí | django.contrib.admin.options.history_view |
| /admin/workflow/suplenciaaprobador/add/ | admin:workflow_suplenciaaprobador_add | ADMIN | No | django.contrib.admin.options.add_view |
| /buscar-conduces/ | buscar_conduces | GET SEGURA | No | conduces.views.buscar_conduces |
| /calendario-escolar/ | calendario_escolar | GET SEGURA | No | conduces.views.calendario_escolar |
| /calendario-escolar/agregar/ | agregar_dia_no_docencia | GET SEGURA | No | conduces.views.agregar_dia_no_docencia |
| /calendario-escolar/editar/<int:dia_id>/ | editar_dia_no_docencia | POST/MUTABLE | Sí | conduces.views.editar_dia_no_docencia |
| /carga-centros/ | carga_centros | GET SEGURA | No | conduces.views.pantalla_carga_centros |
| /carga-menu/ | carga_menu | GET SEGURA | No | conduces.views.pantalla_carga_menu |
| /cargar-centros/ | cargar_centros_excel | EXPORTACIÓN | No | conduces.views.cargar_centros_excel |
| /cargar-menu/ | cargar_menu_excel | EXPORTACIÓN | No | conduces.views.cargar_menu_excel |
| /cartas/ | cartas_administrativas | GET SEGURA | No | conduces.views.cartas_administrativas |
| /cartas/generar-pdf/ | generar_carta_pdf | DESCARGA | No | conduces.views.generar_carta_pdf |
| /catalogos/ | catalogos:centro | GET SEGURA | No | catalogos.views.centro |
| /catalogos/<slug:clave>/ | catalogos:lista | GET SEGURA | Sí | catalogos.views.lista |
| /catalogos/<slug:clave>/<int:pk>/actividad/ | catalogos:actividad | GET SEGURA | Sí | catalogos.views.actividad |
| /catalogos/<slug:clave>/<int:pk>/editar/ | catalogos:editar | POST/MUTABLE | Sí | catalogos.views.editar |
| /catalogos/<slug:clave>/nuevo/ | catalogos:crear | POST/MUTABLE | Sí | catalogos.views.editar |
| /centros/ | lista_centros | GET SEGURA | No | conduces.views.pantalla_carga_centros |
| /centros/crear/ | crear_centro | POST/MUTABLE | No | conduces.views.crear_centro |
| /centros/editar/<int:centro_id>/ | editar_centro | POST/MUTABLE | Sí | conduces.views.editar_centro |
| /centros/eliminar/<int:centro_id>/ | eliminar_centro | POST/MUTABLE | Sí | conduces.views.eliminar_centro |
| /centros/mapa/ | mapa_centros | GET SEGURA | No | conduces.views.mapa_centros |
| /centros/mapa/actualizar-ubicacion/ | actualizar_ubicacion_centro | POST/MUTABLE | No | conduces.views.actualizar_ubicacion_centro |
| /comercial/ | comercial:dashboard | GET SEGURA | No | comercial.views.dashboard |
| /comercial/clientes/ | comercial:clientes_lista | GET SEGURA | No | comercial.views.clientes_lista |
| /comercial/clientes/<int:cliente_pk>/contactos/nuevo/ | comercial:contacto_crear | POST/MUTABLE | Sí | comercial.views.contacto_crear |
| /comercial/clientes/<int:cliente_pk>/direcciones/nueva/ | comercial:direccion_crear | POST/MUTABLE | Sí | comercial.views.direccion_crear |
| /comercial/clientes/<int:pk>/ | comercial:cliente_detalle | GET SEGURA | Sí | comercial.views.cliente_detalle |
| /comercial/clientes/<int:pk>/360/ | comercial:cliente_360 | GET SEGURA | Sí | comercial.o2c_views.cliente_360 |
| /comercial/clientes/<int:pk>/360/<str:accion>/ | comercial:cliente_360_accion | POST/MUTABLE | Sí | comercial.o2c_views.cliente_accion |
| /comercial/clientes/<int:pk>/editar/ | comercial:cliente_editar | POST/MUTABLE | Sí | comercial.views.cliente_editar |
| /comercial/clientes/<int:pk>/estado/ | comercial:cliente_cambiar_estado | POST/MUTABLE | Sí | comercial.views.cliente_cambiar_estado |
| /comercial/clientes/nuevo/ | comercial:cliente_crear | POST/MUTABLE | No | comercial.views.cliente_crear |
| /comercial/configuracion/ | comercial:configuracion_dashboard | GET SEGURA | No | comercial.configuracion_views.dashboard |
| /comercial/configuracion/catalogos/<str:tipo>/ | comercial:catalogo_lista | GET SEGURA | Sí | comercial.configuracion_views.catalogo_lista |
| /comercial/configuracion/catalogos/<str:tipo>/<int:pk>/ | comercial:catalogo_detalle | GET SEGURA | Sí | comercial.configuracion_views.catalogo_detalle |
| /comercial/configuracion/catalogos/<str:tipo>/<int:pk>/editar/ | comercial:catalogo_editar | POST/MUTABLE | Sí | comercial.configuracion_views.catalogo_editar |
| /comercial/configuracion/catalogos/<str:tipo>/<int:pk>/estado/ | comercial:catalogo_estado | POST/MUTABLE | Sí | comercial.configuracion_views.catalogo_estado |
| /comercial/configuracion/catalogos/<str:tipo>/nuevo/ | comercial:catalogo_crear | POST/MUTABLE | Sí | comercial.configuracion_views.catalogo_editar |
| /comercial/configuracion/editar/ | comercial:configuracion_editar | POST/MUTABLE | No | comercial.configuracion_views.configuracion_editar |
| /comercial/configuracion/exportar/<str:formato>/ | comercial:configuracion_exportar | EXPORTACIÓN | Sí | comercial.configuracion_views.exportar |
| /comercial/configuracion/politicas/<str:tipo>/ | comercial:politica_lista | GET SEGURA | Sí | comercial.configuracion_views.politica_lista |
| /comercial/configuracion/politicas/<str:tipo>/<int:pk>/ | comercial:politica_detalle | GET SEGURA | Sí | comercial.configuracion_views.politica_detalle |
| /comercial/configuracion/politicas/<str:tipo>/<int:pk>/<str:accion>/ | comercial:politica_accion | POST/MUTABLE | Sí | comercial.configuracion_views.politica_accion |
| /comercial/configuracion/politicas/<str:tipo>/<int:pk>/editar/ | comercial:politica_editar | POST/MUTABLE | Sí | comercial.configuracion_views.politica_editar |
| /comercial/configuracion/politicas/<str:tipo>/nueva/ | comercial:politica_crear | POST/MUTABLE | Sí | comercial.configuracion_views.politica_editar |
| /comercial/configuracion/reportes/ | comercial:configuracion_reportes | GET SEGURA | No | comercial.configuracion_views.reportes |
| /comercial/configuracion/secuencias/ | comercial:secuencias | GET SEGURA | No | comercial.configuracion_views.secuencias |
| /comercial/configuracion/validar/ | comercial:readiness_ejecutar | POST/MUTABLE | No | comercial.configuracion_views.readiness_ejecutar |
| /comercial/contactos/<int:pk>/editar/ | comercial:contacto_editar | POST/MUTABLE | Sí | comercial.views.contacto_editar |
| /comercial/cotizaciones/ | comercial:cotizaciones_lista | GET SEGURA | No | comercial.o2c_views.cotizaciones_lista |
| /comercial/cotizaciones/<int:pk>/ | comercial:cotizacion_detalle | GET SEGURA | Sí | comercial.o2c_views.cotizacion_detalle |
| /comercial/cotizaciones/<int:pk>/<str:accion>/ | comercial:cotizacion_accion | POST/MUTABLE | Sí | comercial.o2c_views.cotizacion_accion |
| /comercial/cotizaciones/<int:pk>/editar/ | comercial:cotizacion_editar | POST/MUTABLE | Sí | comercial.o2c_views.cotizacion_form |
| /comercial/cotizaciones/<int:pk>/pdf/ | comercial:cotizacion_pdf | DESCARGA | Sí | comercial.o2c_views.cotizacion_pdf |
| /comercial/cotizaciones/nueva/ | comercial:cotizacion_crear | POST/MUTABLE | No | comercial.o2c_views.cotizacion_form |
| /comercial/crm/ | comercial:crm_dashboard | GET SEGURA | No | comercial.crm_views.dashboard |
| /comercial/crm/actividades/ | comercial:actividades_lista | GET SEGURA | No | comercial.crm_views.actividades_lista |
| /comercial/crm/actividades/<int:pk>/ | comercial:actividad_detalle | GET SEGURA | Sí | comercial.crm_views.actividad_detalle |
| /comercial/crm/actividades/<int:pk>/<str:accion>/ | comercial:actividad_accion | POST/MUTABLE | Sí | comercial.crm_views.actividad_accion |
| /comercial/crm/actividades/<int:pk>/editar/ | comercial:actividad_editar | POST/MUTABLE | Sí | comercial.crm_views.actividad_form |
| /comercial/crm/actividades/nueva/ | comercial:actividad_crear | POST/MUTABLE | No | comercial.crm_views.actividad_form |
| /comercial/crm/agenda/ | comercial:agenda | GET SEGURA | No | comercial.crm_views.agenda_view |
| /comercial/crm/agenda/<str:vista>/ | comercial:agenda_vista | GET SEGURA | Sí | comercial.crm_views.agenda_view |
| /comercial/crm/exportar/<str:tipo>/<str:formato>/ | comercial:crm_exportar | EXPORTACIÓN | Sí | comercial.crm_views.exportar |
| /comercial/crm/masivo/<str:tipo>/<str:accion>/ | comercial:crm_accion_masiva | POST/MUTABLE | Sí | comercial.crm_views.accion_masiva |
| /comercial/crm/oportunidades/ | comercial:oportunidades_lista | GET SEGURA | No | comercial.crm_views.oportunidades_lista |
| /comercial/crm/oportunidades/<int:pk>/ | comercial:oportunidad_detalle | GET SEGURA | Sí | comercial.crm_views.oportunidad_detalle |
| /comercial/crm/oportunidades/<int:pk>/<str:accion>/ | comercial:oportunidad_accion | POST/MUTABLE | Sí | comercial.crm_views.oportunidad_accion |
| /comercial/crm/oportunidades/<int:pk>/editar/ | comercial:oportunidad_editar | POST/MUTABLE | Sí | comercial.crm_views.oportunidad_form |
| /comercial/crm/oportunidades/nueva/ | comercial:oportunidad_crear | POST/MUTABLE | No | comercial.crm_views.oportunidad_form |
| /comercial/crm/pipeline/ | comercial:pipeline | GET SEGURA | No | comercial.crm_views.pipeline_view |
| /comercial/crm/prospectos/ | comercial:prospectos_lista | GET SEGURA | No | comercial.crm_views.prospectos_lista |
| /comercial/crm/prospectos/<int:pk>/ | comercial:prospecto_detalle | GET SEGURA | Sí | comercial.crm_views.prospecto_detalle |
| /comercial/crm/prospectos/<int:pk>/<str:accion>/ | comercial:prospecto_accion | POST/MUTABLE | Sí | comercial.crm_views.prospecto_accion |
| /comercial/crm/prospectos/<int:pk>/editar/ | comercial:prospecto_editar | POST/MUTABLE | Sí | comercial.crm_views.prospecto_form |
| /comercial/crm/prospectos/nuevo/ | comercial:prospecto_crear | POST/MUTABLE | No | comercial.crm_views.prospecto_form |
| /comercial/crm/reportes/ | comercial:crm_reportes | GET SEGURA | No | comercial.crm_views.reportes |
| /comercial/direcciones/<int:pk>/editar/ | comercial:direccion_editar | POST/MUTABLE | Sí | comercial.views.direccion_editar |
| /comercial/o2c/ | comercial:o2c_dashboard | GET SEGURA | No | comercial.o2c_views.dashboard |
| /comercial/o2c/ | comercial:o2c_full_dashboard | GET SEGURA | No | comercial.o2c_full_views.dashboard |
| /comercial/o2c/<str:tipo>/ | comercial:o2c_full_lista | GET SEGURA | Sí | comercial.o2c_full_views.listado |
| /comercial/o2c/conduce/<int:pk>/entregar/ | comercial:o2c_conduce_entregar | GET SEGURA | Sí | comercial.o2c_full_views.conduce_entregar |
| /comercial/o2c/cxc/<int:pk>/cobrar/ | comercial:o2c_cobrar | GET SEGURA | Sí | comercial.o2c_full_views.cobrar |
| /comercial/o2c/despacho/<int:pk>/conduce/ | comercial:o2c_despacho_conduce | GET SEGURA | Sí | comercial.o2c_full_views.despacho_conduce |
| /comercial/o2c/entrega/<int:pk>/facturar/ | comercial:o2c_entrega_facturar | POST/MUTABLE | Sí | comercial.o2c_full_views.entrega_facturar |
| /comercial/o2c/exportar/<str:tipo>/<str:formato>/ | comercial:o2c_exportar | EXPORTACIÓN | Sí | comercial.o2c_views.exportar |
| /comercial/o2c/exportar/<str:tipo>/<str:formato>/ | comercial:o2c_full_exportar | EXPORTACIÓN | Sí | comercial.o2c_full_views.exportar |
| /comercial/o2c/finanzas/cobros/<int:pk>/aplicar/ | comercial:fin_cobro_aplicar | GET SEGURA | Sí | comercial.financial_views.cobro_aplicar |
| /comercial/o2c/finanzas/cobros/<int:pk>/integrar/ | comercial:fin_cobro_integrar | POST/MUTABLE | Sí | comercial.financial_views.cobro_integrar |
| /comercial/o2c/finanzas/cobros/<int:pk>/revertir/ | comercial:fin_cobro_revertir | POST/MUTABLE | Sí | comercial.financial_views.cobro_revertir |
| /comercial/o2c/finanzas/cobros/registrar/ | comercial:fin_cobro_registrar | POST/MUTABLE | No | comercial.financial_views.cobro_registrar |
| /comercial/o2c/finanzas/conciliaciones/<int:pk>/aplicar/ | comercial:fin_conciliacion_aplicar | GET SEGURA | Sí | comercial.financial_views.conciliacion_aplicar |
| /comercial/o2c/finanzas/conciliaciones/lineas/<int:pk>/revertir/ | comercial:fin_conciliacion_revertir | POST/MUTABLE | Sí | comercial.financial_views.conciliacion_revertir |
| /comercial/o2c/finanzas/exportar/<str:tipo>/<str:formato>/ | comercial:fin_exportar | EXPORTACIÓN | Sí | comercial.financial_views.exportacion_financiera |
| /comercial/o2c/finanzas/factoring/<int:pk>/aprobar/ | comercial:fin_factoring_aprobar | POST/MUTABLE | Sí | comercial.financial_views.factoring_aprobar |
| /comercial/o2c/finanzas/factoring/<int:pk>/desembolsar/ | comercial:fin_factoring_desembolsar | POST/MUTABLE | Sí | comercial.financial_views.factoring_desembolsar |
| /comercial/o2c/finanzas/factoring/solicitar/ | comercial:fin_factoring_solicitar | POST/MUTABLE | No | comercial.financial_views.factoring_solicitar |
| /comercial/o2c/finanzas/facturas/<int:pk>/anular/ | comercial:fin_factura_anular | POST/MUTABLE | Sí | comercial.financial_views.factura_anular |
| /comercial/o2c/finanzas/facturas/<int:pk>/contabilizar/ | comercial:fin_factura_contabilizar | GET SEGURA | Sí | comercial.financial_views.factura_contabilizar |
| /comercial/o2c/finanzas/facturas/<int:pk>/emitir/ | comercial:fin_factura_emitir | POST/MUTABLE | Sí | comercial.financial_views.factura_emitir |
| /comercial/o2c/finanzas/facturas/<int:pk>/nota-credito/ | comercial:fin_nota_credito | GET SEGURA | Sí | comercial.financial_views.nota_credito |
| /comercial/o2c/finanzas/facturas/<int:pk>/nota-debito/ | comercial:fin_nota_debito | GET SEGURA | Sí | comercial.financial_views.nota_debito |
| /comercial/o2c/finanzas/facturas/<int:pk>/reintentar/ | comercial:fin_reintentar | POST/MUTABLE | Sí | comercial.financial_views.reintentar_integracion |
| /comercial/o2c/packing/<int:pk>/despachar/ | comercial:o2c_packing_despachar | GET SEGURA | Sí | comercial.o2c_full_views.packing_despachar |
| /comercial/o2c/pedido/<int:pk>/reservar/ | comercial:o2c_pedido_reservar | GET SEGURA | Sí | comercial.o2c_full_views.pedido_reservar |
| /comercial/o2c/picking/<int:pk>/completar/ | comercial:o2c_picking_completar | POST/MUTABLE | Sí | comercial.o2c_full_views.picking_completar |
| /comercial/o2c/preparacion/<int:pk>/validar/ | comercial:o2c_preparacion_validar | POST/MUTABLE | Sí | comercial.o2c_full_views.preparacion_validar |
| /comercial/o2c/reportes/ | comercial:o2c_reportes | GET SEGURA | No | comercial.o2c_views.reportes |
| /comercial/o2c/reserva/<int:pk>/preparar/ | comercial:o2c_reserva_preparar | GET SEGURA | Sí | comercial.o2c_full_views.reserva_preparar |
| /comercial/pedidos/ | comercial:pedidos_lista | GET SEGURA | No | comercial.pedidos_views.pedidos_lista |
| /comercial/pedidos/<int:pk>/ | comercial:pedido_detalle | GET SEGURA | Sí | comercial.pedidos_views.pedido_detalle |
| /comercial/pedidos/<int:pk>/aprobar/ | comercial:pedido_aprobar | POST/MUTABLE | Sí | comercial.pedidos_views.pedido_aprobar |
| /comercial/pedidos/<int:pk>/cancelar/ | comercial:pedido_cancelar | POST/MUTABLE | Sí | comercial.pedidos_views.pedido_cancelar |
| /comercial/pedidos/<int:pk>/duplicar/ | comercial:pedido_duplicar | POST/MUTABLE | Sí | comercial.pedidos_views.pedido_duplicar |
| /comercial/pedidos/<int:pk>/editar/ | comercial:pedido_editar | POST/MUTABLE | Sí | comercial.pedidos_views.pedido_editar |
| /comercial/pedidos/<int:pk>/enviar/ | comercial:pedido_enviar_aprobacion | POST/MUTABLE | Sí | comercial.pedidos_views.pedido_enviar_aprobacion |
| /comercial/pedidos/<int:pk>/reabrir/ | comercial:pedido_reabrir | GET SEGURA | Sí | comercial.pedidos_views.pedido_reabrir |
| /comercial/pedidos/<int:pk>/rechazar/ | comercial:pedido_rechazar | POST/MUTABLE | Sí | comercial.pedidos_views.pedido_rechazar |
| /comercial/pedidos/dashboard/ | comercial:pedidos_dashboard | GET SEGURA | No | comercial.pedidos_views.pedidos_dashboard |
| /comercial/pedidos/nuevo/ | comercial:pedido_crear | POST/MUTABLE | No | comercial.pedidos_views.pedido_crear |
| /comercial/precios/listas/ | comercial:listas_precio | GET SEGURA | No | comercial.o2c_views.listas |
| /comercial/precios/listas/<int:pk>/ | comercial:lista_detalle | GET SEGURA | Sí | comercial.o2c_views.lista_detalle |
| /comercial/precios/listas/<int:pk>/activar/ | comercial:lista_activar | POST/MUTABLE | Sí | comercial.o2c_views.lista_activar |
| /comercial/precios/listas/<int:pk>/editar/ | comercial:lista_editar | POST/MUTABLE | Sí | comercial.o2c_views.lista_form |
| /comercial/precios/listas/nueva/ | comercial:lista_crear | POST/MUTABLE | No | comercial.o2c_views.lista_form |
| /comercial/precios/simulador/ | comercial:simulador_precio | GET SEGURA | No | comercial.o2c_views.simulador |
| /comercial/productos-comerciales/ | comercial:productos_comerciales | GET SEGURA | No | comercial.o2c_views.productos_lista |
| /comercial/productos-comerciales/<int:pk>/ | comercial:producto_detalle | GET SEGURA | Sí | comercial.o2c_views.producto_detalle |
| /comercial/productos-comerciales/<int:pk>/editar/ | comercial:producto_editar | POST/MUTABLE | Sí | comercial.o2c_views.producto_form |
| /comercial/productos-comerciales/nuevo/ | comercial:producto_comercial_crear | POST/MUTABLE | No | comercial.o2c_views.producto_form |
| /comercial/programacion-comercial/ | comercial:programacion_comercial | GET SEGURA | No | comercial.o2c_views.programacion |
| /comercial/programacion-comercial/<str:vista>/ | comercial:programacion_comercial_vista | GET SEGURA | Sí | comercial.o2c_views.programacion |
| /comercial/programacion/diaria/ | comercial:programacion_diaria | GET SEGURA | No | comercial.pedidos_views.programacion_diaria |
| /comercial/programacion/semanal/ | comercial:programacion_semanal | GET SEGURA | No | comercial.pedidos_views.programacion_semanal |
| /compras/ | compras:dashboard | GET SEGURA | No | compras.views.dashboard |
| /compras/cuentas/<int:pk>/<str:accion>/ | compras:revisar_cuenta | POST/MUTABLE | Sí | compras.views.revisar_cuenta |
| /compras/cuentas/<int:pk>/ver/ | compras:ver_cuenta | GET SEGURA | Sí | compras.views.ver_cuenta |
| /compras/expedientes/ | compras:expedientes_lista | GET SEGURA | No | compras.views.expedientes_lista |
| /compras/expedientes/<int:expediente_id>/rfq/nueva/ | compras:rfq_crear | POST/MUTABLE | Sí | compras.views.rfq_crear_view |
| /compras/expedientes/<int:pk>/ | compras:expediente_detalle | GET SEGURA | Sí | compras.views.expediente_detalle |
| /compras/expedientes/<int:pk>/<str:accion>/ | compras:expediente_accion | POST/MUTABLE | Sí | compras.views.expediente_accion |
| /compras/expedientes/<int:pk>/editar/ | compras:expediente_editar | POST/MUTABLE | Sí | compras.views.expediente_editar_view |
| /compras/invitaciones/<int:pk>/<str:accion>/ | compras:invitacion_accion | POST/MUTABLE | Sí | compras.views.invitacion_accion |
| /compras/invitaciones/<int:pk>/contacto/ | compras:invitacion_contacto | GET SEGURA | Sí | compras.views.invitacion_contacto |
| /compras/p2p/<str:recurso>/ | compras:p2p_recurso_lista | GET SEGURA | Sí | compras.p2p_views.lista |
| /compras/p2p/<str:recurso>/<int:pk>/ | compras:p2p_recurso_detalle | GET SEGURA | Sí | compras.p2p_views.detalle |
| /compras/p2p/accion/<str:recurso>/<int:pk>/<str:accion>/ | compras:p2p_accion | POST/MUTABLE | Sí | compras.p2p_operational_views.accion |
| /compras/p2p/cierre/<str:recurso>/ | compras:p2p_finance_list | GET SEGURA | Sí | compras.p2p_finance_views.lista |
| /compras/p2p/cierre/<str:recurso>/<int:pk>/ | compras:p2p_finance_detail | GET SEGURA | Sí | compras.p2p_finance_views.detalle |
| /compras/p2p/cierre/anticipos/<int:pk>/<str:accion>/ | compras:p2p_finance_anticipo_accion | POST/MUTABLE | Sí | compras.p2p_finance_views.anticipo_accion |
| /compras/p2p/cierre/anticipos/crear/ | compras:p2p_finance_anticipo_crear | POST/MUTABLE | No | compras.p2p_finance_views.anticipo_crear |
| /compras/p2p/cierre/certificados/<int:pk>/pdf/ | compras:p2p_finance_certificado | DESCARGA | Sí | compras.p2p_finance_views.certificado |
| /compras/p2p/cierre/documentos/<str:recurso>/<int:pk>/pdf/ | compras:p2p_finance_pdf | DESCARGA | Sí | compras.p2p_finance_views.pdf |
| /compras/p2p/cierre/extractos/importar/ | compras:p2p_finance_extracto_importar | POST/MUTABLE | No | compras.p2p_finance_views.extracto_importar |
| /compras/p2p/cierre/matching/<int:pk>/<str:accion>/ | compras:p2p_finance_matching_accion | POST/MUTABLE | Sí | compras.p2p_finance_views.matching_accion |
| /compras/p2p/cierre/notas/<str:tipo>/<int:pk>/<str:accion>/ | compras:p2p_finance_nota_accion | POST/MUTABLE | Sí | compras.p2p_finance_views.nota_accion |
| /compras/p2p/cierre/notas/crear/ | compras:p2p_finance_nota_crear | POST/MUTABLE | No | compras.p2p_finance_views.nota_crear |
| /compras/p2p/cierre/retenciones/<int:pk>/<str:accion>/ | compras:p2p_finance_retencion_accion | POST/MUTABLE | Sí | compras.p2p_finance_views.retencion_accion |
| /compras/p2p/cierre/retenciones/crear/ | compras:p2p_finance_retencion_crear | POST/MUTABLE | No | compras.p2p_finance_views.retencion_crear |
| /compras/p2p/dashboard/ | compras:p2p_dashboard | GET SEGURA | No | compras.p2p_views.dashboard |
| /compras/p2p/exportacion/ | compras:p2p_exportacion | EXPORTACIÓN | No | compras.p2p_operational_views.exportar |
| /compras/p2p/exportar/ | compras:p2p_exportar | EXPORTACIÓN | No | compras.views.p2p_exportar |
| /compras/p2p/finanzas/<str:recurso>/ | compras:p2p_settlements | GET SEGURA | Sí | compras.settlements_views.lista |
| /compras/p2p/finanzas/anticipos/<int:pk>/<str:accion>/ | compras:p2p_anticipo_accion | POST/MUTABLE | Sí | compras.settlements_views.accion_anticipo |
| /compras/p2p/finanzas/anticipos/crear/ | compras:p2p_anticipo_crear | POST/MUTABLE | No | compras.settlements_views.crear_anticipo_view |
| /compras/p2p/finanzas/certificados/<int:pk>/pdf/ | compras:p2p_certificado_pdf | DESCARGA | Sí | compras.settlements_views.certificado_pdf |
| /compras/p2p/finanzas/compensaciones/<int:pk>/<str:accion>/ | compras:p2p_compensacion_accion | POST/MUTABLE | Sí | compras.settlements_views.accion_compensacion |
| /compras/p2p/finanzas/compensaciones/crear/ | compras:p2p_compensacion_crear | POST/MUTABLE | No | compras.settlements_views.crear_compensacion |
| /compras/p2p/finanzas/retenciones/<int:pk>/<str:accion>/ | compras:p2p_retencion_accion | POST/MUTABLE | Sí | compras.settlements_views.accion_retencion |
| /compras/p2p/finanzas/retenciones/crear/ | compras:p2p_retencion_crear | POST/MUTABLE | No | compras.settlements_views.crear_retencion |
| /compras/p2p/ofertas/<int:pk>/linea/ | compras:p2p_linea_oferta | GET SEGURA | Sí | compras.p2p_operational_views.linea_oferta |
| /compras/p2p/operar/<str:tipo>/ | compras:p2p_wizard | GET SEGURA | Sí | compras.p2p_operational_views.wizard |
| /compras/p2p/wizard-enterprise/<uuid:sesion_id>/ | compras:p2p_wizard_enterprise | GET SEGURA | Sí | compras.p2p_operational_views.wizard_enterprise |
| /compras/p2p/wizard-enterprise/iniciar/<str:tipo>/ | compras:p2p_wizard_enterprise_iniciar | POST/MUTABLE | Sí | compras.p2p_operational_views.wizard_enterprise_iniciar |
| /compras/proveedores/ | compras:lista | GET SEGURA | No | compras.views.lista |
| /compras/proveedores/<int:pk>/ | compras:detalle | GET SEGURA | Sí | compras.views.detalle |
| /compras/proveedores/<int:pk>/agregar/<str:tipo>/ | compras:agregar_relacion | GET SEGURA | Sí | compras.views.agregar_relacion |
| /compras/proveedores/<int:pk>/editar/ | compras:editar | POST/MUTABLE | Sí | compras.views.editar |
| /compras/proveedores/<int:pk>/estado/<str:accion>/ | compras:estado | POST/MUTABLE | Sí | compras.views.estado |
| /compras/proveedores/exportar/ | compras:exportar | EXPORTACIÓN | No | compras.views.exportar |
| /compras/proveedores/nuevo/ | compras:crear | POST/MUTABLE | No | compras.views.editar |
| /compras/rfq/ | compras:rfq_lista | GET SEGURA | No | compras.views.rfq_lista |
| /compras/rfq/<int:pk>/ | compras:rfq_detalle | GET SEGURA | Sí | compras.views.rfq_detalle |
| /compras/rfq/<int:pk>/accion/<str:accion>/ | compras:rfq_accion | POST/MUTABLE | Sí | compras.views.rfq_accion |
| /compras/rfq/<int:pk>/agregar/<str:tipo>/ | compras:rfq_agregar | GET SEGURA | Sí | compras.views.rfq_agregar |
| /compras/rfq/<int:pk>/editar/ | compras:rfq_editar | POST/MUTABLE | Sí | compras.views.rfq_editar_view |
| /compras/rfq/<int:pk>/extender/ | compras:rfq_extender | GET SEGURA | Sí | compras.views.rfq_extender_view |
| /compras/rfq/lineas/<int:pk>/editar/ | compras:rfq_linea_editar | POST/MUTABLE | Sí | compras.views.rfq_linea_editar |
| /compras/solicitudes/ | compras:solicitudes_lista | GET SEGURA | No | compras.views.solicitudes_lista |
| /compras/solicitudes/<int:pk>/ | compras:solicitud_detalle | GET SEGURA | Sí | compras.views.solicitud_detalle |
| /compras/solicitudes/<int:pk>/<str:accion>/ | compras:solicitud_accion | POST/MUTABLE | Sí | compras.views.solicitud_accion |
| /compras/solicitudes/<int:pk>/editar/ | compras:solicitud_editar | POST/MUTABLE | Sí | compras.views.solicitud_editar |
| /compras/solicitudes/<int:pk>/lineas/<int:linea_id>/retirar/ | compras:solicitud_linea_retirar | GET SEGURA | Sí | compras.views.solicitud_linea_retirar |
| /compras/solicitudes/<int:pk>/lineas/agregar/ | compras:solicitud_linea_agregar | GET SEGURA | Sí | compras.views.solicitud_linea_agregar |
| /compras/solicitudes/<int:solicitud_id>/crear-expediente/ | compras:expediente_desde_solicitud | POST/MUTABLE | Sí | compras.views.expediente_desde_solicitud_view |
| /compras/solicitudes/dashboard/ | compras:solicitudes_dashboard | GET SEGURA | No | compras.views.solicitudes_dashboard |
| /compras/solicitudes/exportar/ | compras:solicitudes_exportar | EXPORTACIÓN | No | compras.views.solicitudes_exportar |
| /compras/solicitudes/nueva/ | compras:solicitud_crear | POST/MUTABLE | No | compras.views.solicitud_editar |
| /conduce/<int:conduce_id>/anular/ | anular_conduce | POST/MUTABLE | Sí | conduces.views.anular_conduce |
| /conduce/<int:conduce_id>/editar/ | editar_conduce | POST/MUTABLE | Sí | conduces.views.editar_conduce |
| /conduce/<int:conduce_id>/eliminar/ | eliminar_conduce | POST/MUTABLE | Sí | conduces.views.eliminar_conduce |
| /conduce/<int:conduce_id>/pdf/ | visualizar_pdf_conduce | DESCARGA | Sí | conduces.views.visualizar_pdf_conduce |
| /conduce/<int:conduce_id>/vista/ | vista_conduce | GET SEGURA | Sí | conduces.views.vista_conduce |
| /contabilidad/ | contabilidad:dashboard | GET SEGURA | No | contabilidad.views.dashboard_contabilidad |
| /contabilidad/aportes/ | contabilidad:aportes_socios | GET SEGURA | No | contabilidad.views.aportes_socios |
| /contabilidad/aportes/crear/ | contabilidad:crear_aporte_socio | POST/MUTABLE | No | contabilidad.views.crear_aporte_socio |
| /contabilidad/cuentas-por-cobrar/ | contabilidad:cuentas_por_cobrar | GET SEGURA | No | contabilidad.views.cuentas_por_cobrar |
| /contabilidad/cuentas-por-cobrar/<int:cuenta_id>/cobro/ | contabilidad:registrar_cobro_cxc | POST/MUTABLE | Sí | contabilidad.views.registrar_cobro_cxc |
| /contabilidad/cuentas-por-cobrar/crear/ | contabilidad:crear_cuenta_por_cobrar | POST/MUTABLE | No | contabilidad.views.crear_cuenta_por_cobrar |
| /contabilidad/cuentas-por-pagar/ | contabilidad:cuentas_por_pagar | POST/MUTABLE | No | contabilidad.views.cuentas_por_pagar |
| /contabilidad/cuentas-por-pagar/<int:cuenta_id>/pago/ | contabilidad:registrar_pago_cxp | POST/MUTABLE | Sí | contabilidad.views.registrar_pago_cxp |
| /contabilidad/cuentas-por-pagar/crear/ | contabilidad:crear_cuenta_por_pagar | POST/MUTABLE | No | contabilidad.views.crear_cuenta_por_pagar |
| /contabilidad/deudas-socios/ | contabilidad:deudas_socios | GET SEGURA | No | contabilidad.views.deudas_socios |
| /contabilidad/deudas-socios/crear/ | contabilidad:crear_deuda_socio | POST/MUTABLE | No | contabilidad.views.crear_deuda_socio |
| /contabilidad/enterprise/ | contabilidad:dashboard_enterprise | GET SEGURA | No | contabilidad.views.dashboard_enterprise |
| /contabilidad/factoring/ | contabilidad:factoring | GET SEGURA | No | contabilidad.views.factoring |
| /contabilidad/factoring/<int:factoring_id>/ | contabilidad:detalle_factoring | GET SEGURA | Sí | contabilidad.views.detalle_factoring |
| /contabilidad/factoring/<int:factoring_id>/pago/ | contabilidad:registrar_pago_factoring | POST/MUTABLE | Sí | contabilidad.views.registrar_pago_factoring |
| /contabilidad/factoring/crear/ | contabilidad:crear_factoring | POST/MUTABLE | No | contabilidad.views.crear_factoring |
| /contabilidad/facturas-606/ | contabilidad:facturas_606 | GET SEGURA | No | contabilidad.views.lista_facturas_606 |
| /contabilidad/facturas-606/crear/ | contabilidad:crear_factura_606 | POST/MUTABLE | No | contabilidad.views.crear_factura_606 |
| /contabilidad/gastos/ | contabilidad:gastos | GET SEGURA | No | contabilidad.views.gastos |
| /contabilidad/gastos/crear/ | contabilidad:crear_gasto | POST/MUTABLE | No | contabilidad.views.crear_gasto |
| /contabilidad/gastos/exportar-606/ | contabilidad:exportar_606_excel | EXPORTACIÓN | No | contabilidad.views.exportar_606_excel |
| /contabilidad/presupuesto/ | contabilidad:presupuesto | GET SEGURA | No | contabilidad.views.presupuesto |
| /contabilidad/presupuesto/crear/ | contabilidad:crear_presupuesto | POST/MUTABLE | No | contabilidad.views.crear_presupuesto |
| /contabilidad/proveedores/ | contabilidad:proveedores | GET SEGURA | No | contabilidad.views.lista_proveedores |
| /contabilidad/proveedores/crear/ | contabilidad:crear_proveedor | POST/MUTABLE | No | contabilidad.views.crear_proveedor |
| /contabilidad/reportes/ | contabilidad:reportes_financieros | GET SEGURA | No | contabilidad.views.reportes_financieros |
| /contabilidad/reportes/balance-general/ | contabilidad:balance_general | GET SEGURA | No | contabilidad.views.balance_general |
| /contabilidad/reportes/cuentas-por-cobrar/ | contabilidad:reporte_cuentas_por_cobrar | GET SEGURA | No | contabilidad.views.reporte_cuentas_por_cobrar |
| /contabilidad/reportes/cuentas-por-pagar/ | contabilidad:reporte_cuentas_por_pagar | POST/MUTABLE | No | contabilidad.views.reporte_cuentas_por_pagar |
| /contabilidad/reportes/estado-resultados/ | contabilidad:estado_resultados | POST/MUTABLE | No | contabilidad.views.estado_resultados |
| /contabilidad/reportes/flujo-efectivo/ | contabilidad:flujo_efectivo | GET SEGURA | No | contabilidad.views.flujo_efectivo |
| /contabilidad/socios/ | contabilidad:socios | GET SEGURA | No | contabilidad.views.socios |
| /contabilidad/socios/crear/ | contabilidad:crear_socio | POST/MUTABLE | No | contabilidad.views.crear_socio |
| /core/ | core:motor_dashboard | GET SEGURA | No | core.views.motor_dashboard |
| /core/360/<str:tipo>/<int:pk>/ | core:enterprise_360 | GET SEGURA | Sí | core.experience_views.enterprise_360 |
| /core/actividad/ | core:actividad | GET SEGURA | No | core.experience_views.actividad |
| /core/alertas/ | core:alertas | GET SEGURA | No | core.experience_views.alertas |
| /core/alertas/<int:pk>/<str:accion>/ | core:alerta_accion | POST/MUTABLE | Sí | core.experience_views.alerta_accion |
| /core/buscar/ | core:busqueda_global | GET SEGURA | No | core.experience_views.busqueda_global |
| /core/conciliaciones/ | core:conciliaciones | GET SEGURA | No | core.views.conciliaciones_lista |
| /core/conciliaciones/<int:pk>/ | core:conciliacion_detalle | GET SEGURA | Sí | core.views.conciliacion_detalle |
| /core/conciliaciones/diagnosticar/ | core:diagnostico_producto | GET SEGURA | No | core.views.diagnostico_producto |
| /core/conciliaciones/previsualizar/ | core:previsualizar_saldo | GET SEGURA | No | core.views.previsualizar_saldo |
| /core/conciliaciones/reconstruir/ | core:reconstruir_saldo | GET SEGURA | No | core.views.reconstruir_saldo |
| /core/design-system/ | core:design_system | GET SEGURA | No | core.views.design_system |
| /core/eventos/ | core:eventos | GET SEGURA | No | core.views.eventos_lista |
| /core/eventos/<int:pk>/ | core:evento_detalle | GET SEGURA | Sí | core.views.evento_detalle |
| /core/eventos/<int:pk>/reintentar/ | core:evento_reintentar | POST/MUTABLE | Sí | core.views.evento_reintentar |
| /core/eventos/fallidos/ | core:eventos_fallidos | GET SEGURA | No | core.views.eventos_fallidos |
| /core/favoritos/toggle/ | core:favorito_toggle | POST/MUTABLE | No | core.experience_views.favorito_toggle |
| /core/idempotencia/ | core:idempotencias | GET SEGURA | No | core.views.idempotencias_lista |
| /core/idempotencia/<int:pk>/ | core:idempotencia_detalle | GET SEGURA | Sí | core.views.idempotencia_detalle |
| /core/idempotencia/<int:pk>/cerrar/ | core:idempotencia_cerrar | POST/MUTABLE | Sí | core.views.idempotencia_cerrar |
| /core/secuencias/ | core:secuencias | GET SEGURA | No | core.views.secuencias_lista |
| /core/secuencias/<int:pk>/ | core:secuencia_detalle | GET SEGURA | Sí | core.views.secuencia_detalle |
| /core/secuencias/<int:pk>/editar/ | core:secuencia_editar | POST/MUTABLE | Sí | core.views.secuencia_editar |
| /core/secuencias/crear/ | core:secuencia_crear | POST/MUTABLE | No | core.views.secuencia_crear |
| /core/workspace/ | core:workspace_home | GET SEGURA | No | core.experience_views.workspace_home |
| /core/workspace/<str:dominio>/ | core:workspace | GET SEGURA | Sí | core.experience_views.workspace |
| /documentos/ | documentos:lista | GET SEGURA | No | documentos.views.documentos_lista |
| /documentos/<int:pk>/ | documentos:detalle | GET SEGURA | Sí | documentos.views.documento_detalle |
| /documentos/<int:pk>/anular/ | documentos:anular | POST/MUTABLE | Sí | documentos.views.documento_anular |
| /documentos/<int:pk>/descargar/ | documentos:descargar | DESCARGA | Sí | documentos.views.documento_descargar |
| /documentos/<int:pk>/reemplazar/ | documentos:reemplazar | GET SEGURA | Sí | documentos.views.documento_reemplazar |
| /documentos/objeto/<str:app_label>/<str:model>/<int:object_id>/ | documentos:objeto | GET SEGURA | Sí | documentos.views.documentos_objeto |
| /documentos/objeto/<str:app_label>/<str:model>/<int:object_id>/cargar/ | documentos:cargar | GET SEGURA | Sí | documentos.views.documento_cargar |
| /facturacion/ | facturacion | GET SEGURA | No | conduces.views.facturacion |
| /facturacion/<int:factura_id>/anular/ | anular_factura | POST/MUTABLE | Sí | conduces.views.anular_factura |
| /facturacion/<int:factura_id>/editar/ | editar_factura | POST/MUTABLE | Sí | conduces.views.editar_factura |
| /facturacion/<int:factura_id>/eliminar/ | eliminar_factura | POST/MUTABLE | Sí | conduces.views.eliminar_factura |
| /facturacion/<int:factura_id>/pdf/ | pdf_factura | DESCARGA | Sí | conduces.views.pdf_factura |
| /facturacion/comprobantes/<int:comprobante_id>/editar/ | editar_comprobante | POST/MUTABLE | Sí | conduces.views.editar_comprobante |
| /facturacion/comprobantes/<int:comprobante_id>/eliminar/ | eliminar_comprobante | POST/MUTABLE | Sí | conduces.views.eliminar_comprobante |
| /facturacion/comprobantes/crear/ | crear_comprobante_fiscal | POST/MUTABLE | No | conduces.views.crear_comprobante_fiscal |
| /facturacion/generar/ | generar_factura | POST/MUTABLE | No | conduces.utils.wrapper |
| /facturacion/ncf/rango/ | crear_rango_ncf | POST/MUTABLE | No | conduces.views.crear_rango_ncf |
| /facturacion/productos/<int:producto_id>/editar/ | editar_producto_facturacion | POST/MUTABLE | Sí | conduces.views.editar_producto_facturacion |
| /facturacion/productos/<int:producto_id>/eliminar/ | eliminar_producto_facturacion | POST/MUTABLE | Sí | conduces.views.eliminar_producto_facturacion |
| /facturacion/productos/crear/ | crear_producto_facturacion | POST/MUTABLE | No | conduces.views.crear_producto_facturacion |
| /generar-conduces/ | generar_conduces | POST/MUTABLE | No | conduces.utils.wrapper |
| /inventario/ | inventario:dashboard | GET SEGURA | No | inventario.views.dashboard_inventario |
| /inventario/cargar-excel/ | inventario:cargar_excel | EXPORTACIÓN | No | inventario.views.cargar_inventario_excel |
| /inventario/detalle-orden/<int:detalle_id>/actualizar/ | inventario:actualizar_detalle_orden | POST/MUTABLE | Sí | inventario.views.actualizar_detalle_orden |
| /inventario/detalle-orden/<int:detalle_id>/eliminar/ | inventario:eliminar_detalle_orden | POST/MUTABLE | Sí | inventario.views.eliminar_detalle_orden |
| /inventario/inventario/pdf/ | inventario:pdf_inventario | DESCARGA | No | inventario.views.pdf_inventario |
| /inventario/movimiento/registrar/ | inventario:registrar_movimiento_manual | POST/MUTABLE | No | inventario.views.registrar_movimiento_manual |
| /inventario/movimientos/ | inventario:movimientos | GET SEGURA | No | inventario.views.movimientos |
| /inventario/orden-compra/<int:orden_id>/ | inventario:detalle_orden_compra | GET SEGURA | Sí | inventario.views.detalle_orden_compra |
| /inventario/orden-compra/<int:orden_id>/agregar-producto/ | inventario:agregar_producto_manual_orden | GET SEGURA | Sí | inventario.views.agregar_producto_manual_orden |
| /inventario/orden-compra/<int:orden_id>/calcular/ | inventario:calcular_orden_compra | GET SEGURA | Sí | inventario.views.calcular_orden_compra |
| /inventario/orden-compra/<int:orden_id>/eliminar/ | inventario:eliminar_orden_compra | POST/MUTABLE | Sí | inventario.views.eliminar_orden_compra |
| /inventario/orden-compra/<int:orden_id>/pdf/ | inventario:pdf_orden_compra | DESCARGA | Sí | inventario.views.pdf_orden_compra |
| /inventario/orden-compra/<int:orden_id>/pdf/descargar/ | inventario:descargar_pdf_orden_compra | DESCARGA | Sí | inventario.views.descargar_pdf_orden_compra |
| /inventario/orden-compra/<int:orden_id>/recibir/ | inventario:recibir_orden_compra | GET SEGURA | Sí | inventario.views.recibir_orden_compra |
| /inventario/ordenes-compra/ | inventario:ordenes_compra | GET SEGURA | No | inventario.views.ordenes_compra |
| /inventario/ordenes-compra/generar/ | inventario:generar_orden_compra | POST/MUTABLE | No | inventario.views.generar_orden_compra_sugerida |
| /inventario/plantilla-excel/ | inventario:descargar_plantilla | DESCARGA | No | inventario.views.descargar_plantilla_inventario |
| /inventario/prestamos/ | inventario:prestamos | GET SEGURA | No | inventario.views.prestamos |
| /inventario/prestamos/<int:prestamo_id>/devolucion/ | inventario:registrar_devolucion_prestamo | POST/MUTABLE | Sí | inventario.views.registrar_devolucion_prestamo |
| /inventario/prestamos/crear/ | inventario:crear_prestamo | POST/MUTABLE | No | inventario.views.crear_prestamo |
| /inventario/produccion/ | inventario:produccion | GET SEGURA | No | inventario.views.produccion |
| /inventario/produccion/<int:produccion_id>/ | inventario:detalle_produccion | GET SEGURA | Sí | inventario.views.detalle_produccion |
| /inventario/produccion/<int:produccion_id>/consumo-manual/ | inventario:registrar_consumo_manual | POST/MUTABLE | Sí | inventario.views.registrar_consumo_manual |
| /inventario/produccion/<int:produccion_id>/ejecutar/ | inventario:ejecutar_produccion | GET SEGURA | Sí | inventario.views.ejecutar_produccion |
| /inventario/produccion/dashboard/ | inventario:produccion_dashboard | GET SEGURA | No | inventario.produccion_views.produccion_dashboard |
| /inventario/produccion/generar/ | inventario:generar_produccion_desde_menu | POST/MUTABLE | No | inventario.views.generar_produccion_desde_menu |
| /inventario/produccion/necesidades/ | inventario:necesidades_materia_prima | GET SEGURA | No | inventario.produccion_views.necesidades_materia_prima |
| /inventario/produccion/ordenes/ | inventario:ordenes_lista | GET SEGURA | No | inventario.produccion_views.ordenes_lista |
| /inventario/produccion/ordenes/<int:pk>/ | inventario:orden_detalle | GET SEGURA | Sí | inventario.produccion_views.orden_detalle |
| /inventario/produccion/ordenes/<int:pk>/cancelar/ | inventario:orden_cancelar | POST/MUTABLE | Sí | inventario.produccion_views.orden_cancelar |
| /inventario/produccion/ordenes/<int:pk>/completar/ | inventario:orden_completar | POST/MUTABLE | Sí | inventario.produccion_views.orden_completar |
| /inventario/produccion/ordenes/<int:pk>/editar/ | inventario:orden_editar | POST/MUTABLE | Sí | inventario.produccion_views.orden_editar |
| /inventario/produccion/ordenes/<int:pk>/iniciar/ | inventario:orden_iniciar | POST/MUTABLE | Sí | inventario.produccion_views.orden_iniciar |
| /inventario/produccion/ordenes/<int:pk>/programar/ | inventario:orden_programar | GET SEGURA | Sí | inventario.produccion_views.orden_programar |
| /inventario/produccion/ordenes/nueva/ | inventario:orden_crear | POST/MUTABLE | No | inventario.produccion_views.orden_crear |
| /inventario/produccion/planes/ | inventario:planes_lista | GET SEGURA | No | inventario.produccion_views.planes_lista |
| /inventario/produccion/planes/<int:pk>/ | inventario:plan_detalle | GET SEGURA | Sí | inventario.produccion_views.plan_detalle |
| /inventario/produccion/planes/<int:pk>/aprobar/ | inventario:plan_aprobar | POST/MUTABLE | Sí | inventario.produccion_views.plan_aprobar |
| /inventario/produccion/planes/<int:pk>/cancelar/ | inventario:plan_cancelar | POST/MUTABLE | Sí | inventario.produccion_views.plan_cancelar |
| /inventario/produccion/planes/<int:pk>/editar/ | inventario:plan_editar | POST/MUTABLE | Sí | inventario.produccion_views.plan_editar |
| /inventario/produccion/planes/<int:pk>/generar-ordenes/ | inventario:plan_generar_ordenes | POST/MUTABLE | Sí | inventario.produccion_views.plan_generar_ordenes |
| /inventario/produccion/planes/generar-pedidos/ | inventario:plan_generar_desde_pedidos | POST/MUTABLE | No | inventario.produccion_views.plan_generar_desde_pedidos |
| /inventario/produccion/planes/nuevo/ | inventario:plan_crear | POST/MUTABLE | No | inventario.produccion_views.plan_crear |
| /inventario/produccion/programacion/diaria/ | inventario:produccion_programacion_diaria | GET SEGURA | No | inventario.produccion_views.produccion_programacion_diaria |
| /inventario/produccion/programacion/semanal/ | inventario:produccion_programacion_semanal | GET SEGURA | No | inventario.produccion_views.produccion_programacion_semanal |
| /inventario/produccion/recetas/ | inventario:recetas_lista | GET SEGURA | No | inventario.produccion_views.recetas_lista |
| /inventario/produccion/recetas/<int:pk>/ | inventario:receta_detalle | GET SEGURA | Sí | inventario.produccion_views.receta_detalle |
| /inventario/produccion/recetas/<int:pk>/duplicar/ | inventario:receta_duplicar | POST/MUTABLE | Sí | inventario.produccion_views.receta_duplicar |
| /inventario/produccion/recetas/<int:pk>/editar/ | inventario:receta_editar | POST/MUTABLE | Sí | inventario.produccion_views.receta_editar |
| /inventario/produccion/recetas/<int:pk>/estado/ | inventario:receta_cambiar_estado | POST/MUTABLE | Sí | inventario.produccion_views.receta_cambiar_estado |
| /inventario/produccion/recetas/nueva/ | inventario:receta_crear | POST/MUTABLE | No | inventario.produccion_views.receta_crear |
| /inventario/producto/<int:producto_id>/desactivar/ | inventario:desactivar_producto_inventario | POST/MUTABLE | Sí | inventario.views.desactivar_producto_inventario |
| /inventario/producto/<int:producto_id>/editar/ | inventario:editar_producto_inventario | POST/MUTABLE | Sí | inventario.views.editar_producto_inventario |
| /inventario/producto/<int:producto_id>/kardex/ | inventario:kardex_producto | GET SEGURA | Sí | inventario.views.kardex_producto |
| /inventario/productos/ | inventario:productos | GET SEGURA | No | inventario.views.productos_inventario |
| /inventario/proyeccion/generar/ | inventario:generar_proyeccion_consumo | POST/MUTABLE | No | inventario.views.generar_proyeccion_consumo |
| /inventario/recetas/ | inventario:recetas | GET SEGURA | No | inventario.views.recetas |
| /inventario/recetas/<int:receta_id>/ | inventario:detalle_receta | GET SEGURA | Sí | inventario.views.detalle_receta |
| /inventario/recetas/<int:receta_id>/ingrediente/agregar/ | inventario:agregar_ingrediente_receta | GET SEGURA | Sí | inventario.views.agregar_ingrediente_receta |
| /inventario/recetas/crear/ | inventario:crear_receta | POST/MUTABLE | No | inventario.views.crear_receta |
| /inventario/recetas/ingrediente/<int:detalle_id>/eliminar/ | inventario:eliminar_ingrediente_receta | POST/MUTABLE | Sí | inventario.views.eliminar_ingrediente_receta |
| /inventario/recetas/producto/crear/ | inventario:crear_producto_produccion | POST/MUTABLE | No | inventario.views.crear_producto_produccion |
| /login/ | login_usuario | GET SEGURA | No | conduces.views.login_usuario |
| /logout/ | logout_usuario | GET SEGURA | No | conduces.views.logout_usuario |
| /menu/crear/ | crear_menu_diario | POST/MUTABLE | No | conduces.views.crear_menu_diario |
| /menu/editar/<int:menu_id>/ | editar_menu_diario | POST/MUTABLE | Sí | conduces.views.editar_menu_diario |
| /menu/eliminar/<int:menu_id>/ | eliminar_menu_diario | POST/MUTABLE | Sí | conduces.views.eliminar_menu_diario |
| /mi-empresa/ | mi_empresa | GET SEGURA | No | conduces.views.mi_empresa |
| /mi-empresa/usuarios/crear/ | crear_usuario_empresa | POST/MUTABLE | No | conduces.views.crear_usuario_empresa |
| /nota-aclaratoria/pdf/ | generar_nota_aclaratoria_pdf | DESCARGA | No | conduces.utils.wrapper |
| /nota-aclaratoria/preparar/ | preparar_nota_aclaratoria | GET SEGURA | No | conduces.utils.wrapper |
| /password-reset/ | password_reset | GET SEGURA | No | django.contrib.auth.views.view |
| /password-reset/done/ | password_reset_done | GET SEGURA | No | django.contrib.auth.views.view |
| /plantilla-centros/ | plantilla_centros | DESCARGA | No | conduces.views.descargar_plantilla_centros |
| /plantilla-menu/ | plantilla_menu | DESCARGA | No | conduces.views.descargar_plantilla_menu |
| /reenviar-codigo/ | reenviar_codigo_correo | GET SEGURA | No | conduces.views.reenviar_codigo_correo |
| /registro/ | registro | GET SEGURA | No | conduces.views.registro |
| /relacion-diaria/pdf/ | generar_relacion_diaria_pdf | DESCARGA | No | conduces.utils.wrapper |
| /relacion-general/pdf/ | generar_relacion_general_pdf | DESCARGA | No | conduces.utils.wrapper |
| /reset/<uidb64>/<token>/ | password_reset_confirm | GET SEGURA | Sí | django.contrib.auth.views.view |
| /reset/done/ | password_reset_complete | GET SEGURA | No | django.contrib.auth.views.view |
| /verificar-correo/ | verificar_correo | GET SEGURA | No | conduces.views.verificar_correo |
| /workflow/ | workflow:dashboard | GET SEGURA | No | workflow.views.dashboard |
| /workflow/bandeja/ | workflow:bandeja | GET SEGURA | No | workflow.views.bandeja |
| /workflow/exportar/ | workflow:exportar | EXPORTACIÓN | No | workflow.views.exportar |
| /workflow/instancias/<int:pk>/ | workflow:instancia | GET SEGURA | Sí | workflow.views.instancia_detalle |
| /workflow/instancias/<int:pk>/<str:accion>/ | workflow:decidir | POST/MUTABLE | Sí | workflow.views.decidir |
| /workflow/reglas/ | workflow:reglas | GET SEGURA | No | workflow.views.reglas |
| /workflow/reglas/<int:pk>/ | workflow:regla_detalle | GET SEGURA | Sí | workflow.views.regla_detalle |
| /workflow/reglas/<int:pk>/<str:accion>/ | workflow:regla_accion | POST/MUTABLE | Sí | workflow.views.regla_accion |
| /workflow/reglas/<int:pk>/agregar/<str:tipo>/ | workflow:regla_agregar | GET SEGURA | Sí | workflow.views.regla_agregar |
| /workflow/reglas/<int:pk>/editar/ | workflow:regla_editar | POST/MUTABLE | Sí | workflow.views.regla_editar |
| /workflow/reglas/<int:pk>/nivel/<int:nivel_id>/agregar/<str:tipo>/ | workflow:nivel_agregar | GET SEGURA | Sí | workflow.views.regla_agregar |
| /workflow/reglas/nueva/ | workflow:regla_crear | POST/MUTABLE | No | workflow.views.regla_editar |
| /workflow/reportes/ | workflow:reportes | GET SEGURA | No | workflow.views.reportes |
| /workflow/suplencias/ | workflow:suplencias | GET SEGURA | No | workflow.views.suplencias |
