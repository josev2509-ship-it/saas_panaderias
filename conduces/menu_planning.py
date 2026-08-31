from dataclasses import dataclass
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from auditoria.services import registrar_evento

from .models import (
    AsignacionProgramaCentro,
    CalendarioEscolar,
    DiaCalendarioEscolar,
    ExcepcionProgramacionMenu,
    ItemCicloMenu,
    PerfilUsuario,
    ProgramacionMenuEscolar,
    VersionProgramaMenu,
)


def puede_gestionar_planificacion(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.has_perm("conduces.change_programamenu"):
        return True
    return PerfilUsuario.objects.filter(user=user, rol="admin_empresa", activo=True).exists()


def exigir_gestion_planificacion(user):
    if not puede_gestionar_planificacion(user):
        raise PermissionDenied


def contar_docencia_regular(calendario):
    return sum(
        1
        for dia in calendario.dias.filter(clasificacion=DiaCalendarioEscolar.Clasificacion.DOCENCIA).only("fecha")
        if dia.fecha.weekday() < 5
    )


@transaction.atomic
def activar_calendario(calendario, *, usuario, request=None, forzar=False, justificacion=""):
    exigir_gestion_planificacion(usuario)
    calendario = CalendarioEscolar.objects.select_for_update().get(pk=calendario.pk, empresa=calendario.empresa)
    detectados = contar_docencia_regular(calendario)
    esperados = calendario.dias_docencia_oficiales
    if detectados != esperados and not (forzar and justificacion.strip()):
        raise ValidationError(
            f"Dias oficiales: {esperados}. Dias calculados: {detectados}. "
            f"Diferencia: {detectados - esperados}. Revise las fechas antes de activar."
        )
    if calendario.dias.filter(clasificacion=DiaCalendarioEscolar.Clasificacion.REQUIERE_REVISION).exists():
        raise ValidationError("Existen fechas que requieren revision.")

    calendario.estado = CalendarioEscolar.Estado.ACTIVO
    calendario.diferencia_justificada = justificacion.strip() if detectados != esperados else ""
    calendario.activado_por = usuario
    calendario.activado_en = timezone.now()
    calendario.save(update_fields=("estado", "diferencia_justificada", "activado_por", "activado_en", "actualizado_en"))
    registrar_evento(
        empresa=calendario.empresa,
        accion="CAMBIAR_ESTADO",
        modulo="planificacion_menu",
        descripcion=f"Calendario {calendario} activado ({detectados}/{esperados} dias regulares).",
        usuario=usuario,
        objeto=calendario,
        request=request,
        datos_anteriores={"estado": CalendarioEscolar.Estado.EN_REVISION},
        datos_nuevos={"estado": CalendarioEscolar.Estado.ACTIVO, "detectados": detectados, "esperados": esperados},
    )
    return calendario


def semana_ciclo(version, fecha):
    semanas_transcurridas = (fecha - version.fecha_ancla_ciclo).days // 7
    return ((version.semana_inicial - 1 + semanas_transcurridas) % version.semanas_ciclo) + 1


def version_vigente(programa, fecha):
    return (
        programa.versiones.filter(
            estado=VersionProgramaMenu.Estado.ACTIVA,
            vigente_desde__lte=fecha,
        )
        .filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=fecha))
        .order_by("-vigente_desde", "-id")
        .first()
    )


@dataclass(frozen=True)
class FilaProgramacion:
    fecha: object
    dia_semana: int
    semana: int | None
    version: VersionProgramaMenu | None
    item: ItemCicloMenu | None
    producto: str
    estado: str


