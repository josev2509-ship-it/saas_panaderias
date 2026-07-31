from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from catalogos.models import Moneda, MonedaEmpresa, TipoCompra
from comercial.models import SecuenciaDocumento
from conduces.models import Empresa

TIPOS = [
    ("MP", "Materia prima", "BIEN", True, True, True),
    ("EMP", "Empaque", "BIEN", True, True, False),
    ("PT", "Producto terminado", "BIEN", True, True, False),
    ("REP", "Repuesto", "BIEN", True, True, False),
    ("MAN", "Mantenimiento", "SERVICIO", False, True, False),
    ("SER", "Servicio", "SERVICIO", False, True, False),
    ("AF", "Activo fijo", "ACTIVO", False, True, True),
    ("SUM", "Suministro", "BIEN", True, True, False),
    ("GO", "Gasto operativo", "GASTO", False, False, False),
    ("EXT", "Compra extraordinaria", "GASTO", False, True, False),
]

SECUENCIAS_FUTURAS = {
    "PROV": "PROV", "SC": "SC", "COT": "COT", "ADJ": "ADJ",
    "OC": "OC", "REC": "REC", "DEV": "DEV", "EVP": "EVP",
}

ROLES = {
    "Administrador de catálogos": None,
    "Consulta de catálogos": {"view_moneda", "view_monedaempresa", "view_condicionpago", "view_unidadmedida", "view_conversionunidad", "view_almacen", "view_centrocosto", "view_impuesto", "view_tipocompra"},
}


class Command(BaseCommand):
    help = "Configura monedas, tipos de compra y grupos de catálogos de forma idempotente."

    @transaction.atomic
    def handle(self, *args, **options):
        dop, _ = Moneda.objects.update_or_create(codigo="DOP", defaults={"nombre": "Peso dominicano", "simbolo": "RD$", "activa": True})
        Moneda.objects.update_or_create(codigo="USD", defaults={"nombre": "Dólar estadounidense", "simbolo": "US$", "activa": True})
        Moneda.objects.update_or_create(codigo="EUR", defaults={"nombre": "Euro", "simbolo": "€", "activa": True})
        for empresa in Empresa.objects.all():
            MonedaEmpresa.objects.get_or_create(empresa=empresa, moneda=dop, defaults={"es_base": True})
            for codigo, nombre, naturaleza, inventario, recepcion, inspeccion in TIPOS:
                TipoCompra.objects.update_or_create(
                    empresa=empresa, codigo=codigo,
                    defaults={"nombre": nombre, "naturaleza": naturaleza, "afecta_inventario": inventario, "requiere_recepcion": recepcion, "requiere_inspeccion": inspeccion},
                )
            for tipo, prefijo in SECUENCIAS_FUTURAS.items():
                SecuenciaDocumento.objects.get_or_create(
                    empresa=empresa, tipo=tipo, periodo=0,
                    defaults={"prefijo": prefijo, "longitud": 6, "reinicia_anualmente": False},
                )
        app_permissions = Permission.objects.filter(content_type__app_label="catalogos")
        admin_empresa, _ = Group.objects.get_or_create(name="Administrador de empresa")
        admin_empresa.permissions.add(*app_permissions)
        for nombre, codenames in ROLES.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            permisos = app_permissions if codenames is None else app_permissions.filter(codename__in=codenames)
            grupo.permissions.set(permisos)
        self.stdout.write(self.style.SUCCESS("Catálogos y roles configurados."))
