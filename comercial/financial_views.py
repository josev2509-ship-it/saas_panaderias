from decimal import Decimal

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from core.application.operation_context import OperationContext
from conduces.services import obtener_empresa_usuario
from comercial.application.financial_integration import (
    anular_factura_sin_cobros, contabilizar_factura_emitida,
    desembolsar_factoring, emitir_nota_credito_integrada,
    emitir_nota_debito_integrada, integrar_cobro, revertir_cobro_integral,
)
from comercial.application.o2c_full import aplicar_cobro, emitir_factura, registrar_cobro, solicitar_factoring
from comercial.application.o2c_full import avanzar_factoring
from comercial.application.financial_exports import exportar
from catalogos.models import MonedaEmpresa
from comercial.models import Cliente, CuentaPorCobrar
from tesoreria.models import ConciliacionBancaria
from tesoreria.services import conciliar_linea, desconciliar_linea


def _context(request):
    return OperationContext(empresa=obtener_empresa_usuario(request), usuario=request.user, request=request, clave_idempotente=request.headers.get("Idempotency-Key", ""))


def _ok(value):
    if hasattr(value, "__dict__"):
        value = {k: str(v) for k, v in vars(value).items()}
    return JsonResponse(value if isinstance(value, dict) else {"id": value.pk})


def financial_action(permission):
    def decorate(view):
        return require_POST(login_required(permission_required(permission, raise_exception=True)(view)))
    return decorate


@financial_action("comercial.change_facturaventa")
def factura_emitir(request, pk): return _ok(emitir_factura(context=_context(request), pk=pk))

@financial_action("contabilidad.contabilizar_asiento")
def factura_contabilizar(request, pk): return _ok(contabilizar_factura_emitida(context=_context(request), factura_id=pk))

@financial_action("comercial.add_notacreditoventa")
def nota_credito(request, pk): return _ok(emitir_nota_credito_integrada(context=_context(request), factura_id=pk, monto=Decimal(request.POST["monto"]), motivo=request.POST["motivo"], ncf=request.POST.get("ncf", "")))

@financial_action("comercial.add_notadebitoventa")
def nota_debito(request, pk): return _ok(emitir_nota_debito_integrada(context=_context(request), factura_id=pk, monto=Decimal(request.POST["monto"]), motivo=request.POST["motivo"], ncf=request.POST.get("ncf", "")))

@financial_action("comercial.add_recibocobro")
def cobro_registrar(request):
    context = _context(request); cliente = Cliente.objects.get(pk=request.POST["cliente_id"], empresa=context.empresa); moneda = MonedaEmpresa.objects.get(pk=request.POST["moneda_id"], empresa=context.empresa)
    return _ok(registrar_cobro(context=context, cliente=cliente, moneda=moneda, monto=Decimal(request.POST["monto"]), metodo=request.POST["metodo"], referencia=request.POST.get("referencia", ""), tasa_cambio=request.POST.get("tasa_cambio")))

@financial_action("comercial.change_recibocobro")
def cobro_aplicar(request, pk): return _ok(aplicar_cobro(context=_context(request), recibo_id=pk, cuenta_id=request.POST["cuenta_id"], monto=Decimal(request.POST["monto"]), monto_cuenta=request.POST.get("monto_cuenta")))

@financial_action("comercial.revertir_cobro")
def cobro_revertir(request, pk): return _ok(revertir_cobro_integral(context=_context(request), recibo_id=pk, motivo=request.POST["motivo"]))

@financial_action("comercial.add_cesionfactoring")
def factoring_solicitar(request):
    context = _context(request); cuenta = CuentaPorCobrar.objects.get(pk=request.POST["cuenta_id"], empresa=context.empresa)
    return _ok(solicitar_factoring(context=context, cuenta_id=cuenta.pk, factor=request.POST["factor"], porcentaje=Decimal(request.POST["porcentaje"]), monto=request.POST.get("monto")))

@financial_action("comercial.change_cesionfactoring")
def factoring_desembolsar(request, pk): return _ok(desembolsar_factoring(context=_context(request), cesion_id=pk, cuenta_bancaria_id=request.POST["cuenta_bancaria_id"], comision=request.POST.get("comision", 0), costo_financiero=request.POST.get("costo_financiero", 0), retencion=request.POST.get("retencion", 0), referencia=request.POST.get("referencia", "")))

@financial_action("comercial.gestionar_factoring_o2c")
def factoring_aprobar(request, pk): return _ok(avanzar_factoring(context=_context(request), pk=pk, estado="APROBADA"))

@financial_action("tesoreria.change_conciliacionbancaria")
def conciliacion_aplicar(request, pk):
    context=_context(request); conciliacion=ConciliacionBancaria.objects.get(pk=pk,empresa=context.empresa)
    return _ok(conciliar_linea(context=context,conciliacion=conciliacion,linea_id=request.POST["linea_id"],movimiento_id=request.POST["movimiento_id"],tipo="MANUAL"))

@financial_action("tesoreria.change_conciliacionbancaria")
def conciliacion_revertir(request, pk): return _ok(desconciliar_linea(context=_context(request),linea_id=pk,motivo=request.POST["motivo"]))

@financial_action("comercial.exportar_cxc")
def exportacion_financiera(request, tipo, formato):
    dto=exportar(context=_context(request),tipo=tipo,formato=formato)
    response=HttpResponse(dto.contenido,content_type=dto.mime);response["Content-Disposition"]=f'attachment; filename="{dto.nombre}"';return response

@financial_action("contabilidad.contabilizar_asiento")
def reintentar_integracion(request, pk): return _ok(contabilizar_factura_emitida(context=_context(request),factura_id=pk))

@financial_action("comercial.change_facturaventa")
def factura_anular(request, pk): return _ok(anular_factura_sin_cobros(context=_context(request), factura_id=pk, motivo=request.POST["motivo"]))

@financial_action("comercial.change_recibocobro")
def cobro_integrar(request, pk): return _ok(integrar_cobro(context=_context(request), recibo_id=pk, cuenta_bancaria_id=request.POST.get("cuenta_bancaria_id"), caja_id=request.POST.get("caja_id")))