def previsualizar_asignacion(asignacion, calendario, fecha_inicio=None, fecha_fin=None):
    if asignacion.centro.empresa_id != calendario.empresa_id or asignacion.programa.empresa_id != calendario.empresa_id:
        raise ValidationError("Calendario, centro y programa deben pertenecer a la misma empresa.")

    inicio = max(fecha_inicio or calendario.inicio_docencia, calendario.inicio_docencia, asignacion.vigente_desde)
    limites = [fecha_fin or calendario.fin_docencia, calendario.fin_docencia]
    if asignacion.vigente_hasta:
        limites.append(asignacion.vigente_hasta)
    fin = min(limites)
    dias_calendario = {dia.fecha: dia for dia in calendario.dias.filter(fecha__range=(inicio, fin))}
    filas = []
    fecha = inicio
    dias_entrega = set(asignacion.dias_entrega)

    while fecha <= fin:
        dia_semana = fecha.weekday()
        if dia_semana in dias_entrega:
            version = version_vigente(asignacion.programa, fecha)
            semana = semana_ciclo(version, fecha) if version else None
            item = (
                version.items.filter(semana=semana, dia_semana=dia_semana).first()
                if version and semana is not None
                else None
            )
            dia = dias_calendario.get(fecha)
            if not dia or dia.clasificacion != DiaCalendarioEscolar.Clasificacion.DOCENCIA:
                estado = ProgramacionMenuEscolar.Estado.SIN_DOCENCIA
                producto = ""
            elif not version or not item:
                estado = ProgramacionMenuEscolar.Estado.NO_PROGRAMADO
                producto = ""
            elif not item.es_suministrado:
                estado = ProgramacionMenuEscolar.Estado.NO_SUMINISTRADO
                producto = ""
            else:
                estado = ProgramacionMenuEscolar.Estado.PROGRAMADO
                producto = item.producto
            filas.append(FilaProgramacion(fecha, dia_semana, semana, version, item, producto, estado))
        fecha += timedelta(days=1)
    return filas


@transaction.atomic
def materializar_programacion(asignacion, calendario, *, usuario, fecha_inicio=None, fecha_fin=None, request=None):
    exigir_gestion_planificacion(usuario)
    if calendario.estado != CalendarioEscolar.Estado.ACTIVO:
        raise ValidationError("El calendario debe estar activo antes de generar programacion.")
    filas = previsualizar_asignacion(asignacion, calendario, fecha_inicio, fecha_fin)
    resultados = []
    for fila in filas:
        if not fila.version:
            continue
        existente = ProgramacionMenuEscolar.objects.filter(asignacion=asignacion, fecha=fila.fecha).first()
        if existente and (existente.bloqueada or existente.confirmada):
            resultados.append(existente)
            continue
        valores = {
            "empresa": calendario.empresa,
            "calendario": calendario,
            "centro": asignacion.centro,
            "dia_semana": fila.dia_semana,
            "semana_ciclo": fila.semana,
            "programa": asignacion.programa,
            "version": fila.version,
            "item_ciclo": fila.item,
            "producto": fila.producto,
            "programa_snapshot": asignacion.programa.nombre,
            "version_snapshot": fila.version.nombre,
            "modalidad_snapshot": asignacion.modalidad,
            "estado": fila.estado,
            "creada_por": usuario,
        }
        objeto, _ = ProgramacionMenuEscolar.objects.update_or_create(
            asignacion=asignacion,
            fecha=fila.fecha,
            defaults=valores,
        )
        resultados.append(objeto)
    registrar_evento(
        empresa=calendario.empresa,
        accion="CREAR",
        modulo="planificacion_menu",
        descripcion=f"Programacion materializada para {asignacion.centro}: {len(resultados)} fechas.",
        usuario=usuario,
        objeto=asignacion,
        request=request,
        datos_nuevos={"filas": len(resultados)},
    )
    return resultados


@transaction.atomic
def aplicar_excepcion(programacion, *, usuario, estado_nuevo, producto_nuevo="", motivo="", request=None):
    exigir_gestion_planificacion(usuario)
    programacion = ProgramacionMenuEscolar.objects.select_for_update().get(
        pk=programacion.pk,
        empresa=programacion.empresa,
    )
    if programacion.bloqueada:
        raise ValidationError("La programacion esta bloqueada por uso documental.")
    if not motivo.strip():
        raise ValidationError("Debe indicar el motivo del ajuste.")
    excepcion = ExcepcionProgramacionMenu.objects.create(
        programacion=programacion,
        estado_anterior=programacion.estado,
        estado_nuevo=estado_nuevo,
        producto_anterior=programacion.producto,
        producto_nuevo=producto_nuevo.strip(),
        motivo=motivo.strip(),
        usuario=usuario,
    )
    programacion.estado = estado_nuevo
    programacion.producto = producto_nuevo.strip()
    programacion.save(update_fields=("estado", "producto", "actualizada_en"))
    registrar_evento(
        empresa=programacion.empresa,
        accion="EDITAR",
        modulo="planificacion_menu",
        descripcion=f"Excepcion aplicada a programacion {programacion.pk}: {motivo.strip()}",
        usuario=usuario,
        objeto=programacion,
        request=request,
        datos_anteriores={"estado": excepcion.estado_anterior, "producto": excepcion.producto_anterior},
        datos_nuevos={"estado": estado_nuevo, "producto": producto_nuevo.strip()},
    )
    return excepcion
