def catalogo_empresa(model, empresa):
    return model.objects.filter(empresa=empresa)
