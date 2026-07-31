from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("workflow/", include("workflow.urls")),
    path("compras/", include("compras.urls")),
    path("catalogos/", include("catalogos.urls")),
    path("core/", include("core.urls")),
    path("admin/", admin.site.urls),

    # App principal
    path("", include("conduces.urls")),

    # Inventario
    path("inventario/", include("inventario.urls")),

    # Contabilidad
    path("contabilidad/", include("contabilidad.urls")),

    # Comercial
    path("comercial/", include("comercial.urls")),

    # Documentos protegidos
    path("documentos/", include("documentos.urls")),

    # 🔐 RESET DE CONTRASEÑA
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(),
        name="password_reset"
    ),

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done"
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm"
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete"
    ),
]

# MEDIA FILES
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
