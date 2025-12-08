import os
import smtplib
from email.message import EmailMessage
from typing import List

def _env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v

def send_email(subject: str, body: str, to_emails: List[str]) -> None:
    host = _env("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = _env("SMTP_USER")
    password = _env("SMTP_PASS")
    email_from = os.getenv("EMAIL_FROM", user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = ", ".join(to_emails)
    msg.set_content(body)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
