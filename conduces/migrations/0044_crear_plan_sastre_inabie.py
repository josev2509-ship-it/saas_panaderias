from decimal import Decimal

from django.db import migrations


def crear_plan_sastre_inabie(apps, schema_editor):
    Plan = apps.get_model("conduces", "Plan")

    Plan.objects.get_or_create(
        codigo="SASTRE_INABIE",
        defaults={
            "nombre": "SASTRE INABIE",
            "precio": Decimal("1500.00"),
            "moneda": "DOP",
            "periodicidad": "MONTHLY",
            "activo": True,

            "modulo_inabie": True,
            "modulo_conduces": True,
            "modulo_centros": True,
            "modulo_menu": True,
            "modulo_facturacion": True,
            "modulo_reportes": True,

            "modulo_rutas": False,
            "modulo_nomina": False,
            "modulo_inventario": False,
            "modulo_catalogos": False,
            "modulo_compras": False,
            "modulo_workflow": False,
        },
    )


def revertir(apps, schema_editor):
    Plan = apps.get_model("conduces", "Plan")
    Plan.objects.filter(
        codigo="SASTRE_INABIE"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "conduces",
            "0043_empresasaas_fecha_suspension_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(
            crear_plan_sastre_inabie,
            revertir,
        ),
    ]
