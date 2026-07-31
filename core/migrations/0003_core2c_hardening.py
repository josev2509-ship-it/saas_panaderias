import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_alter_conciliacioninventario_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="conciliacioninventario",
            name="corregido_por",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="+", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="conciliacioninventario",
            name="saldo_disponible",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=16),
        ),
        migrations.AddField(
            model_name="conciliacioninventario",
            name="saldo_reservado",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=16),
        ),
        migrations.AddField(
            model_name="conciliacioninventario",
            name="severidad",
            field=models.CharField(
                choices=[
                    ("NINGUNA", "Ninguna"), ("BAJA", "Baja"),
                    ("MEDIA", "Media"), ("ALTA", "Alta"),
                ],
                default="NINGUNA", max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="eventodominio",
            name="categoria",
            field=models.CharField(
                choices=[
                    ("TRAZABILIDAD", "Trazabilidad"),
                    ("EJECUTABLE", "Ejecutable"),
                ],
                default="TRAZABILIDAD", max_length=15,
            ),
        ),
        migrations.AddField(
            model_name="eventodominio",
            name="fecha_ultimo_intento",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="eventodominio",
            name="requiere_consumidor",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="conciliacioninventario",
            name="estado",
            field=models.CharField(
                choices=[
                    ("CONSISTENTE", "Consistente"), ("DIFERENCIA", "Diferencia"),
                    ("CORREGIDA", "Corregida"), ("IGNORADA", "Ignorada"),
                    ("REQUIERE_INTERVENCION", "Requiere intervencion"),
                ],
                max_length=24,
            ),
        ),
        migrations.AlterField(
            model_name="eventodominio",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"), ("PROCESANDO", "Procesando"),
                    ("PROCESADO", "Procesado"), ("ERROR", "Error"),
                    ("AGOTADO", "Agotado"), ("CANCELADO", "Cancelado"),
                ],
                default="PENDIENTE", max_length=15,
            ),
        ),
    ]
