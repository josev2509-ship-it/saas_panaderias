from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("contabilidad", "0016_alter_anticipoproveedor_estado"), ("tesoreria", "0002_importacionextractobancario_lineaextractobancario_and_more")]
    operations = [
        migrations.AddField(model_name="solicitudpago", name="fecha_prevista", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="solicitudpago", name="prioridad", field=models.CharField(choices=[("BAJA", "Baja"), ("MEDIA", "Media"), ("ALTA", "Alta"), ("URGENTE", "Urgente")], default="MEDIA", max_length=10)),
        migrations.AddField(model_name="solicitudpago", name="cuenta_prevista", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="pagos_programados", to="tesoreria.cuentabancariaempresa")),
        migrations.AddField(model_name="solicitudpago", name="observacion", field=models.TextField(blank=True)),
    ]
