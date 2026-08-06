from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render

from .icons.registry import ICONS


@login_required
def catalog(request):
    if not request.user.is_staff:
        raise PermissionDenied
    if not getattr(settings, "SEDL_CATALOG_ENABLED", settings.DEBUG):
        raise Http404
    return render(request, "design_system/catalog.html", {"icons": ICONS.values()})
