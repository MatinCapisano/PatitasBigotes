from __future__ import annotations

from email.message import EmailMessage
import smtplib

from source.db.config import (
    get_mail_from,
    get_smtp_host,
    get_smtp_password,
    get_smtp_port,
    get_smtp_use_tls,
    get_smtp_username,
)


def _build_message(*, to_email: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = get_mail_from()
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def _send_message(msg: EmailMessage) -> None:
    host = get_smtp_host()
    port = get_smtp_port()
    username = get_smtp_username()
    password = get_smtp_password()
    use_tls = get_smtp_use_tls()

    with smtplib.SMTP(host=host, port=port, timeout=10) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(msg)


def send_email_verification(*, to_email: str, verify_link: str) -> None:
    body = (
        "Hola,\n\n"
        "Para verificar tu email en PatitasBigotes usa este enlace:\n"
        f"{verify_link}\n\n"
        "Si no solicitaste esta acción, ignorá este correo.\n"
    )
    msg = _build_message(
        to_email=to_email,
        subject="Verifica tu email",
        body=body,
    )
    _send_message(msg)


def send_password_reset(*, to_email: str, reset_link: str) -> None:
    body = (
        "Hola,\n\n"
        "Para restablecer tu contraseña en PatitasBigotes usa este enlace:\n"
        f"{reset_link}\n\n"
        "Si no solicitaste este cambio, ignorá este correo.\n"
    )
    msg = _build_message(
        to_email=to_email,
        subject="Restablecer contraseña",
        body=body,
    )
    _send_message(msg)
