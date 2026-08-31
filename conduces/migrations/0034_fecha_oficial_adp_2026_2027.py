from datetime import date

from django.db import migrations


def agregar_dia_adp(apps, schema_editor):
    FechaOficialCalendario = apps.get_model("conduces", "FechaOficialCalendario")
    FechaOficialCalendario.objects.update_or_create(
        anio_inicio=2026,
        anio_fin=2027,
        fecha=date(2027, 4, 13),
        defaults={
            "clasificacion": "NO_LECTIVO",
            "motivo": "Día de la ADP",
            "fuente": "Calendario escolar oficial 2026-2027",
            "activa": True,
        },
    )


def retirar_dia_adp(apps, schema_editor):
    FechaOficialCalendario = apps.get_model("conduces", "FechaOficialCalendario")
    FechaOficialCalendario.objects.filter(
        anio_inicio=2026,
        anio_fin=2027,
        fecha=date(2027, 4, 13),
        motivo="Día de la ADP",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("conduces", "0033_fechaoficialcalendario")]
    operations = [migrations.RunPython(agregar_dia_adp, retirar_dia_adp)]
