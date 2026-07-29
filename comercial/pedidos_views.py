from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from conduces.services import obtener_empresa_usuario
from documentos.services import obtener_documentos

from .forms import DetallePedidoFormSet, PedidoForm, RechazoPedidoForm
from .models import Cliente, DetallePedido, Pedido
from .pedidos_services import calcular_linea, duplicar_pedido, recalcular_pedido, siguiente_numero, transicionar_pedido


def _empresa(request):
    empresa = obtener_empresa_usuario(request)
    if not empresa:
        messages.error(request, "Tu usuario no tiene una empresa asociada.")
        return None, redirect("inicio")
    return empresa, None


@login_required
def pedidos_dashboard(request):
    empresa, salida = _empresa(request)
    if salida: return salida
    hoy = timezone.localdate()
    qs = Pedido.objects.filter(empresa=empresa)
    contexto = {
        "empresa": empresa, "hoy": qs.filter(fecha_pedido=hoy).count(),
        "pendientes": qs.filter(estado=Pedido.Estado.PENDIENTE_APROBACION).count(),
        "aprobados": qs.filter(estado=Pedido.Estado.APROBADO, fecha_entrega__range=(hoy, hoy + timedelta(days=7))).count(),
        "urgentes": qs.filter(prioridad=Pedido.Prioridad.URGENTE).exclude(estado=Pedido.Estado.CANCELADO).count(),
        "cancelados": qs.filter(estado=Pedido.Estado.CANCELADO, fecha_actualizacion__year=hoy.year, fecha_actualizacion__month=hoy.month).count(),
        "totales": qs.exclude(estado=Pedido.Estado.CANCELADO).values("moneda").annotate(total=Sum("total")),
        "proximos": qs.exclude(estado=Pedido.Estado.CANCELADO).filter(fecha_entrega__gte=hoy).select_related("cliente")[:8],
        "alertas": qs.filter(
            Q(prioridad=Pedido.Prioridad.URGENTE, estado=Pedido.Estado.PENDIENTE_APROBACION)
            | Q(direccion_entrega__isnull=True)
            | Q(detalles__precio_unitario=0)
        ).distinct()[:10],
    }
    return render(request, "comercial/pedidos_dashboard.html", contexto)


@login_required
@permission_required("comercial.view_pedido", raise_exception=True)
def pedidos_lista(request):
    empresa, salida = _empresa(request)
    if salida: return salida
    qs = Pedido.objects.filter(empresa=empresa).select_related("cliente", "creado_por")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(numero__icontains=q) | Q(cliente__nombre_comercial__icontains=q) | Q(cliente__rnc_cedula__icontains=q))
    for campo in ("estado", "prioridad", "condicion_pago", "fecha_pedido", "fecha_entrega", "moneda", "creado_por"):
        valor = request.GET.get(campo, "")
        if valor: qs = qs.filter(**{campo: valor})
    totales = list(qs.values("moneda").annotate(total=Sum("total")))
    hoy = timezone.localdate()
    return render(request, "comercial/pedidos_lista.html", {
        "empresa": empresa, "pagina": Paginator(qs, 20).get_page(request.GET.get("page")),
        "q": q, "totales": totales, "estados": Pedido.Estado.choices,
        "prioridades": Pedido.Prioridad.choices, "condiciones": Cliente.CondicionPago.choices,
        "monedas": Pedido.Moneda.choices, "pedidos_hoy": qs.filter(fecha_pedido=hoy).count(),
        "creadores": Pedido.objects.filter(empresa=empresa, creado_por__isnull=False).values_list(
            "creado_por_id", "creado_por__username"
        ).distinct(),
        "pendientes": qs.filter(estado=Pedido.Estado.PENDIENTE_APROBACION).count(),
        "aprobados": qs.filter(estado=Pedido.Estado.APROBADO).count(),
        "urgentes": qs.filter(prioridad=Pedido.Prioridad.URGENTE).count(),
    })


