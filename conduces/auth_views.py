import logging

from django.contrib import messages
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetView
from django.conf import settings
from django.shortcuts import redirect
from django.template import loader

from core import transactional_email
from core.transactional_email import safe_delivery_error


logger = logging.getLogger("conduces.recuperacion_password")


class SastrePasswordResetForm(PasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        subject = "".join(
            loader.render_to_string(subject_template_name, context).splitlines()
        )
        body = loader.render_to_string(email_template_name, context)
        html = None
        if html_email_template_name:
            html = loader.render_to_string(html_email_template_name, context)
        transactional_email.send_transactional_email(
            subject=subject,
            text=body,
            html=html,
            recipients=[to_email],
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        )


class SastrePasswordResetView(PasswordResetView):
    form_class = SastrePasswordResetForm
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"

    def form_valid(self, form):
        logger.info("RECUPERACION_PASSWORD_ENVIO_INICIADO")
        try:
            response = super().form_valid(form)
        except Exception as error:
            details = safe_delivery_error(error)
            logger.error(
                "RECUPERACION_PASSWORD_ENVIO_FALLIDO causa=%s status=%s request_id=%s",
                details["category"],
                details["status"] or "n/a",
                details["request_id"] or "n/a",
            )
            messages.error(
                self.request,
                "El servicio de correo no está disponible temporalmente. Intenta más tarde.",
            )
            return redirect("password_reset")
        logger.info("RECUPERACION_PASSWORD_ENVIO_ENVIADO")
        return response
