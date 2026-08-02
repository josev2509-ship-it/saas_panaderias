from datetime import timedelta
from decimal import Decimal
from django.core.management import call_command
from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone
from conduces.models import Empresa
from core.application.numbering import obtener_siguiente_numero
from comercial.models import Prospecto,OportunidadComercial,ActividadComercial,FuenteProspecto,VendedorComercial
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def handle(self,*a,**o):
        try:e=Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
        if o["dry_run"]:self.stdout.write("Se generarían 30 prospectos, 15 oportunidades y 40 actividades.");return
        call_command("configurar_crm",empresa=e.pk);fuentes=list(FuenteProspecto.objects.filter(empresa=e));vendedores=list(VendedorComercial.objects.filter(empresa=e,activo=True));usuario=e.usuario;hoy=timezone.localdate();ahora=timezone.now();ps=[]
        for i in range(1,31):
            obj=Prospecto.objects.filter(empresa=e,identificacion_fiscal=f"DEMO{i:06d}").first()
            if not obj:obj=Prospecto.objects.create(empresa=e,numero=obtener_siguiente_numero(empresa=e,tipo_documento="PROS",usuario=usuario),identificacion_fiscal=f"DEMO{i:06d}",nombre=f"Prospecto Demo {i}",nombre_comercial=f"Empresa Demo {i}",correo=f"crm-demo-{i}@example.invalid",telefono=f"809555{i:04d}",fuente=fuentes[(i-1)%len(fuentes)] if fuentes else None,vendedor=vendedores[(i-1)%len(vendedores)] if vendedores else None,estado=("NUEVO","CONTACTADO","CALIFICADO","NO_CALIFICADO","DESCARTADO")[i%5],presupuesto_estimado=Decimal(i*1000),motivo_no_calificacion="Demo" if i%5==3 else "",motivo_descarte="Demo" if i%5==4 else "",creado_por=usuario,actualizado_por=usuario)
            ps.append(obj)
        ops=[]
        for i in range(1,16):
            obj=OportunidadComercial.objects.filter(empresa=e,titulo=f"Oportunidad Demo {i}").first()
            if not obj:
                etapa=("IDENTIFICADA","CALIFICADA","PROPUESTA","NEGOCIACION","GANADA","PERDIDA")[i%6];obj=OportunidadComercial.objects.create(empresa=e,numero=obtener_siguiente_numero(empresa=e,tipo_documento="OPO",usuario=usuario),prospecto=ps[(i-1)%len(ps)],titulo=f"Oportunidad Demo {i}",vendedor=vendedores[(i-1)%len(vendedores)] if vendedores else None,etapa=etapa,monto_estimado=Decimal(i*5000),probabilidad=Decimal(100 if etapa=="GANADA" else 0 if etapa=="PERDIDA" else (i%5)*20),fecha_apertura=hoy-timedelta(days=i*2),fecha_estimada_cierre=hoy+timedelta(days=i*3),fecha_cierre_real=hoy if etapa in ("GANADA","PERDIDA") else None,motivo_perdida="Competencia" if etapa=="PERDIDA" else "",creado_por=usuario,actualizado_por=usuario)
            ops.append(obj)
        for i in range(1,41):
            if not ActividadComercial.objects.filter(empresa=e,asunto=f"Actividad Demo {i}").exists():
                estado=("PENDIENTE","EN_PROGRESO","COMPLETADA","VENCIDA")[i%4];ActividadComercial.objects.create(empresa=e,prospecto=ps[(i-1)%len(ps)],oportunidad=ops[(i-1)%len(ops)],tipo=ActividadComercial.TIPOS[i%len(ActividadComercial.TIPOS)][0],asunto=f"Actividad Demo {i}",responsable=usuario,fecha_inicio=ahora+timedelta(days=i-10),estado=estado,resultado="Resultado demo" if estado=="COMPLETADA" else "",creado_por=usuario,actualizado_por=usuario)
        self.stdout.write(self.style.SUCCESS("Datos demo CRM generados idempotentemente."))
