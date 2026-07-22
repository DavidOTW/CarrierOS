from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


def smtp_configured() -> bool:
    host = os.getenv("CARRIEROS_SMTP_HOST", "").strip()
    from_email = os.getenv("CARRIEROS_SMTP_FROM", "").strip()
    security = os.getenv("CARRIEROS_SMTP_SECURITY", "starttls").strip().lower()
    auth_required = os.getenv("CARRIEROS_SMTP_AUTH_REQUIRED", "true").strip().lower() == "true"
    username = os.getenv("CARRIEROS_SMTP_USERNAME", "").strip()
    password = os.getenv("CARRIEROS_SMTP_PASSWORD", "")
    return bool(
        host
        and from_email
        and security in {"starttls", "ssl", "none"}
        and (not auth_required or (username and password))
    )


def send_password_reset_email(*, recipient: str, full_name: str, reset_url: str) -> None:
    host = os.getenv("CARRIEROS_SMTP_HOST", "").strip()
    from_email = os.getenv("CARRIEROS_SMTP_FROM", "").strip()
    if not host or not from_email:
        raise RuntimeError("CarrierOS email delivery is not configured")

    port = int(os.getenv("CARRIEROS_SMTP_PORT", "587"))
    username = os.getenv("CARRIEROS_SMTP_USERNAME", "").strip()
    password = os.getenv("CARRIEROS_SMTP_PASSWORD", "")
    security = os.getenv("CARRIEROS_SMTP_SECURITY", "starttls").strip().lower()

    message = EmailMessage()
    message["Subject"] = "Reset your CarrierOS password"
    message["From"] = from_email
    message["To"] = recipient
    message.set_content(
        f"Hello {full_name or 'CarrierOS customer'},\n\n"
        "A password reset was requested for your CarrierOS account. "
        "Use the secure link below within 30 minutes:\n\n"
        f"{reset_url}\n\n"
        "If you did not request this change, you can ignore this email. "
        "Your password will remain unchanged.\n\nCarrierOS Support"
    )

    context = ssl.create_default_context()
    if security == "ssl":
        with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as server:
            if username:
                server.login(username, password)
            server.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=15) as server:
        server.ehlo()
        if security == "starttls":
            server.starttls(context=context)
            server.ehlo()
        if username:
            server.login(username, password)
        server.send_message(message)
