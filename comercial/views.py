from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from conduces.services import obtener_empresa_usuario
from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from .forms import ClienteForm, ContactoClienteForm, DireccionClienteForm
from .models import Cliente, ContactoCliente, DireccionCliente


def _empresa(request):
    empresa = obtener_empresa_usuario(request)
    if not empresa:
        messages.error(request, "Tu usuario no tiene una empresa asociada. Contacta al administrador.")
        return None, redirect("inicio")
    return empresa, None


@login_required
def dashboard(request):
    empresa, salida = _empresa(request)
    if salida:
        return salida
    qs = Cliente.objects.filter(empresa=empresa)
    return render(request, "comercial/dashboard.html", {
        "empresa": empresa, "total": qs.count(),
        "activos": qs.filter(estado=Cliente.Estado.ACTIVO).count(),
        "credito": qs.filter(condicion_pago=Cliente.CondicionPago.CREDITO).count(),
        "bloqueados": qs.filter(estado=Cliente.Estado.BLOQUEADO_CREDITO).count(),
        "recientes": qs.order_by("-fecha_creacion")[:5],
    })


@login_required
def clientes_lista(request):
    empresa, salida = _empresa(request)
    if salida:
        return salida
    base = Cliente.objects.filter(empresa=empresa)
    qs = base
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(codigo__icontains=q) | Q(nombre_comercial__icontains=q)
                       | Q(razon_social__icontains=q) | Q(rnc_cedula__icontains=q)
                       | Q(telefono__icontains=q))
    filtros = {k: request.GET.get(k, "") for k in ("tipo_cliente", "estado", "condicion_pago")}
    for campo, valor in filtros.items():
        if valor:
            qs = qs.filter(**{campo: valor})
    return render(request, "comercial/clientes_lista.html", {
        "empresa": empresa, "pagina": Paginator(qs, 20).get_page(request.GET.get("page")),
        "q": q, "filtros": filtros, "tipos": Cliente.Tipo.choices,
        "estados": Cliente.Estado.choices, "condiciones": Cliente.CondicionPago.choices,
        "total": base.count(), "activos": base.filter(estado=Cliente.Estado.ACTIVO).count(),
        "credito": base.filter(condicion_pago=Cliente.CondicionPago.CREDITO).count(),
        "bloqueados": base.filter(estado=Cliente.Estado.BLOQUEADO_CREDITO).count(),
    })


def _form_cliente(request, empresa, cliente=None):
    anteriores = None
    if cliente is not None:
        anteriores = {
            "nombre_comercial": cliente.nombre_comercial,
            "razon_social": cliente.razon_social,
            "condicion_pago": cliente.condicion_pago,
            "dias_credito": cliente.dias_credito,
            "limite_credito": str(cliente.limite_credito),
            "estado": cliente.estado,
        }
    form = ClienteForm(request.POST or None, instance=cliente)
    if request.method == "POST" and form.is_valid():
        objeto = form.save(commit=False)
        objeto.empresa = empresa
        if cliente is None:
            objeto.creado_por = request.user
        objeto.save()
        nuevos = {
            "nombre_comercial": objeto.nombre_comercial,
            "razon_social": objeto.razon_social,
            "condicion_pago": objeto.condicion_pago,
            "dias_credito": objeto.dias_credito,
            "limite_credito": str(objeto.limite_credito),
            "estado": objeto.estado,
        }
        registrar_evento(
            empresa=empresa, usuario=request.user, request=request, objeto=objeto,
            modulo="comercial", accion=(
                EventoAuditoria.Accion.CREAR if cliente is None else EventoAuditoria.Accion.EDITAR
            ),
            descripcion=(
                f"Se creó el cliente «{objeto.nombre_comercial}»."
                if cliente is None else f"Se actualizó el cliente «{objeto.nombre_comercial}»."
            ),
            datos_anteriores=anteriores, datos_nuevos=nuevos,
        )
        messages.success(request, "Cliente guardado correctamente.")
        return redirect("comercial:cliente_detalle", pk=objeto.pk)
    return render(request, "comercial/cliente_form.html", {
        "empresa": empresa, "form": form, "cliente": cliente,
    })


