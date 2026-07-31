import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from auditoria.models import EventoAuditoria
from auditoria.services import registrar_evento
from conduces.models import Empresa
from contabilidad.models import Proveedor as ProveedorLegacy
from compras.domain.identity import normalizar_identificacion
from compras.models import Proveedor, ProveedorLegadoMap


class Command(BaseCommand):
    help="Importación idempotente y controlada de proveedores fiscales heredados."

    def add_arguments(self,p):
        p.add_argument("--empresa",type=int,required=True)
        p.add_argument("--confirmar",action="store_true")
        p.add_argument("--dry-run",action="store_true")
        p.add_argument("--solo-id",type=int)
        p.add_argument("--solo-conflictos",action="store_true")
        p.add_argument("--estrategia",default="RNC_NORMALIZADO")
        p.add_argument("--salida")
        p.add_argument("--actualizar-mapeos",action="store_true")
        p.add_argument("--sin-documentos",action="store_true")

    @transaction.atomic
    def handle(self,*args,**o):
        if o["confirmar"] and o["dry_run"]: raise CommandError("No combine --confirmar y --dry-run.")
        empresa=Empresa.objects.get(pk=o["empresa"])
        qs=ProveedorLegacy.objects.all().order_by("pk")
        if o["solo_id"]: qs=qs.filter(pk=o["solo_id"])
        rows=[]; stats={"creados":0,"vinculados":0,"omitidos":0,"conflictos":0,"sin_empresa":0,"sin_rnc":0,"errores":0}
        for legacy in qs:
            row={"legacy_id":legacy.pk,"nombre":legacy.nombre,"resultado":""}
            if ProveedorLegadoMap.objects.filter(empresa=empresa,proveedor_legacy=legacy).exists():
                row["resultado"]="omitido_mapeado"; stats["omitidos"]+=1; rows.append(row); continue
            rnc=normalizar_identificacion(legacy.rnc)
            if not rnc: stats["sin_rnc"]+=1
            matches=Proveedor.objects.filter(empresa=empresa,rnc_normalizado=rnc) if rnc else Proveedor.objects.none()
            if matches.count()>1:
                row["resultado"]="conflicto"; stats["conflictos"]+=1; rows.append(row); continue
            nuevo=matches.first()
            if not nuevo and not o["solo_conflictos"]:
                row["resultado"]="creado"
                if o["confirmar"]:
                    nuevo=Proveedor(empresa=empresa,codigo=f"LEG-{legacy.pk:06d}",tipo_persona="JURIDICA",
                        razon_social=legacy.nombre,rnc_identificacion=legacy.rnc or "",correo=legacy.correo or "",
                        telefono=legacy.telefono or "")
                    nuevo.full_clean(); nuevo.save()
                stats["creados"]+=1
            elif nuevo:
                row["resultado"]="vinculado"; stats["vinculados"]+=1
            else:
                row["resultado"]="omitido"; stats["omitidos"]+=1
            if o["confirmar"] and nuevo:
                ProveedorLegadoMap.objects.get_or_create(empresa=empresa,proveedor_legacy=legacy,
                    defaults={"proveedor_nuevo":nuevo,"metodo_correspondencia":"RNC_NORMALIZADO" if rnc else "IMPORTACION",
                              "estado":"CONFIRMADO","origen":"MIGRACION_CONTROLADA"})
            rows.append(row)
        if o["confirmar"]:
            registrar_evento(empresa=empresa,modulo="compras",accion=EventoAuditoria.Accion.OTRO,
                descripcion="Migración controlada de proveedores heredados.",datos_nuevos=stats)
        if o["salida"]:
            path=Path(o["salida"])
            if path.suffix.lower()==".json": path.write_text(json.dumps({"resumen":stats,"filas":rows},ensure_ascii=False,indent=2),encoding="utf-8")
            else:
                with path.open("w",newline="",encoding="utf-8-sig") as fh:
                    writer=csv.DictWriter(fh,fieldnames=("legacy_id","nombre","resultado"));writer.writeheader();writer.writerows(rows)
        self.stdout.write(json.dumps({"modo":"real" if o["confirmar"] else "simulacion",**stats},ensure_ascii=False))
