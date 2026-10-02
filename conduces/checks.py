from django.core.checks import Tags, Warning, register
from django.db import models

from .models import EmpresaSaaS, PerfilUsuario


@register(Tags.database)
def tenant_integrity_check(app_configs, **kwargs):
    warnings = []
    try:
        sin_vinculo = EmpresaSaaS.objects.filter(empresa_operativa__isnull=True).count()
        admins_sin_saas = PerfilUsuario.objects.filter(
            activo=True, rol="admin_empresa", empresa__isnull=True
        ).count()
        contradicciones = PerfilUsuario.objects.filter(
            activo=True,
            empresa__empresa_operativa__isnull=False,
            user__empresa_principal__isnull=False,
        ).exclude(
            empresa__empresa_operativa=models.F("user__empresa_principal")
        ).count()
    except Exception:
        return []
    if sin_vinculo:
        warnings.append(Warning(
            f"Hay {sin_vinculo} EmpresaSaaS sin empresa operativa vinculada.",
            id="conduces.W001",
        ))
    if admins_sin_saas:
        warnings.append(Warning(
            f"Hay {admins_sin_saas} administradores activos sin EmpresaSaaS.",
            id="conduces.W002",
        ))
    if contradicciones:
        warnings.append(Warning(
            f"Hay {contradicciones} perfiles con vínculos empresariales contradictorios.",
            id="conduces.W003",
        ))
    return warnings
