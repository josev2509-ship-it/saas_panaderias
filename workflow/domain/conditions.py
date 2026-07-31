from decimal import Decimal
from .exceptions import WorkflowConfigurationError

def condition_value(condition):
    return {"TEXTO":condition.valor_texto,"LISTA":[x.strip() for x in condition.valor_texto.split(",") if x.strip()],"DECIMAL":condition.valor_decimal,"ENTERO":condition.valor_entero,"BOOLEANO":condition.valor_booleano,"FECHA":condition.valor_fecha}[condition.valor_tipo]

def evaluate_condition(condition,context,allowed_fields):
    if condition.campo not in allowed_fields: raise WorkflowConfigurationError(f"Campo de condición no permitido: {condition.campo}.")
    actual=context.get(condition.campo); op=condition.operador
    if op=="ES_NULO": return actual is None
    if op=="NO_ES_NULO": return actual is not None
    expected=condition_value(condition)
    operations={"IGUAL":lambda:a==expected,"DIFERENTE":lambda:a!=expected,"MAYOR_QUE":lambda:a>expected,"MAYOR_O_IGUAL":lambda:a>=expected,"MENOR_QUE":lambda:a<expected,"MENOR_O_IGUAL":lambda:a<=expected,"EN_LISTA":lambda:a in expected,"NO_EN_LISTA":lambda:a not in expected,"CONTIENE":lambda:expected in a,"NO_CONTIENE":lambda:expected not in a}
    try:
        a=actual; return bool(operations[op]())
    except (KeyError,TypeError,ValueError) as exc: raise WorkflowConfigurationError(f"No se pudo evaluar {condition.campo} con {op}.") from exc

def rule_matches(rule,context,allowed_fields):
    groups={}
    for c in rule.condiciones.filter(activa=True): groups.setdefault(c.agrupador,[]).append(evaluate_condition(c,context,allowed_fields))
    return not groups or any(all(values) for values in groups.values())
