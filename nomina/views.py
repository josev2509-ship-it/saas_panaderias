import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from conduces.services import obtener_empresa_usuario
from rrhh.models import HistorialLaboral

from .documents import payroll_pdf, payroll_xlsx, payslip_pdf, payslips_zip, settlement_pdf
from .forms import ConceptoForm, LiquidacionForm, NovedadForm, PeriodoForm, PlantillaDocumentoForm
from .labor_settlement import calculate_settlement
from .models import ConceptoNomina, DetalleNominaEmpleado, HistorialNomina, LiquidacionLaboral, Nomina, NovedadNomina, PeriodoNomina, PlantillaDocumentoRRHH
from .services import procesar_nomina


def _e(request):
    return obtener_empresa_usuario(request)


def _audit(request, obj, description, before=None, after=None):
    return registrar_evento(empresa=_e(request), usuario=request.user, request=request, objeto=obj, modulo="nomina", accion=EventoAuditoria.Accion.EDITAR if before else EventoAuditoria.Accion.CREAR, descripcion=description, datos_anteriores=before, datos_nuevos=after)


@login_required
@permission_required("nomina.view_nomina", raise_exception=True)
def dashboard(request):
    periods = PeriodoNomina.objects.filter(empresa=_e(request)).select_related("tipo").order_by("-desde")
    payrolls = Nomina.objects.filter(empresa=_e(request)).select_related("periodo__tipo").order_by("-periodo__desde")
    return render(request, "nomina/dashboard.html", {"periodos": periods, "nominas": payrolls})


@login_required
@permission_required("nomina.add_periodonomina", raise_exception=True)
@transaction.atomic
def periodo_crear(request):
    form = PeriodoForm(request.POST or None, empresa=_e(request))
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.empresa = _e(request)
        obj.save()
        _audit(request, obj, "Período de nómina creado.")
        return redirect("nomina:dashboard")
    return render(request, "rrhh/form.html", {"form": form, "titulo": "Crear período de nómina"})


@login_required
@require_POST
@permission_required("nomina.add_nomina", raise_exception=True)
@transaction.atomic
def calcular(request, periodo_id):
    period = get_object_or_404(PeriodoNomina, empresa=_e(request), pk=periodo_id)
    try:
        payroll = procesar_nomina(empresa=_e(request), periodo=period, usuario=request.user)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("nomina:dashboard")
    _audit(request, payroll, "Nómina RD calculada o recalculada.", after={"total_neto": str(payroll.total_neto), "parametro": payroll.snapshot_reglas.get("version")})
    messages.success(request, "Nómina calculada con TSS, ISR y aportes patronales.")
    return redirect("nomina:detalle", payroll.pk)


@login_required
@permission_required("nomina.view_nomina", raise_exception=True)
def detalle(request, pk):
    payroll = get_object_or_404(Nomina.objects.select_related("periodo__tipo"), empresa=_e(request), pk=pk)
    details = payroll.detalles.select_related("empleado__puesto").order_by("empleado__apellidos")
    return render(request, "nomina/detalle.html", {"nomina": payroll, "detalles": details})


@login_required
@permission_required("nomina.view_nomina", raise_exception=True)
def empleado_detalle(request, pk, detalle_id):
    payroll = get_object_or_404(Nomina, empresa=_e(request), pk=pk)
    detail = get_object_or_404(DetalleNominaEmpleado.objects.select_related("empleado__puesto", "nomina__periodo"), nomina=payroll, pk=detalle_id)
    return render(request, "nomina/empleado_detalle.html", {"nomina": payroll, "detalle": detail, "lineas": detail.lineas.select_related("concepto")})


