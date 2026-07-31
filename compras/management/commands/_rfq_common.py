from compras.models import ExpedienteCompra,ProcesoRFQ
def scoped(model,empresa):return model.objects.filter(empresa_id=empresa) if empresa else model.objects.all()
def add_scope(parser,modify=False):parser.add_argument("--empresa",type=int);parser.add_argument("--dry-run",action="store_true") if modify else None