def _guardar_pedido(request, empresa, pedido=None):
    if pedido and pedido.estado != Pedido.Estado.BORRADOR:
        messages.error(request, "Solo los pedidos en borrador pueden editarse.")
        return redirect("comercial:pedido_detalle", pk=pedido.pk)
    inicial = {}
    cliente_id = request.GET.get("cliente")
    if pedido is None and cliente_id:
        cliente = get_object_or_404(Cliente, pk=cliente_id, empresa=empresa)
        inicial = {
            "cliente": cliente, "condicion_pago": cliente.condicion_pago,
            "dias_credito": cliente.dias_credito, "lista_precio": cliente.lista_precio,
            "direccion_entrega": cliente.direcciones.filter(tipo="ENTREGA", activa=True, es_principal=True).first(),
            "contacto": cliente.contactos.filter(activo=True, es_principal=True).first(),
            "fecha_pedido": timezone.localdate(), "fecha_entrega": timezone.localdate(),
        }
    form = PedidoForm(request.POST or None, instance=pedido, empresa=empresa, initial=inicial)
    formset = DetallePedidoFormSet(
        request.POST or None, instance=pedido or Pedido(), prefix="detalles", form_kwargs={"empresa": empresa}
    )
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            objeto = form.save(commit=False)
            objeto.empresa = empresa
            objeto.actualizado_por = request.user
            if pedido is None:
                objeto.numero = siguiente_numero(empresa, objeto.fecha_pedido)
                objeto.creado_por = request.user
            objeto.full_clean()
            objeto.save()
            formset.instance = objeto
            lineas = formset.save(commit=False)
            for eliminada in formset.deleted_objects:
                eliminada.delete()
            for linea in lineas:
                linea.pedido = objeto
                if not linea.descripcion:
                    linea.descripcion = linea.producto.nombre
                linea.unidad_medida = linea.producto.unidad_medida
                calcular_linea(linea)
                linea.full_clean()
                linea.save()
            recalcular_pedido(objeto)
            registrar_evento(
                empresa=empresa, usuario=request.user, request=request, objeto=objeto, modulo="comercial",
                accion=EventoAuditoria.Accion.CREAR if pedido is None else EventoAuditoria.Accion.EDITAR,
                descripcion=f"Se {'creó' if pedido is None else 'editó'} el pedido {objeto.numero}.",
                datos_nuevos={"numero": objeto.numero, "total": str(objeto.total), "estado": objeto.estado},
            )
        messages.success(request, "Pedido guardado correctamente.")
        return redirect("comercial:pedido_detalle", pk=objeto.pk)
    return render(request, "comercial/pedido_form.html", {
        "empresa": empresa, "form": form, "formset": formset, "pedido": pedido,
    })


@login_required
@permission_required("comercial.add_pedido", raise_exception=True)
def pedido_crear(request):
    empresa, salida = _empresa(request)
    return salida or _guardar_pedido(request, empresa)


@login_required
@permission_required("comercial.change_pedido", raise_exception=True)
def pedido_editar(request, pk):
    empresa, salida = _empresa(request)
    if salida: return salida
    return _guardar_pedido(request, empresa, get_object_or_404(Pedido, pk=pk, empresa=empresa))


@login_required
@permission_required("comercial.view_pedido", raise_exception=True)
def pedido_detalle(request, pk):
    empresa, salida = _empresa(request)
    if salida: return salida
    pedido = get_object_or_404(Pedido.objects.select_related("cliente", "direccion_entrega", "contacto"), pk=pk, empresa=empresa)
    ct = ContentType.objects.get_for_model(pedido)
    return render(request, "comercial/pedido_detalle.html", {
        "empresa": empresa, "pedido": pedido,
        "documentos": obtener_documentos(pedido, empresa).select_related("tipo_documento", "creado_por"),
        "eventos": EventoAuditoria.objects.filter(empresa=empresa, content_type=ct, object_id=pedido.pk)[:20],
        "rechazo_form": RechazoPedidoForm(),
    })