@login_required
@require_POST
@permission_required("nomina.change_nomina", raise_exception=True)
@transaction.atomic
def estado(request, pk):
    obj = get_object_or_404(Nomina, empresa=_e(request), pk=pk)
    new = request.POST.get("estado", "").upper()
    transitions = {"CALCULADA": {"APROBADA"}, "APROBADA": {"CERRADA", "PAGADA"}}
    if new not in transitions.get(obj.estado, set()):
        return HttpResponse("Transición no permitida.", status=400)
    previous = obj.estado
    obj.estado = new
    obj.save(update_fields=["estado"])
    HistorialNomina.objects.create(nomina=obj, estado_anterior=previous, estado_nuevo=new)
    _audit(request, obj, "Estado de nómina actualizado.", {"estado": previous}, {"estado": new})
    return redirect("nomina:detalle", obj.pk)


@login_required
@permission_required("nomina.view_conceptonomina", raise_exception=True)
def conceptos(request):
    return render(request, "rrhh/workforce_list.html", {"titulo": "Conceptos de nómina", "objetos": ConceptoNomina.objects.filter(empresa=_e(request)).order_by("codigo"), "tipo": "conceptos"})


@login_required
@permission_required("nomina.add_conceptonomina", raise_exception=True)
def concepto_crear(request):
    form = ConceptoForm(request.POST or None, empresa=_e(request))
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.empresa = _e(request)
        obj.save()
        _audit(request, obj, "Concepto de nómina creado.")
        return redirect("nomina:conceptos")
    return render(request, "rrhh/form.html", {"form": form, "titulo": "Crear concepto de nómina"})


@login_required
@permission_required("nomina.add_novedadnomina", raise_exception=True)
def novedad_crear(request):
    form = NovedadForm(request.POST or None, empresa=_e(request))
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.empresa, obj.estado = _e(request), "APROBADA"
        obj.save()
        _audit(request, obj, "Novedad de ingreso/descuento aprobada.")
        messages.success(request, "Novedad registrada. Recalcule la nómina abierta para aplicarla.")
        return redirect("nomina:dashboard")
    return render(request, "rrhh/form.html", {"form": form, "titulo": "Registrar ingreso o descuento"})


@login_required
@permission_required("nomina.view_liquidacionlaboral", raise_exception=True)
def prestaciones(request):
    objects = LiquidacionLaboral.objects.filter(empresa=_e(request)).select_related("empleado").order_by("-fecha")
    return render(request, "nomina/prestaciones.html", {"objetos": objects})


@login_required
@permission_required("nomina.add_liquidacionlaboral", raise_exception=True)
@transaction.atomic
def prestacion_crear(request):
    form = LiquidacionForm(request.POST or None, empresa=_e(request))
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.empresa, obj.fecha = _e(request), form.cleaned_data["fecha_salida"]
        obj.save()
        obj = calculate_settlement(settlement=obj)
        HistorialLaboral.objects.create(empleado=obj.empleado, accion="PRESTACIONES_CALCULADAS", snapshot={"liquidacion": obj.pk, "total": str(obj.total), "estado": obj.estado})
        _audit(request, obj, "Prestaciones laborales calculadas automáticamente.", after={"total": str(obj.total), "revision": obj.requiere_revision})
        return redirect("nomina:prestacion_detalle", obj.pk)
    return render(request, "rrhh/form.html", {"form": form, "titulo": "Calcular prestaciones laborales"})


@login_required
@require_POST
@permission_required("nomina.change_liquidacionlaboral", raise_exception=True)
def prestacion_recalcular(request, pk):
    obj = get_object_or_404(LiquidacionLaboral, empresa=_e(request), pk=pk)
    try:
        calculate_settlement(settlement=obj)
        messages.success(request, "Prestaciones recalculadas.")
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    return redirect("nomina:prestacion_detalle", pk)


@login_required
@permission_required("nomina.view_liquidacionlaboral", raise_exception=True)
def prestacion_detalle(request, pk):
    obj = get_object_or_404(LiquidacionLaboral.objects.select_related("empleado"), empresa=_e(request), pk=pk)
    return render(request, "nomina/prestacion_detalle.html", {"obj": obj, "desglose": obj.prestaciones.all()})


