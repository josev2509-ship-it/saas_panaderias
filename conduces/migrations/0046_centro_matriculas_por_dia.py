from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("conduces", "0045_alter_conduce_numero_and_more")]

    operations = [
        migrations.AddField(
            model_name="centroeducativo", name="matricula_lunes_viernes",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="centroeducativo", name="matricula_fin_semana",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
