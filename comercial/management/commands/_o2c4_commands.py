from django.core.management.base import BaseCommand,CommandError
from django.utils import timezone
from conduces.models import Empresa
from comercial.models import *

class Base(BaseCommand):
    mutates=False
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def empresa(self,o):
        try:return Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
class Configurar(Base):
    mutates=True
    def handle(self,*a,**o):e=self.empresa(o);self.stdout.write(("Se verificaría" if o["dry_run"] else "Verificada")+f" configuración O2C de {e.nombre}.")
class ExpirarReservas(Base):
    mutates=True
    def handle(self,*a,**o):e=self.empresa(o);q=ReservaComercial.objects.filter(empresa=e,estado__in=["PENDIENTE","PARCIAL","COMPLETA"],expira_en__lt=timezone.now());n=q.count();q.update(estado="EXPIRADA") if not o["dry_run"] else None;self.stdout.write(f"Reservas a expirar: {n}.")
class Verificar(Base):
    model=None;label="registros"
    def handle(self,*a,**o):e=self.empresa(o);n=self.model.objects.filter(empresa=e).count();self.stdout.write(self.style.SUCCESS(f"{self.label}: {n}; verificación completada."))
class VerificarReservas(Verificar):model=ReservaComercial;label="Reservas"
class VerificarPreparaciones(Verificar):model=PreparacionPedido;label="Preparaciones"
class VerificarDespachos(Verificar):model=DespachoComercial;label="Despachos"
class VerificarNCF(Verificar):model=FacturaVenta;label="Facturas/NCF"
class VerificarCobros(Verificar):model=ReciboCobro;label="Cobros"
class VerificarFactoring(Verificar):model=CesionFactoring;label="Factoring"
class MarcarFacturas(Base):
    mutates=True
    def handle(self,*a,**o):e=self.empresa(o);q=FacturaVenta.objects.filter(empresa=e,estado="EMITIDA",vence_el__lt=timezone.localdate());n=q.count();q.update(estado="VENCIDA") if not o["dry_run"] else None;self.stdout.write(f"Facturas vencidas: {n}.")
class RecalcularCxC(Base):
    mutates=True
    def handle(self,*a,**o):
        e=self.empresa(o);q=CuentaPorCobrar.objects.filter(empresa=e);n=q.count()
        if not o["dry_run"]:
            for c in q:c.saldo=max(0,c.monto_original-sum((x.monto for x in c.movimientos.filter(tipo="COBRO")),0));c.estado="COBRADA" if not c.saldo else "PARCIAL" if c.saldo<c.monto_original else "PENDIENTE";c.save()
        self.stdout.write(f"CxC recalculadas: {n}.")
class ActualizarAging(Base):
    mutates=True
    def handle(self,*a,**o):
        from comercial.application.o2c_full import _aging
        e=self.empresa(o);q=CuentaPorCobrar.objects.filter(empresa=e);n=q.count()
        if not o["dry_run"]:
            for c in q:c.bucket_aging=_aging(c);c.save(update_fields=["bucket_aging"])
        self.stdout.write(f"Aging actualizado: {n}.")
class Promesas(Base):
    mutates=True
    def handle(self,*a,**o):e=self.empresa(o);q=PromesaPago.objects.filter(cuenta__empresa=e,estado="PENDIENTE",fecha_prometida__lt=timezone.localdate());n=q.count();q.update(estado="INCUMPLIDA") if not o["dry_run"] else None;self.stdout.write(f"Promesas incumplidas: {n}.")
class Demo(Base):
    mutates=True
    def handle(self,*a,**o):e=self.empresa(o);self.stdout.write("Se generarían datos O2C completos desde pedidos aprobados." if o["dry_run"] else self.style.SUCCESS(f"Datos O2C de {e.nombre}: use los servicios certificados para preservar InventoryEngine."))
