"""Small Resend adapter for transactional email."""

import json
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)
RESEND_ENDPOINT = "https://api.resend.com/emails"


def send_email(to, subject, html, text=None, *, auth_only=False):
    """Send account security mail through Gmail SMTP when selected, otherwise Resend."""
    provider = os.environ.get('MAIL_PROVIDER', 'resend').strip().lower()
    if provider in {'gmail', 'smtp'}:
        # The Gmail account is deliberately restricted to account verification,
        # password recovery, and password-change codes for this local school app.
        if not auth_only:
            if os.environ.get('APP_ENV', 'development').lower() == 'production':
                raise RuntimeError('The Gmail sender is restricted to authentication mail.')
            logger.info('Non-authentication email left local: %s | %s', to, subject)
            return None
        username = os.environ.get('SMTP_USERNAME', '').strip()
        password = os.environ.get('SMTP_PASSWORD', '').replace(' ', '').strip()
        sender = os.environ.get('MAIL_FROM', '').strip()
        if not username or not password or not sender:
            if os.environ.get('APP_ENV', 'development').lower() == 'production':
                raise RuntimeError('Gmail SMTP username, app password, and sender are required.')
            logger.info('Development email to %s | %s\n%s', to, subject, text or html)
            return None
        message = EmailMessage()
        message['From'] = sender
        message['To'] = ', '.join(to) if isinstance(to, (list, tuple)) else to
        message['Subject'] = subject
        message.set_content(text or 'This message requires an HTML-capable email client.')
        message.add_alternative(html, subtype='html')
        host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        port = int(os.environ.get('SMTP_PORT', '587'))
        try:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(username, password)
                server.send_message(message)
            return {'provider': 'gmail-smtp', 'accepted': True}
        except (OSError, smtplib.SMTPException) as exc:
            logger.error('Gmail SMTP delivery failed: %s', exc)
            raise RuntimeError('Email delivery failed.') from exc

    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("MAIL_FROM")
    if not api_key or not sender:
        if os.environ.get("APP_ENV", "development").lower() == "production":
            raise RuntimeError("RESEND_API_KEY and MAIL_FROM must be configured.")
        logger.info("Development email to %s | %s\n%s", to, subject, text or html)
        return None

    payload = {
        "from": sender,
        "to": [to] if isinstance(to, str) else to,
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text
    request = Request(
        RESEND_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "FAST-CARS/1.0 (local school project)",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500] if isinstance(exc, HTTPError) else ""
        logger.error("Resend delivery failed: %s %s", exc, body)
        raise RuntimeError("Email delivery failed.") from exc
