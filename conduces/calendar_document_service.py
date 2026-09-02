import hashlib
from calendar import month_name
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction

from auditoria.services import registrar_evento

from .calendar_document_parser import LocalTextPDFProvider
from .models import (
    AnalisisDocumentoCalendario,
    CalendarioEscolar,
    DiaCalendarioEscolar,
    EventoDocumentoCalendario,
    ProgramacionMenuEscolar,
    TotalMensualCalendario,
)


def validar_pdf(archivo):
    nombre = (getattr(archivo, "name", "") or "").lower()
    if not nombre.endswith(".pdf"):
        raise ValidationError("El documento debe ser un archivo PDF.")
    max_mb = settings.CALENDAR_PDF_MAX_MB
    if getattr(archivo, "size", 0) > max_mb * 1024 * 1024:
        raise ValidationError(f"El PDF supera el limite de {max_mb} MB.")
    posicion = archivo.tell()
    cabecera = archivo.read(5)
    archivo.seek(posicion)
    if cabecera != b"%PDF-":
        raise ValidationError("El archivo no contiene una cabecera PDF valida.")


def _hash_archivo(archivo):
    archivo.seek(0)
    digest = hashlib.sha256()
    for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
        digest.update(bloque)
    archivo.seek(0)
    return digest.hexdigest()


def _iterar_meses(inicio, fin):
    actual = date(inicio.year, inicio.month, 1)
    limite = date(fin.year, fin.month, 1)
    while actual <= limite:
        yield actual.year, actual.month
        actual = date(actual.year + (actual.month == 12), 1 if actual.month == 12 else actual.month + 1, 1)


def _construir_dias(calendario, resultado):
    eventos_por_fecha = {}
    for evento in resultado.eventos:
        fin = evento.fecha_fin or evento.fecha_inicio
        actual = evento.fecha_inicio
        while actual <= fin:
            eventos_por_fecha[actual] = evento
            actual += timedelta(days=1)
    filas = []
    actual = calendario.inicio_docencia
    while actual <= calendario.fin_docencia:
        evento = eventos_por_fecha.get(actual)
        if evento:
            clasificacion = evento.clasificacion
            motivo = evento.descripcion
            origen = "ANALISIS_DOCUMENTAL"
        else:
            clasificacion = (
                DiaCalendarioEscolar.Clasificacion.DOCENCIA
                if actual.weekday() < 5
                else DiaCalendarioEscolar.Clasificacion.NO_LECTIVO
            )
            motivo = ""
            origen = "PREVISUALIZACION_DOCUMENTAL"
        filas.append(DiaCalendarioEscolar(
            calendario=calendario,
            fecha=actual,
            clasificacion=clasificacion,
            motivo=motivo,
            origen=origen,
        ))
        actual += timedelta(days=1)
    calendario.dias.all().delete()
    DiaCalendarioEscolar.objects.bulk_create(filas)


def _guardar_resultados(analisis, resultado):
    for evento in resultado.eventos:
        EventoDocumentoCalendario.objects.create(
            analisis=analisis,
            fecha_inicio=evento.fecha_inicio,
            fecha_fin=evento.fecha_fin,
            clasificacion=evento.clasificacion,
            tipo_contextual=evento.tipo,
            descripcion=evento.descripcion,
            evidencia=evento.evidencia.texto,
            pagina=evento.evidencia.pagina,
            confianza=evento.evidencia.confianza,
            estado=(
                EventoDocumentoCalendario.Estado.DETECTADO
                if evento.evidencia.confianza >= 0.8
                else EventoDocumentoCalendario.Estado.REQUIERE_REVISION
            ),
        )


def _calcular_totales(analisis, resultado):
    calendario = analisis.calendario
    inconsistencias = 0
    suma_calculada = 0
    for anio, mes in _iterar_meses(calendario.inicio_docencia, calendario.fin_docencia):
        calculados = sum(
            1 for dia in calendario.dias.filter(
                fecha__year=anio,
                fecha__month=mes,
                clasificacion=DiaCalendarioEscolar.Clasificacion.DOCENCIA,
            ).only("fecha") if dia.fecha.weekday() < 5
        )
        suma_calculada += calculados
        declarado_data = resultado.totales_mensuales.get((anio, mes))
        declarados = declarado_data[0] if declarado_data else None
        diferencia = calculados - declarados if declarados is not None else 0
        estado = "OK" if declarados is not None and diferencia == 0 else "REQUIERE_REVISION"
        if estado != "OK":
            inconsistencias += 1
        eventos_mes = [evento for evento in resultado.eventos if evento.fecha_inicio.year == anio and evento.fecha_inicio.month == mes]
        explicacion = ""
        if diferencia and eventos_mes:
            explicacion = "Eventos detectados: " + "; ".join(evento.descripcion for evento in eventos_mes[:5])
        elif diferencia:
            explicacion = f"Existe una diferencia de {diferencia:+d} dia(s) y no se encontro evidencia suficiente para resolverla automaticamente."
        evidencia = declarado_data[1] if declarado_data else None
        TotalMensualCalendario.objects.create(
            analisis=analisis, anio=anio, mes=mes,
            dias_declarados=declarados, dias_calculados=calculados,
            diferencia=diferencia, estado=estado,
            evidencia=evidencia.texto if evidencia else "",
            pagina=evidencia.pagina if evidencia else None,
            explicacion=explicacion,
        )
    total_inconsistente = resultado.total_oficial is None or suma_calculada != resultado.total_oficial
    return inconsistencias, suma_calculada, total_inconsistente


