from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


MATRIZ={
 "Administrador de Compras":None,
 "Gestor de Proveedores":{"view_proveedor","add_proveedor","change_proveedor","activar_proveedor","suspender_proveedor","bloquear_proveedor","reactivar_proveedor","inactivar_proveedor","exportar_proveedores","view_riesgo_proveedor","view_contactoproveedor","add_contactoproveedor","change_contactoproveedor","view_direccionproveedor","add_direccionproveedor","change_direccionproveedor","view_productoproveedor","add_productoproveedor","change_productoproveedor","establecer_proveedor_preferido","view_cuentabancariaproveedor","add_cuentabancariaproveedor","change_cuentabancariaproveedor","verificar_cuenta_bancaria","view_documentos_proveedor","gestionar_documentos_proveedor","revisar_documentos_proveedor","view_correspondencia_proveedor","gestionar_correspondencia_proveedor"},
 "Comprador":{"view_proveedor","view_contactoproveedor","view_direccionproveedor","view_productoproveedor","view_documentos_proveedor"},
 "Auditor de Compras":{"view_proveedor","view_riesgo_proveedor","view_contactoproveedor","view_direccionproveedor","view_productoproveedor","view_cuentabancariaproveedor","view_documentos_proveedor","view_correspondencia_proveedor","exportar_proveedores"},
 "Consulta de Compras":{"view_proveedor","view_contactoproveedor","view_direccionproveedor","view_productoproveedor"},
}
class Command(BaseCommand):
 help="Crea grupos y asigna permisos de Compras sin retirar permisos externos."
 def handle(self,*args,**opts):
  all_perms=Permission.objects.filter(content_type__app_label="compras")
  for nombre,codes in MATRIZ.items():
   group,_=Group.objects.get_or_create(name=nombre)
   selected=all_perms if codes is None else all_perms.filter(codename__in=codes)
   group.permissions.add(*selected)
   self.stdout.write(f"{nombre}: {selected.count()} permisos")
