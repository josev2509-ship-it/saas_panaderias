import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from uuid import uuid4

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


@dataclass(frozen=True)
class DeliveryResult:
    provider: str
    message_id: str


class TransactionalEmailError(Exception):
    """Safe delivery error that never contains credentials or message contents."""

    def __init__(self, category, *, status=None, request_id=None):
        self.category = category
        self.status = status
        self.request_id = request_id
        super().__init__(category)


def safe_delivery_error(error):
    if isinstance(error, TransactionalEmailError):
        return {
            "category": error.category,
            "status": error.status,
            "request_id": error.request_id,
        }
    errno = getattr(error, "errno", None)
    category = type(error).__name__
    if errno is not None:
        category = f"{category}:errno={errno}"
    return {"category": category, "status": None, "request_id": None}


def _resend_error_category(body):
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return "http_error"
    value = payload.get("name") or payload.get("type")
    if isinstance(value, str) and value.replace("_", "").isalnum():
        return value[:80]
    return "http_error"


def send_transactional_email(
    *,
    subject,
    text,
    recipients,
    html=None,
    from_email=None,
    idempotency_key=None,
):
    api_key = getattr(settings, "RESEND_API_KEY", "")
    if not api_key:
        raise TransactionalEmailError("missing_resend_api_key")

    recipients = [str(value).strip() for value in recipients if str(value).strip()]
    if not recipients:
        raise TransactionalEmailError("missing_recipient")

    payload = {
        "from": from_email or settings.DEFAULT_FROM_EMAIL,
        "to": recipients,
        "subject": subject,
        "text": text,
    }
    if html:
        payload["html"] = html

    request = urllib.request.Request(
        getattr(settings, "RESEND_API_URL", "https://api.resend.com/emails"),
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "sastre-erp/1.0",
            "Idempotency-Key": idempotency_key or f"sastre/{uuid4()}",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=getattr(settings, "RESEND_API_TIMEOUT", 15),
        ) as response:
            response_body = response.read(16384)
            status = response.status
            request_id = response.headers.get("x-request-id")
    except urllib.error.HTTPError as error:
        body = error.read(16384)
        raise TransactionalEmailError(
            _resend_error_category(body),
            status=error.code,
            request_id=error.headers.get("x-request-id"),
        ) from error
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as error:
        reason = getattr(error, "reason", error)
        errno = getattr(reason, "errno", None)
        category = "network_error"
        if errno is not None:
            category = f"network_error:errno={errno}"
        raise TransactionalEmailError(category) from error

    try:
        result = json.loads(response_body.decode("utf-8"))
        message_id = result["id"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise TransactionalEmailError(
            "invalid_provider_response",
            status=status,
            request_id=request_id,
        ) from error

    return DeliveryResult(provider="resend", message_id=str(message_id))


class ResendEmailBackend(BaseEmailBackend):
    """Django email backend for framework consumers such as password reset."""

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            html = None
            for alternative in getattr(message, "alternatives", ()):
                if alternative.mimetype == "text/html":
                    html = alternative.content
                    break
            try:
                send_transactional_email(
                    subject=message.subject,
                    text=message.body,
                    html=html,
                    recipients=message.to,
                    from_email=message.from_email,
                )
            except TransactionalEmailError:
                if not self.fail_silently:
                    raise
            else:
                sent += 1
        return sent
