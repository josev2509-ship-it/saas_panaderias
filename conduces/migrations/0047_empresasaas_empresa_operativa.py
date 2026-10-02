from django.db import migrations, models
import django.db.models.deletion


def vincular_empresas_historicas(apps, schema_editor):
    Empresa = apps.get_model("conduces", "Empresa")
    EmpresaSaaS = apps.get_model("conduces", "EmpresaSaaS")
    PerfilUsuario = apps.get_model("conduces", "PerfilUsuario")

    for empresa_saas in EmpresaSaaS.objects.filter(empresa_operativa__isnull=True).iterator():
        user_ids = PerfilUsuario.objects.filter(empresa=empresa_saas).values_list("user_id", flat=True)
        candidatos = list(Empresa.objects.filter(usuario_id__in=user_ids).distinct()[:2])

        if len(candidatos) != 1 and empresa_saas.rnc:
            candidatos = list(Empresa.objects.filter(rnc=empresa_saas.rnc).distinct()[:2])

        if len(candidatos) != 1 and empresa_saas.correo:
            correo = empresa_saas.correo.strip().lower()
            candidatos = list(Empresa.objects.filter(correo__iexact=correo).distinct()[:2])

        if len(candidatos) != 1:
            continue

        operativa = candidatos[0]
        if EmpresaSaaS.objects.filter(empresa_operativa=operativa).exclude(pk=empresa_saas.pk).exists():
            continue

        campos = ["empresa_operativa"]
        empresa_saas.empresa_operativa = operativa
        if empresa_saas.nombre.strip().casefold() == "mi empresa" and operativa.nombre.strip():
            empresa_saas.nombre = operativa.nombre
            campos.append("nombre")
        if not empresa_saas.rnc and operativa.rnc:
            empresa_saas.rnc = operativa.rnc
            campos.append("rnc")
        if not empresa_saas.correo and operativa.correo:
            empresa_saas.correo = operativa.correo
            campos.append("correo")
        empresa_saas.save(update_fields=campos)


class Migration(migrations.Migration):
    dependencies = [("conduces", "0046_centro_matriculas_por_dia")]

    operations = [
        migrations.AddField(
            model_name="empresasaas",
            name="empresa_operativa",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="empresa_saas",
                to="conduces.empresa",
            ),
        ),
        migrations.RunPython(vincular_empresas_historicas, migrations.RunPython.noop),
    ]
