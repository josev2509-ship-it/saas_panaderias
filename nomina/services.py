from .payroll_engine import process_payroll


def procesar_nomina(*, empresa, periodo, usuario=None):
    """Compatibilidad con integraciones certificadas previas."""
    return process_payroll(empresa=empresa, periodo=periodo, usuario=usuario)
