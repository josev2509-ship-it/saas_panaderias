from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from compras.application.financial import actualizar_aging_cxp
from compras.application.p2p import recalcular_comparativo
from compras.models import (AdjudicacionCompra, ComparativoCompra, OfertaProveedor,
                            OrdenCompraEnterprise, RecepcionCompra)
from contabilidad.models import CuentaPorPagarEnterprise, FacturaProveedor, OrdenPago
from conduces.models import Empresa

MODELS={"ofertas":OfertaProveedor,"comparativos":ComparativoCompra,"adjudicaciones":AdjudicacionCompra,"ordenes":OrdenCompraEnterprise,"recepciones":RecepcionCompra,"facturas":FacturaProveedor,"cxp":CuentaPorPagarEnterprise,"pagos":OrdenPago}

class P2PCheckCommand(BaseCommand):
    resource="ofertas";modifies=False
    def add_arguments(self,parser):
        parser.add_argument("--empresa",type=int,required=True)
        if self.modifies:parser.add_argument("--dry-run",action="store_true")
    def handle(self,*args,**options):
        try:empresa=Empresa.objects.get(pk=options["empresa"])
        except Empresa.DoesNotExist as exc:raise CommandError("Empresa inexistente.") from exc
        qs=MODELS[self.resource].objects.filter(empresa=empresa);self.stdout.write(f"{self.resource}: {qs.count()} registros; empresa={empresa.pk}")

class AgingCommand(P2PCheckCommand):
    resource="cxp";modifies=True
    def handle(self,*args,**options):
        if options["dry_run"]:return super().handle(*args,**options)
        empresa=Empresa.objects.get(pk=options["empresa"]);self.stdout.write(f"CxP actualizadas: {len(actualizar_aging_cxp(empresa=empresa))}")

class VencerOfertasCommand(P2PCheckCommand):
    resource="ofertas";modifies=True
    def handle(self,*args,**options):
        empresa=Empresa.objects.get(pk=options["empresa"]);qs=OfertaProveedor.objects.filter(empresa=empresa,valida_hasta__lt=timezone.localdate(),estado__in=["ENVIADA","ACTUALIZADA"]);count=qs.count()
        if not options["dry_run"]:qs.update(estado="VENCIDA")
        self.stdout.write(f"Ofertas {'detectadas' if options['dry_run'] else 'vencidas'}: {count}")