def _download(content, content_type, filename, inline=False):
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'{"inline" if inline else "attachment"}; filename="{filename}"'
    return response


@login_required
@permission_required("nomina.view_nomina", raise_exception=True)
def exportar(request, pk):
    obj = get_object_or_404(Nomina, empresa=_e(request), pk=pk)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{obj.numero}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Empleado", "Bruto", "AFP", "SFS", "ISR", "Otros descuentos", "Aportes patronales", "Neto"])
    for d in obj.detalles.select_related("empleado"):
        writer.writerow([d.empleado.codigo, d.ingresos, d.afp_empleado, d.sfs_empleado, d.isr, d.otros_descuentos, d.aportes, d.neto])
    return response


@login_required
@permission_required("nomina.view_nomina", raise_exception=True)
def exportar_excel(request, pk):
    obj = get_object_or_404(Nomina.objects.select_related("periodo"), empresa=_e(request), pk=pk)
    return _download(payroll_xlsx(obj), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"{obj.numero}.xlsx")


@login_required
@permission_required("nomina.view_nomina", raise_exception=True)
def nomina_pdf(request, pk):
    obj = get_object_or_404(Nomina.objects.select_related("periodo"), empresa=_e(request), pk=pk)
    return _download(payroll_pdf(obj), "application/pdf", f"{obj.numero}.pdf", inline=request.GET.get("download") != "1")


@login_required
@permission_required("nomina.view_nomina", raise_exception=True)
def volante_pdf(request, pk, detalle_id):
    detail = get_object_or_404(DetalleNominaEmpleado.objects.select_related("nomina__empresa", "nomina__periodo", "empleado"), pk=detalle_id, nomina_id=pk, nomina__empresa=_e(request))
    return _download(payslip_pdf(detail), "application/pdf", f"volante-{detail.empleado.codigo}-{detail.nomina.numero}.pdf", inline=request.GET.get("download") != "1")


@login_required
@permission_required("nomina.view_nomina", raise_exception=True)
def volantes_zip(request, pk):
    obj = get_object_or_404(Nomina.objects.select_related("periodo"), empresa=_e(request), pk=pk)
    return _download(payslips_zip(obj), "application/zip", f"volantes-{obj.numero}.zip")


@login_required
@permission_required("nomina.view_liquidacionlaboral", raise_exception=True)
def prestacion_pdf(request, pk):
    obj = get_object_or_404(LiquidacionLaboral.objects.select_related("empleado"), empresa=_e(request), pk=pk)
    return _download(settlement_pdf(obj), "application/pdf", f"prestaciones-{obj.empleado.codigo}.pdf", inline=request.GET.get("download") != "1")


@login_required
@permission_required("nomina.view_liquidacionlaboral", raise_exception=True)
def liquidacion_carta(request, pk):
    obj = get_object_or_404(LiquidacionLaboral.objects.select_related("empleado"), empresa=_e(request), pk=pk)
    return _download(settlement_pdf(obj, letter=True), "application/pdf", f"carta-liquidacion-{obj.empleado.codigo}.pdf", inline=request.GET.get("download") != "1")


@login_required
@permission_required("nomina.view_plantilladocumentorrhh", raise_exception=True)
def plantillas(request):
    return render(request, "nomina/plantillas.html", {"objetos": PlantillaDocumentoRRHH.objects.filter(empresa=_e(request)).order_by("tipo")})


@login_required
@permission_required("nomina.change_plantilladocumentorrhh", raise_exception=True)
def plantilla_editar(request, pk=None):
    obj = get_object_or_404(PlantillaDocumentoRRHH, empresa=_e(request), pk=pk) if pk else None
    form = PlantillaDocumentoForm(request.POST or None, instance=obj, empresa=_e(request))
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.empresa = _e(request)
        item.save()
        _audit(request, item, "Plantilla documental RRHH actualizada.")
        return redirect("nomina:plantillas")
    return render(request, "rrhh/form.html", {"form": form, "titulo": "Plantilla documental RRHH"})
