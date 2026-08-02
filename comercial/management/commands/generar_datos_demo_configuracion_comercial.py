from datetime import date
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand,CommandError
from conduces.models import Empresa
from comercial.models import EquipoComercial,ZonaComercial,RutaComercial,VendedorComercial,PoliticaCredito,PoliticaDescuento,PoliticaEntrega,PoliticaFacturacion,PoliticaDevolucion,PoliticaComision
class Command(BaseCommand):
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true");p.add_argument("--inabie",action="store_true")
    def handle(self,*a,**o):
        try:e=Empresa.objects.get(pk=o["empresa"])
        except Empresa.DoesNotExist:raise CommandError("Empresa no encontrada.")
        if o["dry_run"]:self.stdout.write("Se generarían 5 vendedores, 2 equipos, 4 zonas, 6 rutas, políticas y secuencias.");return
        call_command("configurar_comercial",empresa=e.pk);call_command("crear_catalogos_comerciales_base",empresa=e.pk);call_command("configurar_secuencias_comerciales",empresa=e.pk)
        equipos=[EquipoComercial.objects.get_or_create(empresa=e,codigo=f"EQ{i}",defaults={"nombre":f"Equipo {i}"})[0] for i in range(1,3)]
        zonas=[ZonaComercial.objects.get_or_create(empresa=e,codigo=f"Z{i}",defaults={"nombre":f"Zona {i}"})[0] for i in range(1,5)]
        rutas=[RutaComercial.objects.get_or_create(empresa=e,codigo=f"R{i}",defaults={"nombre":f"Ruta {i}","zona":zonas[(i-1)%4]})[0] for i in range(1,7)]
        usuarios=list(get_user_model().objects.order_by("pk")[:5])
        for i,u in enumerate(usuarios,1):VendedorComercial.objects.get_or_create(empresa=e,usuario=u,defaults={"codigo":f"V{i}","nombre":u.get_full_name() or u.username,"equipo":equipos[(i-1)%2],"zona":zonas[(i-1)%4]})
        for model in (PoliticaCredito,PoliticaDescuento,PoliticaEntrega,PoliticaFacturacion,PoliticaDevolucion,PoliticaComision):model.objects.get_or_create(empresa=e,codigo="BASE",version=1,defaults={"nombre":"Política base","estado":"ACTIVA","vigencia_desde":date.today(),"creado_por":usuarios[0] if usuarios else None})
        self.stdout.write(self.style.SUCCESS("Datos demo comerciales generados idempotentemente."))
