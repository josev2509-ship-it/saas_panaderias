from django.urls import path

from .media_views import protected_media


urlpatterns = [
    path("media/<path:media_path>", protected_media, name="protected_media_test"),
]
