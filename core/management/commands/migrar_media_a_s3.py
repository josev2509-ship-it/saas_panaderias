import os
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from storages.backends.s3 import S3Storage


class Command(BaseCommand):
    help = (
        "Copia de forma idempotente los archivos existentes en MEDIA_ROOT "
        "al Storage Bucket S3 configurado para producción."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="",
            help="Directorio origen. Por defecto usa settings.MEDIA_ROOT.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Analiza lo que se copiaría sin escribir en S3.",
        )

        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Sobrescribe un objeto remoto si existe con tamaño diferente.",
        )

    def handle(self, *args, **options):
        source = Path(
            options["source"]
            or settings.MEDIA_ROOT
        ).resolve()

        if not source.exists():
            raise CommandError(
                f"MEDIA_ROOT no existe: {source}"
            )

        if not source.is_dir():
            raise CommandError(
                f"El origen no es un directorio: {source}"
            )

        bucket = (
            os.environ.get("BUCKET")
            or os.environ.get("AWS_S3_BUCKET_NAME")
            or os.environ.get("AWS_STORAGE_BUCKET_NAME")
        )

        access_key = (
            os.environ.get("ACCESS_KEY_ID")
            or os.environ.get("AWS_ACCESS_KEY_ID")
        )

        secret_key = (
            os.environ.get("SECRET_ACCESS_KEY")
            or os.environ.get("AWS_SECRET_ACCESS_KEY")
        )

        region = (
            os.environ.get("REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or os.environ.get("AWS_S3_REGION_NAME")
            or "auto"
        )

        endpoint = (
            os.environ.get("ENDPOINT")
            or os.environ.get("AWS_ENDPOINT_URL")
            or os.environ.get("AWS_S3_ENDPOINT_URL")
        )

        faltantes = []

        if not bucket:
            faltantes.append("BUCKET")

        if not access_key:
            faltantes.append("ACCESS_KEY_ID")

        if not secret_key:
            faltantes.append("SECRET_ACCESS_KEY")

        if not endpoint:
            faltantes.append("ENDPOINT")

        if faltantes:
            raise CommandError(
                "Faltan variables del bucket: "
                + ", ".join(faltantes)
            )

        storage = S3Storage(
            bucket_name=bucket,
            access_key=access_key,
            secret_key=secret_key,
            region_name=region,
            endpoint_url=endpoint,
            addressing_style="virtual",
            location="media",
            default_acl=None,
            querystring_auth=True,
            file_overwrite=True,
        )

        archivos = sorted(
            p
            for p in source.rglob("*")
            if p.is_file()
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Migración MEDIA -> Storage Bucket"
            )
        )
        self.stdout.write(
            f"Origen: {source}"
        )
        self.stdout.write(
            f"Archivos detectados: {len(archivos)}"
        )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    "MODO DRY-RUN: no se escribirá nada."
                )
            )

        copiados = 0
        existentes = 0
        sobrescritos = 0
        errores = 0

        for archivo_local in archivos:
            nombre = archivo_local.relative_to(
                source
            ).as_posix()

            tamano_local = archivo_local.stat().st_size

            try:
                existe = storage.exists(nombre)

                if existe:
                    tamano_remoto = storage.size(nombre)

                    if tamano_remoto == tamano_local:
                        existentes += 1

                        self.stdout.write(
                            f"YA EXISTE  {nombre}"
                        )

                        continue

                    if not options["overwrite"]:
                        errores += 1

                        self.stderr.write(
                            self.style.ERROR(
                                "CONFLICTO   "
                                f"{nombre} "
                                f"(local={tamano_local}, "
                                f"remoto={tamano_remoto})"
                            )
                        )

                        continue

                    if options["dry_run"]:
                        sobrescritos += 1

                        self.stdout.write(
                            f"SOBRESCRIBIRÍA {nombre}"
                        )

                        continue

                    storage.delete(nombre)
                    sobrescritos += 1

                if options["dry_run"]:
                    copiados += 1

                    self.stdout.write(
                        f"COPIARÍA    {nombre}"
                    )

                    continue

                with archivo_local.open("rb") as fh:
                    guardado = storage.save(
                        nombre,
                        File(
                            fh,
                            name=archivo_local.name,
                        ),
                    )

                if guardado != nombre:
                    raise RuntimeError(
                        "Storage devolvió un nombre inesperado: "
                        f"{guardado}"
                    )

                if not storage.exists(nombre):
                    raise RuntimeError(
                        "El objeto no aparece después de guardarse."
                    )

                tamano_remoto = storage.size(nombre)

                if tamano_remoto != tamano_local:
                    raise RuntimeError(
                        "Tamaño remoto diferente: "
                        f"local={tamano_local}, "
                        f"remoto={tamano_remoto}"
                    )

                copiados += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"OK          {nombre}"
                    )
                )

            except Exception as exc:
                errores += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"ERROR       {nombre}: {exc}"
                    )
                )

        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write(
            f"Copiados:       {copiados}"
        )
        self.stdout.write(
            f"Ya existentes:  {existentes}"
        )
        self.stdout.write(
            f"Sobrescritos:   {sobrescritos}"
        )
        self.stdout.write(
            f"Errores:        {errores}"
        )
        self.stdout.write("=" * 70)

        if errores:
            raise CommandError(
                f"La migración terminó con {errores} conflicto(s)/error(es)."
            )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN completado correctamente."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "MIGRACIÓN MEDIA -> S3 COMPLETADA"
                )
            )
