from django.urls import path

from .views import catalog

app_name = "sedl"
urlpatterns = [path("", catalog, name="catalog")]
