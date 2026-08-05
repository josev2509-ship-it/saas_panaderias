from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from django.utils import timezone

from catalogos.models import Almacen,CentroCosto,Moneda,MonedaEmpresa,TipoCompra,UnidadMedida
from conduces.models import Empresa
from contabilidad.models import (AnticipoProveedor,AplicacionAnticipoProveedor,AplicacionNotaProveedor,
 CertificadoRetencionProveedor,CompensacionP2P,CuentaPorPagarEnterprise,FacturaProveedor,
 NotaCreditoProveedor,NotaDebitoProveedor,OrdenPago,RetencionProveedor,SolicitudPago)
from compras.models import (AdjudicacionCompra,ComparativoCompra,ExpedienteCompra,
    OfertaProveedor,OrdenCompraEnterprise,ProcesoRFQ,Proveedor,RecepcionCompra,WizardSession,WizardStepState)
from tesoreria.models import (ConciliacionBancaria,CuentaBancariaEmpresa,ImportacionExtractoBancario,
 LineaExtractoBancario,MovimientoTesoreria)

TARGETS={"proveedores":50,"rfq":150,"ofertas":300,"comparativos":100,"adjudicaciones":80,"ordenes":120,"recepciones":180,"facturas":150,"pagos":200}

class Command(BaseCommand):
    help="Genera un universo P2P determinista, idempotente y aislado por empresa."
    def add_arguments(self,p):p.add_argument("--empresa",type=int,required=True);p.add_argument("--dry-run",action="store_true")
    def handle(self,*args,**options):
        try:empresa=Empresa.objects.select_related("usuario").get(pk=options["empresa"])
        except Empresa.DoesNotExist as exc:raise CommandError("Empresa inexistente.") from exc
        counts={"proveedores":Proveedor.objects.filter(empresa=empresa,codigo__startswith="DMP2P-").count(),"rfq":ProcesoRFQ.objects.filter(empresa=empresa,numero__startswith="DMP2P-").count(),"ofertas":OfertaProveedor.objects.filter(empresa=empresa,numero__startswith="DMP2P-").count(),"comparativos":ComparativoCompra.objects.filter(empresa=empresa,numero__startswith="DMP2P-").count(),"adjudicaciones":AdjudicacionCompra.objects.filter(empresa=empresa,numero__startswith="DMP2P-").count(),"ordenes":OrdenCompraEnterprise.objects.filter(empresa=empresa,numero__startswith="DMP2P-").count(),"recepciones":RecepcionCompra.objects.filter(empresa=empresa,numero__startswith="DMP2P-").count(),"facturas":FacturaProveedor.objects.filter(empresa=empresa,numero__startswith="DMP2P-").count(),"pagos":OrdenPago.objects.filter(empresa=empresa,numero__startswith="DMP2P-").count()}
        if options["dry_run"]:
            self.stdout.write(str({name:{"actual":counts[name],"objetivo":target,"faltan":max(0,target-counts[name])} for name,target in TARGETS.items()}));return
        self._generate(empresa);self.stdout.write(self.style.SUCCESS(f"Demo P2P listo para empresa {empresa.pk}: {TARGETS}"))

    @transaction.atomic
    def _generate(self,empresa):
        user=empresa.usuario;today=timezone.localdate();now=timezone.now()
        currency,_=Moneda.objects.get_or_create(codigo="DOP",defaults={"nombre":"Peso dominicano","simbolo":"RD$"});mon,_=MonedaEmpresa.objects.get_or_create(empresa=empresa,moneda=currency,defaults={"es_base":True,"activa":True});cc,_=CentroCosto.objects.get_or_create(empresa=empresa,codigo="DMP2P",defaults={"nombre":"Demo P2P","responsable":user});tc,_=TipoCompra.objects.get_or_create(empresa=empresa,codigo="DMP2P",defaults={"nombre":"Compra demo","naturaleza":"BIEN","afecta_inventario":True});warehouse,_=Almacen.objects.get_or_create(empresa=empresa,codigo="DMP2P",defaults={"nombre":"Almacén demo P2P","tipo":"GENERAL","responsable":user});unit,_=UnidadMedida.objects.get_or_create(empresa=empresa,codigo="DMP2P-U",defaults={"nombre":"Unidad demo","simbolo":"u","magnitud":"UNIDAD"})
        providers=[]
        for i in range(50):
            p,_=Proveedor.objects.get_or_create(empresa=empresa,codigo=f"DMP2P-{i+1:03d}",defaults={"tipo_persona":"JURIDICA","razon_social":f"Proveedor Demo P2P {i+1:03d}","nombre_comercial":f"Proveedor {i+1:03d}","estado":"ACTIVO","nivel_riesgo":["BAJO","MEDIO","ALTO","CRITICO"][i%4],"documentacion_completa":i%5!=0,"creado_por":user});providers.append(p)
        rfqs=[]
        for i in range(150):
            exp,_=ExpedienteCompra.objects.get_or_create(empresa=empresa,numero=f"DMP2P-EXP-{i+1:04d}",defaults={"titulo":f"Expediente demo {i+1}","responsable":user,"solicitante_principal":user,"centro_costo":cc,"tipo_compra":tc,"prioridad":["NORMAL","ALTA","URGENTE"][i%3],"moneda":mon,"presupuesto_estimado":Decimal("10000")+i,"estado":"RFQ_ABIERTA","creado_por":user,"actualizado_por":user})
            rfq,_=ProcesoRFQ.objects.get_or_create(empresa=empresa,numero=f"DMP2P-RFQ-{i+1:04d}",defaults={"expediente":exp,"titulo":f"RFQ Demo {i+1}","objeto":"Compra demostrativa","descripcion":"Datos sintéticos P2P","estado":["ABIERTA","CERRADA","EXTENDIDA"][i%3],"moneda":mon,"fecha_inicio":now-timedelta(days=2),"fecha_limite":now+timedelta(days=15+i%20),"entrega_requerida_desde":today+timedelta(days=20),"entrega_requerida_hasta":today+timedelta(days=40),"lugar_entrega":warehouse.nombre,"almacen_destino":warehouse,"condiciones_comerciales":"Crédito 30 días","creado_por":user,"actualizado_por":user});rfqs.append(rfq)
        offers=[]
        for i in range(300):
            version=1+i//150;o,_=OfertaProveedor.objects.get_or_create(empresa=empresa,numero=f"DMP2P-OFE-{i+1:04d}",version=version,defaults={"rfq":rfqs[i%150],"proveedor":providers[i%50],"moneda":mon,"fecha_oferta":today,"valida_hasta":today+timedelta(days=30),"estado":["ENVIADA","ACTUALIZADA","EVALUADA"][i%3],"subtotal":Decimal("1000")+i,"impuesto":Decimal("180"),"total":Decimal("1180")+i,"score_tecnico":80+i%20,"score_economico":75+i%25,"score_total":78+i%20,"creado_por":user,"actualizado_por":user});offers.append(o)
        comparisons=[]
        for i in range(100):
            c,_=ComparativoCompra.objects.get_or_create(empresa=empresa,numero=f"DMP2P-COM-{i+1:04d}",version=1,defaults={"expediente":rfqs[i].expediente,"rfq":rfqs[i],"estado":"CONGELADO" if i%2 else "BORRADOR","ponderaciones":{"precio":25,"tecnico":75},"recomendacion":providers[i%50].razon_social,"creado_por":user,"actualizado_por":user});comparisons.append(c)
        awards=[]
        for i in range(80):
            a,_=AdjudicacionCompra.objects.get_or_create(empresa=empresa,numero=f"DMP2P-ADJ-{i+1:04d}",version=1,defaults={"expediente":comparisons[i].expediente,"comparativo":comparisons[i],"tipo":["TOTAL","PARCIAL","MULTIPLE"][i%3],"estado":"APROBADA","justificacion":"Mejor combinación técnica y económica.","aprobada_en":now,"creado_por":user,"actualizado_por":user});awards.append(a)
        orders=[]
        for i in range(120):
            o,_=OrdenCompraEnterprise.objects.get_or_create(empresa=empresa,numero=f"DMP2P-OC-{i+1:04d}",version=1,defaults={"adjudicacion":awards[i%80] if i<80 else None,"proveedor":providers[i%50],"moneda":mon,"fecha":today-timedelta(days=i%20),"entrega_desde":today,"entrega_hasta":today+timedelta(days=30),"estado":["ACEPTADA","PARCIALMENTE_RECIBIDA","RECIBIDA","FACTURADA"][i%4],"subtotal":Decimal("5000")+i,"impuesto":Decimal("900"),"total":Decimal("5900")+i,"creado_por":user,"actualizado_por":user});orders.append(o)
        receipts=[]
        for i in range(180):
            r,_=RecepcionCompra.objects.get_or_create(empresa=empresa,numero=f"DMP2P-REC-{i+1:04d}",defaults={"orden":orders[i%120],"estado":["PARCIAL","COMPLETA","CON_DIFERENCIAS"][i%3],"fecha":now-timedelta(days=i%30),"almacen":warehouse,"documento_proveedor":f"ENT-{i+1:04d}","creado_por":user,"actualizado_por":user});receipts.append(r)
        invoices=[]
        for i in range(150):
            f,_=FacturaProveedor.objects.get_or_create(empresa=empresa,proveedor=orders[i%120].proveedor,numero=f"DMP2P-FAC-{i+1:04d}",defaults={"orden":orders[i%120],"recepcion":receipts[i],"fecha":today-timedelta(days=i%45),"vence_el":today+timedelta(days=30-i%60),"moneda":mon,"subtotal":Decimal("1000")+i,"impuesto":Decimal("180"),"total":Decimal("1180")+i,"estado":["VALIDADA","PARCIALMENTE_PAGADA","VENCIDA"][i%3],"creado_por":user});invoices.append(f)
            CuentaPorPagarEnterprise.objects.get_or_create(empresa=empresa,factura=f,defaults={"proveedor":f.proveedor,"moneda":mon,"monto_original":f.total,"saldo":f.total if i%3!=1 else f.total/2,"vence_el":f.vence_el,"estado":"PENDIENTE" if i%3==0 else "PARCIAL" if i%3==1 else "VENCIDA","bucket_aging":"CORRIENTE","creado_por":user})
        accounts=list(CuentaPorPagarEnterprise.objects.filter(empresa=empresa,factura__numero__startswith="DMP2P-").order_by("pk"))
        for i in range(200):
            number=f"DMP2P-PAG-{i+1:04d}"
            if not OrdenPago.objects.filter(empresa=empresa,numero=number).exists():
                request=SolicitudPago.objects.create(empresa=empresa,cuenta=accounts[i%150],monto=Decimal("100")+(i%10),estado="APROBADA",creado_por=user);OrdenPago.objects.create(empresa=empresa,numero=number,solicitud=request,estado=["APROBADA","PARCIAL","PAGADA"][i%3],creado_por=user)
        advance,_=AnticipoProveedor.objects.get_or_create(empresa=empresa,proveedor=providers[0],referencia="DMP2P-ANT-001",defaults={"moneda":mon,"monto":Decimal("500"),"saldo":Decimal("250"),"estado":"DISPONIBLE","creado_por":user})
        retention,_=RetencionProveedor.objects.get_or_create(empresa=empresa,clave_idempotencia="DMP2P-RET-001",defaults={"numero":"DMP2P-RET-001","proveedor":accounts[0].proveedor,"factura":accounts[0].factura,"tipo":"ISR","codigo":"DEMO-CONFIG","base":Decimal("1000"),"tasa":Decimal("0.10"),"monto":Decimal("100"),"saldo":Decimal("100"),"estado":"APLICADA","fecha":today,"creado_por":user})
        CertificadoRetencionProveedor.objects.get_or_create(empresa=empresa,retencion=retention,defaults={"numero":"DMP2P-CERT-001","contenido_hash":"0"*64,"creado_por":user})
        CompensacionP2P.objects.get_or_create(empresa=empresa,clave_idempotencia="DMP2P-COMP-001",defaults={"numero":"DMP2P-COMP-001","cuenta_pagar":accounts[0],"anticipo":advance,"moneda":mon,"monto":Decimal("100"),"monto_base":Decimal("100"),"estado":"PROPUESTA","creado_por":user})
        for index,estado in enumerate(("APROBADA","RECHAZADA","ANULADA","APLICADA"),1):
            note,_=NotaCreditoProveedor.objects.get_or_create(empresa=empresa,factura=invoices[index],numero=f"DMP2P-NC-{index:03d}",defaults={"monto":Decimal("100"),"saldo_disponible":Decimal("0") if estado=="APLICADA" else Decimal("100"),"motivo":"Escenario demo narrativo","estado":estado,"creado_por":user})
            NotaDebitoProveedor.objects.get_or_create(empresa=empresa,factura=invoices[index+5],numero=f"DMP2P-ND-{index:03d}",defaults={"monto":Decimal("25"),"motivo":"Recargo demo","concepto":"RECARGO","estado":estado,"creado_por":user})
        for index,estado in enumerate(("DISPONIBLE","RECHAZADO","ANULADO","APLICADO"),1):
            AnticipoProveedor.objects.get_or_create(empresa=empresa,proveedor=providers[index],referencia=f"DMP2P-ANT-{index+1:03d}",defaults={"moneda":mon,"monto":Decimal("200"),"saldo":Decimal("0") if estado=="APLICADO" else Decimal("200"),"estado":estado,"creado_por":user})
        for index,estado in enumerate(("APROBADA","RECHAZADA","ANULADA"),2):
            RetencionProveedor.objects.get_or_create(empresa=empresa,clave_idempotencia=f"DMP2P-RET-{index:03d}",defaults={"numero":f"DMP2P-RET-{index:03d}","proveedor":accounts[index].proveedor,"factura":accounts[index].factura,"tipo":"ISR","codigo":"DEMO-CONFIG","base":Decimal("1000"),"tasa":Decimal("0.10"),"monto":Decimal("100"),"saldo":Decimal("100"),"estado":estado,"fecha":today,"creado_por":user})
        bank,_=CuentaBancariaEmpresa.objects.get_or_create(empresa=empresa,banco="Banco Demo P2P",numero_enmascarado="****5151",defaults={"moneda":mon,"saldo":Decimal("5000")})
        movements=[MovimientoTesoreria.objects.get_or_create(empresa=empresa,cuenta=bank,referencia=f"DMP2P-AMB-{i}",defaults={"tipo":"EGRESO","fecha":today,"monto":Decimal("50")})[0] for i in (1,2)]
        extract,_=ImportacionExtractoBancario.objects.get_or_create(empresa=empresa,cuenta=bank,huella="d"*64,defaults={"nombre_archivo":"DMP2P-ambiguo.csv","formato":"CSV","estado":"CONFIRMADA","confirmado_por":user,"confirmado_en":now})
        line,_=LineaExtractoBancario.objects.get_or_create(importacion=extract,huella="e"*64,defaults={"numero":2,"fecha":today,"descripcion":"Matching ambiguo demo","referencia":"SIN-REFERENCIA","monto":Decimal("-50"),"saldo":Decimal("4950"),"estado":"PENDIENTE"})
        ConciliacionBancaria.objects.get_or_create(empresa=empresa,cuenta=bank,desde=today,hasta=today,defaults={"saldo_banco":Decimal("4950"),"saldo_libros":Decimal("4950"),"estado":"BORRADOR"})
        for estado,offset in (("ACTIVO",1),("COMPLETADO",2),("EXPIRADO",-1),("FALLIDO",1)):
            session,_=WizardSession.objects.get_or_create(empresa=empresa,usuario=user,tipo="COMPRA",clave_idempotencia=f"DMP2P-WIZ-{estado}",defaults={"estado":estado,"paso_actual":11 if estado=="COMPLETADO" else 1,"total_pasos":11,"expira_en":now+timedelta(days=offset)})
            if not session.pasos.exists():WizardStepState.objects.bulk_create([WizardStepState(sesion=session,numero=i,nombre=f"Paso demo {i}",estado="VALIDADO" if estado=="COMPLETADO" else "PENDIENTE") for i in range(1,12)])