@login_required
def cliente_crear(request):
    empresa, salida = _empresa(request)
    return salida or _form_cliente(request, empresa)


@login_required
def cliente_editar(request, pk):
    empresa, salida = _empresa(request)
    if salida:
        return salida
    return _form_cliente(request, empresa, get_object_or_404(Cliente, pk=pk, empresa=empresa))


@login_required
def cliente_detalle(request, pk):
    empresa, salida = _empresa(request)
    if salida:
        return salida
    cliente = get_object_or_404(
        Cliente.objects.prefetch_related("direcciones", "contactos"), pk=pk, empresa=empresa
    )
    from auditoria.models import EventoAuditoria
    from documentos.services import obtener_documentos
    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(cliente)
    documentos = obtener_documentos(cliente, empresa).select_related("tipo_documento", "creado_por")
    eventos = EventoAuditoria.objects.filter(
        empresa=empresa, content_type=ct, object_id=cliente.pk
    ).select_related("usuario")[:30]
    return render(request, "comercial/cliente_detalle.html", {
        "empresa": empresa, "cliente": cliente, "documentos": documentos, "eventos": eventos,
    })


@login_required
def cliente_cambiar_estado(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    empresa, salida = _empresa(request)
    if salida:
        return salida
    cliente = get_object_or_404(Cliente, pk=pk, empresa=empresa)
    estado = request.POST.get("estado")
    estados = dict(Cliente.Estado.choices)
    if estado not in estados:
        messages.error(request, "El estado seleccionado no es válido.")
    else:
        estado_anterior = cliente.estado
        cliente.estado = estado
        cliente.save(update_fields=["estado", "fecha_actualizacion"])
        registrar_evento(
            empresa=empresa, usuario=request.user, request=request, objeto=cliente,
            modulo="comercial", accion=EventoAuditoria.Accion.CAMBIAR_ESTADO,
            descripcion=f"Se cambió el estado del cliente de {estados[estado_anterior]} a {estados[estado]}.",
            datos_anteriores={"estado": estado_anterior}, datos_nuevos={"estado": estado},
        )
        messages.success(request, f"Estado actualizado a {estados[estado]}.")
    return redirect("comercial:cliente_detalle", pk=cliente.pk)


def _form_relacion(request, model, form_class, template, cliente_pk=None, pk=None):
    empresa, salida = _empresa(request)
    if salida:
        return salida
    if pk:
        objeto = get_object_or_404(model, pk=pk, cliente__empresa=empresa)
        cliente = objeto.cliente
    else:
        objeto = None
        cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=empresa)
    form = form_class(request.POST or None, instance=objeto)
    if request.method == "POST" and form.is_valid():
        objeto = form.save(commit=False)
        objeto.cliente = cliente
        objeto.save()
        messages.success(request, "Información guardada correctamente.")
        return redirect("comercial:cliente_detalle", pk=cliente.pk)
    return render(request, template, {
        "empresa": empresa, "form": form, "cliente": cliente, "objeto": objeto,
    })


@login_required
def direccion_crear(request, cliente_pk):
    return _form_relacion(request, DireccionCliente, DireccionClienteForm, "comercial/direccion_form.html", cliente_pk=cliente_pk)


@login_required
def direccion_editar(request, pk):
    return _form_relacion(request, DireccionCliente, DireccionClienteForm, "comercial/direccion_form.html", pk=pk)


@login_required
def contacto_crear(request, cliente_pk):
    return _form_relacion(request, ContactoCliente, ContactoClienteForm, "comercial/contacto_form.html", cliente_pk=cliente_pk)


@login_required
def contacto_editar(request, pk):
    return _form_relacion(request, ContactoCliente, ContactoClienteForm, "comercial/contacto_form.html", pk=pk)