def _accion(request, pk, accion):
    if request.method != "POST": return HttpResponseNotAllowed(["POST"])
    empresa, salida = _empresa(request)
    if salida: return salida
    pedido = get_object_or_404(Pedido, pk=pk, empresa=empresa)
    try:
        pedido = transicionar_pedido(
            pedido=pedido, empresa=empresa, usuario=request.user, accion=accion,
            comentario=request.POST.get("motivo", ""), request=request,
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, "Estado actualizado correctamente.")
    return redirect("comercial:pedido_detalle", pk=pedido.pk)


@login_required
def pedido_enviar_aprobacion(request, pk): return _accion(request, pk, "enviar")
@login_required
def pedido_aprobar(request, pk): return _accion(request, pk, "aprobar")
@login_required
def pedido_rechazar(request, pk): return _accion(request, pk, "rechazar")
@login_required
def pedido_reabrir(request, pk): return _accion(request, pk, "reabrir")
@login_required
def pedido_cancelar(request, pk): return _accion(request, pk, "cancelar")


@login_required
@permission_required("comercial.add_pedido", raise_exception=True)
def pedido_duplicar(request, pk):
    if request.method != "POST": return HttpResponseNotAllowed(["POST"])
    empresa, salida = _empresa(request)
    if salida: return salida
    origen = get_object_or_404(Pedido, pk=pk, empresa=empresa)
    nuevo = duplicar_pedido(origen=origen, empresa=empresa, usuario=request.user, request=request)
    messages.success(request, f"Pedido duplicado como {nuevo.numero}.")
    return redirect("comercial:pedido_detalle", pk=nuevo.pk)


def _programacion(request, semanal=False):
    empresa, salida = _empresa(request)
    if salida: return salida
    try: inicio = date.fromisoformat(request.GET.get("fecha", ""))
    except ValueError: inicio = timezone.localdate()
    fin = inicio + timedelta(days=6 if semanal else 0)
    pedidos = Pedido.objects.filter(empresa=empresa, fecha_entrega__range=(inicio, fin)).exclude(estado=Pedido.Estado.CANCELADO).select_related("cliente", "direccion_entrega").prefetch_related("detalles__producto")
    dias = []
    for offset in range((fin - inicio).days + 1):
        fecha = inicio + timedelta(days=offset)
        grupo = [p for p in pedidos if p.fecha_entrega == fecha]
        productos = defaultdict(Decimal)
        for pedido in grupo:
            for linea in pedido.detalles.all(): productos[linea.descripcion] += linea.cantidad
        dias.append({
            "fecha": fecha, "pedidos": grupo, "productos": productos.items(),
            "aprobados": sum(p.estado == Pedido.Estado.APROBADO for p in grupo),
            "pendientes": sum(p.estado == Pedido.Estado.PENDIENTE_APROBACION for p in grupo),
            "lineas": sum(p.detalles.count() for p in grupo),
            "totales": [(m, sum((p.total for p in grupo if p.moneda == m), 0)) for m, _ in Pedido.Moneda.choices],
            "alertas": [
                (p, motivo) for p in grupo for motivo in (
                    ["Urgente pendiente de aprobación"] if p.prioridad == Pedido.Prioridad.URGENTE and p.estado == Pedido.Estado.PENDIENTE_APROBACION else []
                ) + (["Sin dirección de entrega"] if not p.direccion_entrega_id else [])
                  + (["Contiene precio cero"] if any(d.precio_unitario == 0 for d in p.detalles.all()) else [])
                  + (["Descuento superior al permitido"] if any(d.porcentaje_descuento > p.cliente.descuento_maximo for d in p.detalles.all()) else [])
                  + (["Fecha vencida sin estado final"] if p.fecha_entrega < timezone.localdate() and p.estado not in {Pedido.Estado.ENTREGADO, Pedido.Estado.FACTURADO, Pedido.Estado.CANCELADO} else [])
            ],
        })
    return render(request, "comercial/programacion.html", {"empresa": empresa, "dias": dias, "semanal": semanal, "inicio": inicio})


@login_required
@permission_required("comercial.view_pedido", raise_exception=True)
def programacion_diaria(request): return _programacion(request)
@login_required
@permission_required("comercial.view_pedido", raise_exception=True)
def programacion_semanal(request): return _programacion(request, True)
