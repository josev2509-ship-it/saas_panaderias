from django.db import transaction


def after_commit(callback):
    transaction.on_commit(callback)


def lock_by_pk(model, *, empresa, pk):
    return model.objects.select_for_update().get(pk=pk, empresa=empresa)

