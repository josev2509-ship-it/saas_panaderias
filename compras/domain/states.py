TRANSITIONS = {
    "EN_EVALUACION": {"ACTIVO", "INACTIVO"},
    "ACTIVO": {"SUSPENDIDO", "BLOQUEADO", "INACTIVO"},
    "SUSPENDIDO": {"ACTIVO", "BLOQUEADO", "INACTIVO"},
    "BLOQUEADO": {"ACTIVO", "INACTIVO"},
    "INACTIVO": set(),
}


def puede_transicionar(desde, hacia):
    return hacia in TRANSITIONS.get(desde, set())