@transaction.atomic
def analizar_documento_calendario(*, empresa, usuario, archivo, request=None, calendario=None, proveedor=None):
    validar_pdf(archivo)
    proveedor = proveedor or LocalTextPDFProvider()
    hash_sha256 = _hash_archivo(archivo)
    analisis = AnalisisDocumentoCalendario.objects.create(
        empresa=empresa,
        calendario=calendario,
        archivo=archivo,
        nombre_original=archivo.name,
        hash_sha256=hash_sha256,
        proveedor=proveedor.nombre,
        version_proveedor=proveedor.version,
        estado=AnalisisDocumentoCalendario.Estado.PROCESANDO,
        creado_por=usuario,
    )
    try:
        with analisis.archivo.open("rb") as documento:
            resultado = proveedor.extract(documento)
    except Exception as error:
        analisis.estado = AnalisisDocumentoCalendario.Estado.FALLIDO
        analisis.advertencias = [f"No fue posible extraer texto del PDF: {type(error).__name__}."]
        analisis.save(update_fields=("estado", "advertencias"))
        return analisis

    analisis.confianza = resultado.confianza
    analisis.advertencias = resultado.advertencias
    analisis.texto_extraido = resultado.texto
    analisis.paginas = resultado.paginas
    analisis.datos_detectados = {
        "nombre": resultado.nombre,
        "anio_inicio": resultado.anio_inicio,
        "anio_fin": resultado.anio_fin,
        "inicio_docencia": resultado.inicio_docencia.isoformat() if resultado.inicio_docencia else None,
        "fin_docencia": resultado.fin_docencia.isoformat() if resultado.fin_docencia else None,
        "total_oficial": resultado.total_oficial,
        "evidencias": {
            clave: {
                "texto": evidencia.texto,
                "pagina": evidencia.pagina,
                "confianza": evidencia.confianza,
            }
            for clave, evidencia in resultado.evidencias.items()
        },
    }
    campos_minimos = all((resultado.anio_inicio, resultado.anio_fin, resultado.inicio_docencia, resultado.fin_docencia))
    if not campos_minimos:
        analisis.estado = AnalisisDocumentoCalendario.Estado.REQUIERE_REVISION
        analisis.save()
        _guardar_resultados(analisis, resultado)
        return analisis

    existente = calendario or CalendarioEscolar.objects.filter(
        empresa=empresa, anio_inicio=resultado.anio_inicio, anio_fin=resultado.anio_fin
    ).first()
    if existente and (
        existente.estado in (CalendarioEscolar.Estado.ACTIVO, CalendarioEscolar.Estado.CERRADO)
        or ProgramacionMenuEscolar.objects.filter(calendario=existente).exists()
    ):
        analisis.calendario = existente
        analisis.estado = AnalisisDocumentoCalendario.Estado.REQUIERE_REVISION
        analisis.advertencias = [*resultado.advertencias, "El calendario tiene estado u operaciones historicas y no fue sobrescrito."]
        analisis.save()
        _guardar_resultados(analisis, resultado)
        return analisis

    calendario = existente or CalendarioEscolar(empresa=empresa)
    calendario.nombre = resultado.nombre or f"Año escolar {resultado.anio_inicio}-{resultado.anio_fin}"
    calendario.anio_inicio = resultado.anio_inicio
    calendario.anio_fin = resultado.anio_fin
    calendario.inicio_docencia = resultado.inicio_docencia
    calendario.fin_docencia = resultado.fin_docencia
    calendario.dias_docencia_oficiales = resultado.total_oficial
    calendario.estado = CalendarioEscolar.Estado.EN_REVISION
    calendario.documento_fuente.name = analisis.archivo.name
    calendario.full_clean()
    calendario.save()
    analisis.calendario = calendario
    _construir_dias(calendario, resultado)
    _guardar_resultados(analisis, resultado)
    inconsistencias, calculados, total_inconsistente = _calcular_totales(analisis, resultado)
    analisis.datos_detectados["total_calculado"] = calculados
    analisis.estado = (
        AnalisisDocumentoCalendario.Estado.DETECTADO
        if not inconsistencias and not total_inconsistente and not resultado.advertencias
        else AnalisisDocumentoCalendario.Estado.REQUIERE_REVISION
    )
    analisis.save()
    registrar_evento(
        empresa=empresa, accion="CARGAR_DOCUMENTO", modulo="calendario_escolar",
        descripcion=f"Calendario analizado con {proveedor.nombre}; estado {analisis.estado}.",
        usuario=usuario, objeto=analisis, request=request,
        datos_nuevos={"hash": hash_sha256, "estado": analisis.estado, "calendario_id": calendario.pk},
    )
    return analisis
